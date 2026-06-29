"""
TMF Intelligence System — Agent Pipeline
=========================================
Five agents run in sequence when a new protocol is submitted.

Model: Claude Sonnet 4.6 throughout
Storage: ChromaDB (persistent) + trial_index.json (fallback)
Primary Key: TAX Study ID (from eTMF Excel — never generated here)

Excel registry is READ-ONLY. Pipeline never writes to it.

File lifecycle:
  inbox/         → picked up and moved immediately (never left behind)
  incoming/      → internal staging only, cleared per file
  unregistered/  → files stay here until Excel is updated and recheck succeeds
  data/pdfs/     → only registered, properly named files land here

File naming (registered only):
  TAX-ID_StudyName_PrimaryRef_DocType_Version_Date.pdf
  e.g. TAX-2026-008_GLADIATOR-UC_APD334-210_Protocol_Amendment-2.0_2022-08-04.pdf

Identifier extraction — tiered:
  Pass 1: Cover page (first 3 pages)
  Pass 2: Page headers/footers
  Pass 3: Full document (first 15,000 chars)
"""

import io
import os
import re
import csv
import json
import time
import shutil
import requests
import PyPDF2
from datetime import datetime
from pathlib import Path
import anthropic

# ── Project paths ──────────────────────────────────────────────────────────────
def _find_project_root():
    here = Path(__file__).parent
    for candidate in [here / "src" / "trial_data.py", here / "trial_data.py"]:
        if candidate.exists():
            return here
    return here

ROOT             = _find_project_root()
CHROMA_DIR       = ROOT / "data" / "chroma_db"
PDF_DIR          = ROOT / "data" / "pdfs"
UNREGISTERED_DIR = ROOT / "data" / "pdfs" / "unregistered"
INCOMING_DIR     = ROOT / "data" / "pdfs" / "incoming"
INDEX_FILE       = ROOT / "data" / "trial_index.json"
EXPORT_FILE      = ROOT / "data" / "exports" / "eTMF_Status_Report.xlsx"
AUDIT_LOG        = ROOT / "logs" / "ingestion_audit.log"

MODEL = "claude-sonnet-4-6"

def _find_trial_data_path():
    for candidate in [ROOT / "src" / "trial_data.py", ROOT / "trial_data.py"]:
        if candidate.exists():
            return candidate
    return None

# ── Audit log ──────────────────────────────────────────────────────────────────
def write_audit_log(record: dict):
    """
    Append one record to logs/ingestion_audit.log (CSV format).
    Fields: timestamp, source_file, document_type, protocol_no,
            study_title, sponsor, match_status, tax_id,
            action, final_location, error
    """
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "timestamp", "source_file", "document_type", "protocol_no",
        "study_title", "sponsor", "match_status", "tax_id",
        "action", "final_location", "error"
    ]
    write_header = not AUDIT_LOG.exists()
    with open(AUDIT_LOG, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        row = {k: record.get(k, "") for k in fieldnames}
        row["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow(row)

# ── ChromaDB ───────────────────────────────────────────────────────────────────
def get_chroma_collection():
    import chromadb
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name="trial_chunks",
        metadata={"hnsw:space": "cosine"}
    )

def embed_text(text: str) -> list:
    import hashlib, math
    words = text.lower().split()
    unique_words = list(set(words))
    embedding = []
    for i in range(384):
        val = 0.0
        for j, word in enumerate(unique_words[:50]):
            h = int(hashlib.md5(f"{word}_{i}_{j}".encode()).hexdigest(), 16)
            val += (h % 1000 - 500) / 500.0
        embedding.append(math.tanh(val / max(len(unique_words), 1)))
    magnitude = math.sqrt(sum(x * x for x in embedding))
    if magnitude > 0:
        embedding = [x / magnitude for x in embedding]
    return embedding

# ── Excel registry — READ ONLY ─────────────────────────────────────────────────
def load_excel_registry() -> list:
    """
    Load eTMF Excel export as study registry.
    READ ONLY — this function never writes to the file.
    Returns list of dicts, one per study row.
    """
    if not EXPORT_FILE.exists():
        return []
    try:
        import openpyxl
        wb = openpyxl.load_workbook(str(EXPORT_FILE), data_only=True, read_only=True)
        ws = None
        for name in ["Study Registry", "Portfolio Summary", "TMF Status Report"]:
            if name in wb.sheetnames:
                ws = wb[name]
                break
        if ws is None:
            return []

        HEADER_ROW = 3
        rows_list = list(ws.rows)
        actual_val = str(rows_list[HEADER_ROW - 1][0].value or "").strip()
        if actual_val != "TAX Study ID":
            for i, row in enumerate(rows_list[:10]):
                if str(row[0].value or "").strip() == "TAX Study ID":
                    HEADER_ROW = i + 1
                    break

        headers = [rows_list[HEADER_ROW - 1][c].value
                   for c in range(len(rows_list[HEADER_ROW - 1]))]
        result = []
        for row in rows_list[HEADER_ROW:]:
            if row[0].value:
                result.append(dict(zip(headers, [c.value for c in row])))
        wb.close()
        return result
    except Exception as e:
        return []

def lookup_study_in_excel(identifiers: dict) -> dict | None:
    """
    Look up a study in the Excel registry using extracted identifiers.
    Priority: protocol_no → study_number → nct_id → eudract → ind_number
    Returns the matching row dict, or None if not found.
    READ ONLY — never modifies Excel.
    """
    registry = load_excel_registry()
    if not registry:
        return None

    lookup_pairs = [
        ("protocol_no",  ["Protocol No", "Sponsor Ref", "Primary Ref"]),
        ("study_number", ["Study Number", "Study Code", "Study No"]),
        ("short_name",   ["Study Name"]),
        ("nct_id",       ["NCT ID", "NCT"]),
        ("eudract",      ["EudraCT No", "EudraCT"]),
        ("ind_number",   ["IND No", "IND Number"]),
    ]

    for id_key, excel_cols in lookup_pairs:
        id_val = identifiers.get(id_key, "")
        if not id_val or str(id_val).strip().lower() in ("none", "n/a", "on file", "", "null"):
            continue
        id_val = str(id_val).strip().upper()
        for row in registry:
            for col in excel_cols:
                cell_val = str(row.get(col) or "").strip().upper()
                if cell_val and cell_val == id_val:
                    return row
    return None

def build_pdf_filename(tax_id: str, study_name: str, identifiers: dict,
                       doc_type: str = "Protocol", version: str = None,
                       version_date: str = None) -> str:
    """
    Build canonical PDF filename for registered files only.
    Format: TAX-ID_StudyName_PrimaryRef_DocType_Version_Date.pdf
    """
    safe_name = re.sub(r'[^\w\-]', '-', study_name).strip('-')
    primary_ref = (
        identifiers.get("protocol_no") or
        identifiers.get("study_number") or
        identifiers.get("nct_id") or
        identifiers.get("eudract") or
        "Unknown"
    )
    safe_ref  = re.sub(r'[^\w\-]', '-', str(primary_ref)).strip('-')
    safe_type = re.sub(r'[^\w\-]', '-', str(doc_type or "Protocol")).strip('-')

    parts = [tax_id, safe_name, safe_ref, safe_type]
    if version:
        safe_ver = re.sub(r'[^\w\-\.]', '-', str(version)).strip('-')
        parts.append(safe_ver)
    if version_date:
        safe_date = re.sub(r'[^\w\-]', '-', str(version_date)).strip('-')
        parts.append(safe_date)

    return "_".join(parts) + ".pdf"


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 1 — UPLOAD AGENT
# Moves file from inbox → incoming/ immediately.
# inbox/ is always emptied — files never left behind.
# ══════════════════════════════════════════════════════════════════════════════
class UploadAgent:
    def run(self, uploaded_file=None, url=None, inbox_path=None):
        PDF_DIR.mkdir(parents=True, exist_ok=True)
        UNREGISTERED_DIR.mkdir(parents=True, exist_ok=True)
        INCOMING_DIR.mkdir(exist_ok=True)

        # From inbox path (CLI / recheck)
        if inbox_path:
            p = Path(inbox_path)
            if not p.exists():
                return {"ok": False, "message": f"File not found: {inbox_path}"}
            pdf_bytes = p.read_bytes()
            dest = INCOMING_DIR / p.name
            dest.write_bytes(pdf_bytes)
            # Remove original from inbox immediately
            if p.parent != UNREGISTERED_DIR:
                p.unlink()
            return {"ok": True, "pdf_bytes": pdf_bytes,
                    "original_filename": p.name,
                    "message": f"Received {p.name} ({len(pdf_bytes)//1024} KB)"}

        # From Streamlit file uploader
        if uploaded_file is not None:
            pdf_bytes = uploaded_file.read()
            dest = INCOMING_DIR / uploaded_file.name
            dest.write_bytes(pdf_bytes)
            return {"ok": True, "pdf_bytes": pdf_bytes,
                    "original_filename": uploaded_file.name,
                    "message": f"Received {uploaded_file.name} ({len(pdf_bytes)//1024} KB)"}

        # From URL
        if url:
            try:
                r = requests.get(url.strip(), timeout=30,
                                 headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code == 200:
                    pdf_bytes = r.content
                    filename = url.strip().split("/")[-1] or "protocol.pdf"
                    (INCOMING_DIR / filename).write_bytes(pdf_bytes)
                    return {"ok": True, "pdf_bytes": pdf_bytes,
                            "original_filename": filename,
                            "message": f"Downloaded {filename} ({len(pdf_bytes)//1024} KB)"}
                return {"ok": False, "message": f"HTTP {r.status_code}"}
            except Exception as e:
                return {"ok": False, "message": f"Download error: {e}"}

        return {"ok": False, "message": "No file, URL, or inbox path provided."}


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 2 — METADATA AGENT
# Tiered extraction: cover page → headers/footers → full document
# Also detects document type (Protocol / SAP / Amendment / ICF)
# ══════════════════════════════════════════════════════════════════════════════
class MetadataAgent:

    def _extract_pages(self, pdf_bytes: bytes) -> tuple:
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            pages = [page.extract_text() or "" for page in reader.pages]
            full_text  = "\n".join(pages)
            cover_text = "\n".join(pages[:3])
            hf_chunks  = []
            for i, page_text in enumerate(pages):
                lines  = page_text.split('\n')
                header = '\n'.join(lines[:3])
                footer = '\n'.join(lines[-3:]) if len(lines) > 3 else ''
                hf_chunks.append(f"[Page {i+1} header]: {header}")
                if footer:
                    hf_chunks.append(f"[Page {i+1} footer]: {footer}")
            return full_text, cover_text, "\n".join(hf_chunks), pages
        except Exception:
            return "", "", "", []

    # ── Regex fallback patterns for version / date ─────────────────────────────
    _VERSION_PATTERNS = [
        # "Amendment 2.0, 04 August 2022"
        r'Amendment\s+(\d+\.?\d*)[,\s]+(\d{1,2}\s+\w+\s+\d{4})',
        # "Protocol Amendment 4 09 November 2022"
        r'Protocol\s+Amendment\s+(\d+\.?\d*)\s+(\d{1,2}\s+\w+\s+\d{4})',
        # "Protocol version and date: Final 6.0, 14-Dec-2021"
        r'(?:version[^:]*:|version\s+and\s+date\s*:)\s*(?:Final\s+)?(\d+\.?\d*)[,\s]+(\d{1,2}[-\s]\w+[-\s]\d{4})',
        # "Version: 5.0  Date: 12 March 2023"
        r'Version\s*:?\s*(\d+\.?\d*)\s+Date\s*:?\s*(\d{1,2}\s+\w+\s+\d{4})',
        # "v2.0 / 04-Aug-2022"
        r'\bv(\d+\.?\d+)\s*[/|]\s*(\d{1,2}[-\s]\w+[-\s]\d{4})',
        # "Final, 14-Dec-2021"
        r'\bFinal\s+(\d+\.?\d*)[,\s]+(\d{1,2}[-\s]\w+[-\s]\d{4})',
    ]

    _MONTHS = {
        'jan':'01','feb':'02','mar':'03','apr':'04','may':'05','jun':'06',
        'jul':'07','aug':'08','sep':'09','oct':'10','nov':'11','dec':'12',
        'january':'01','february':'02','march':'03','april':'04','june':'06',
        'july':'07','august':'08','september':'09','october':'10',
        'november':'11','december':'12',
    }

    def _parse_date(self, raw: str) -> str:
        """Convert human dates to YYYY-MM-DD. Returns None if unparseable."""
        raw = raw.strip().replace('-', ' ')
        parts = raw.split()
        if len(parts) == 3:
            try:
                # "04 August 2022" or "August 04 2022"
                if parts[0].isdigit():
                    day, mon, yr = parts
                else:
                    mon, day, yr = parts
                m = self._MONTHS.get(mon.lower())
                if m:
                    return f"{yr}-{m}-{int(day):02d}"
            except Exception:
                pass
        return None

    def _regex_version_date(self, cover_text: str) -> dict:
        """Try to extract version and date from cover text using regex patterns."""
        result = {}
        for pattern in self._VERSION_PATTERNS:
            m = re.search(pattern, cover_text, re.IGNORECASE)
            if m:
                ver_raw  = m.group(1).strip()
                date_raw = m.group(2).strip()
                result["version"]      = f"Amendment {ver_raw}" if "Amendment" in pattern else f"Version {ver_raw}"
                parsed = self._parse_date(date_raw)
                if parsed:
                    result["version_date"] = parsed
                break
        return result

    def _call_claude(self, text: str, client: anthropic.Anthropic, pass_name: str) -> dict:
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=800,
                system="""You are a clinical trial document identifier specialist.
Extract study identifiers from clinical trial protocol documents.
Return ONLY a valid JSON object — no explanation, no markdown, no code fences.
If a field is not found, use null.
For version and version_date: look carefully at the cover page for amendment numbers,
version numbers, and dates. These are critical fields — do not guess or omit them.""",
                messages=[{"role": "user", "content": f"""Extract all study identifiers from this clinical trial protocol text.

Fields to extract:
- document_type: "Protocol", "SAP", "Amendment", "ICF", or "Unknown"
- protocol_no: Protocol number / Protocol ID (e.g. APD334-210, TV48574-UC-30068)
- study_number: Study number / study code / sponsor reference
- parent_protocol_no: Parent protocol number (for SAPs only, else null)
- nct_id: ClinicalTrials.gov ID (NCT followed by exactly 8 digits)
- eudract: EudraCT number (format YYYY-NNNNNN-NN)
- ind_number: FDA IND number
- short_name: Study acronym or short name (e.g. GLADIATOR UC, RELIEVE UCCD)
- full_title: Full protocol title
- drug: Drug or compound name (e.g. Etrasimod, Vedolizumab)
- sponsor: Sponsoring organization
- phase: Trial phase (e.g. Phase 2, Phase 3)
- condition: Disease or condition (e.g. Ulcerative Colitis, Crohn's Disease)
- version: EXACT version or amendment label from the document
  (e.g. "Amendment 2.0", "Protocol Amendment 4", "Final 6.0", "Version 5.1")
  Do NOT write "Version 1.0" unless those exact words appear in the document.
- version_date: EXACT date of this version in YYYY-MM-DD format
  (e.g. "2022-08-04" for 04 August 2022)
  Do NOT use today's date. Only use dates found in the document.
- protocol_date: Date of the original protocol (first version), YYYY-MM-DD
- amendment_number: Amendment number only (e.g. "2.0", "4") if this is an amendment
- primary_objective: One sentence summary of primary objective
- primary_endpoint: One sentence summary of primary endpoint
- countries: Array of country names where study is conducted

IMPORTANT:
- version and version_date must come from the actual document cover page.
- If you cannot find version or version_date with confidence, return null for both.
- Do NOT default to "Version 1.0" or today's date.

Text ({pass_name}):
{text[:12000]}"""}]
            )
            raw = resp.content[0].text.strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw.strip())
        except Exception:
            return {}

    def _has_identifier(self, meta: dict) -> bool:
        for key in ["protocol_no", "study_number", "nct_id", "eudract"]:
            val = meta.get(key)
            if val and str(val).strip().lower() not in ("null", "none", "n/a", "", "unknown"):
                return True
        return False

    def run(self, pdf_bytes: bytes) -> dict:
        client = anthropic.Anthropic()
        full_text, cover_text, hf_text, pages = self._extract_pages(pdf_bytes)

        if not full_text.strip():
            return {"ok": False, "message": "No text extracted from PDF.",
                    "metadata": {}, "full_text": ""}

        meta = self._call_claude(cover_text, client, "cover page")
        if not self._has_identifier(meta):
            hf_meta = self._call_claude(hf_text, client, "page headers and footers")
            for k, v in hf_meta.items():
                if not meta.get(k) and v:
                    meta[k] = v
        if not self._has_identifier(meta):
            full_meta = self._call_claude(full_text[:15000], client, "full document")
            for k, v in full_meta.items():
                if not meta.get(k) and v:
                    meta[k] = v

        # ── Regex fallback for version/date if Claude didn't find them ──────────
        def _is_blank(val):
            return not val or str(val).strip().lower() in ("null","none","n/a","","unknown","version 1.0","v1.0")

        if _is_blank(meta.get("version")) or _is_blank(meta.get("version_date")):
            regex_result = self._regex_version_date(cover_text)
            if not regex_result:
                regex_result = self._regex_version_date(full_text[:5000])
            if regex_result.get("version") and _is_blank(meta.get("version")):
                meta["version"] = regex_result["version"]
            if regex_result.get("version_date") and _is_blank(meta.get("version_date")):
                meta["version_date"] = regex_result["version_date"]

        # ── Clean NCT ID ────────────────────────────────────────────────────────
        nct = str(meta.get("nct_id") or "").strip().upper()
        meta["nct_id"] = nct if re.match(r'^NCT\d{8}$', nct) else None

        # ── Normalise document type ─────────────────────────────────────────────
        raw_type = str(meta.get("document_type") or "").strip()
        for dt in ["Protocol", "SAP", "Amendment", "ICF"]:
            if dt.lower() in raw_type.lower():
                meta["document_type"] = dt
                break
        else:
            meta["document_type"] = "Unknown"

        # ── Sanitise version/date — never silently default ──────────────────────
        if _is_blank(meta.get("version")):
            meta["version"] = None
        if _is_blank(meta.get("version_date")):
            meta["version_date"] = None

        primary = (meta.get("protocol_no") or meta.get("study_number") or
                   meta.get("nct_id") or meta.get("eudract") or "Unknown")
        ver_str = meta.get("version") or "version unknown"
        msg = (f"{meta.get('short_name','?')} | {meta.get('drug','?')} | "
               f"{meta.get('phase','?')} | {meta.get('document_type','?')} | "
               f"Ref: {primary} | {ver_str}")

        return {
            "ok": True,
            "metadata": meta,
            "full_text": full_text,
            "message": msg,
            "has_identifier": self._has_identifier(meta)
        }


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 3 — REGISTRY AGENT
# Gatekeeper. Excel is READ ONLY — never written to.
# TAX Study ID comes from Excel only — never generated here.
# SAP not ingested unless parent protocol is registered.
# ══════════════════════════════════════════════════════════════════════════════
class RegistryAgent:
    def run(self, metadata: dict, original_filename: str = None) -> dict:
        td_path = _find_trial_data_path()
        if td_path is None:
            return {"ok": False, "message": "trial_data.py not found."}

        doc_type = metadata.get("document_type", "Unknown")

        # ── SAP rule: parent protocol must be registered first ─────────────────
        if doc_type == "SAP":
            parent_ref = metadata.get("parent_protocol_no") or metadata.get("protocol_no")
            if parent_ref:
                parent_lookup = {"protocol_no": parent_ref, "study_number": parent_ref}
                parent_row = lookup_study_in_excel(parent_lookup)
                if parent_row is None:
                    self._quarantine(original_filename)
                    write_audit_log({
                        "source_file":   original_filename,
                        "document_type": doc_type,
                        "protocol_no":   parent_ref,
                        "study_title":   metadata.get("short_name", ""),
                        "sponsor":       metadata.get("sponsor", ""),
                        "match_status":  "UNREGISTERED",
                        "tax_id":        "",
                        "action":        "UNREGISTERED",
                        "final_location": str(UNREGISTERED_DIR / (original_filename or "")),
                        "error":         "SAP parent protocol not in registry",
                    })
                    return {
                        "ok": False,
                        "unregistered": True,
                        "message": f"SAP rejected — parent protocol '{parent_ref}' not in registry. Moved to unregistered/."
                    }

        # ── Look up study in Excel registry (READ ONLY) ────────────────────────
        excel_row = lookup_study_in_excel(metadata)

        if excel_row is None:
            self._quarantine(original_filename)
            write_audit_log({
                "source_file":   original_filename,
                "document_type": doc_type,
                "protocol_no":   metadata.get("protocol_no", ""),
                "study_title":   metadata.get("short_name", ""),
                "sponsor":       metadata.get("sponsor", ""),
                "match_status":  "UNREGISTERED",
                "tax_id":        "",
                "action":        "UNREGISTERED",
                "final_location": str(UNREGISTERED_DIR / (original_filename or "")),
                "error":         "No match found in Excel registry",
            })
            return {
                "ok": False,
                "unregistered": True,
                "message": (
                    "Study not found in eTMF registry. "
                    "File moved to data/pdfs/unregistered/. "
                    "Add study to Excel registry and rerun to ingest."
                )
            }

        # ── Registry match found — TAX ID from Excel only ──────────────────────
        tax_id     = str(excel_row.get("TAX Study ID") or "").strip()
        study_name = str(excel_row.get("Study Name") or metadata.get("short_name") or "").strip()

        if not tax_id:
            return {"ok": False, "message": "TAX Study ID missing from Excel registry row."}

        metadata["tax_id"] = tax_id

        # ── Duplicate check ────────────────────────────────────────────────────
        try:
            collection = get_chroma_collection()
            existing = collection.get(where={"tax_id": tax_id})["ids"]
            if existing:
                # Clean up incoming staging file
                if original_filename:
                    src = INCOMING_DIR / original_filename
                    if src.exists():
                        src.unlink()
                write_audit_log({
                    "source_file":   original_filename,
                    "document_type": doc_type,
                    "protocol_no":   metadata.get("protocol_no", ""),
                    "study_title":   study_name,
                    "sponsor":       metadata.get("sponsor", ""),
                    "match_status":  "DUPLICATE",
                    "tax_id":        tax_id,
                    "action":        "DUPLICATE",
                    "final_location": "",
                    "error":         "Already indexed in ChromaDB",
                })
                return {"ok": True, "duplicate": True, "tax_id": tax_id,
                        "message": f"{tax_id} already indexed — skipping"}
        except Exception:
            pass

        # ── Build canonical filename ───────────────────────────────────────────
        excel_ref = str(excel_row.get("Sponsor Ref") or "").strip()
        filename_ids = dict(metadata)
        if excel_ref:
            filename_ids["protocol_no"] = excel_ref

        canonical_name = build_pdf_filename(
            tax_id, study_name, filename_ids,
            doc_type=doc_type,
            version=metadata.get("version"),
            version_date=metadata.get("version_date"),
        )

        # ── Move from incoming/ to data/pdfs/ ─────────────────────────────────
        if original_filename:
            src = INCOMING_DIR / original_filename
            dst = PDF_DIR / canonical_name
            if src.exists():
                shutil.move(str(src), str(dst))

        # ── Check if already in trial_data.py ─────────────────────────────────
        with open(td_path, "r", encoding="utf-8") as f:
            content = f.read()

        if f'"{tax_id}"' in content:
            write_audit_log({
                "source_file":   original_filename,
                "document_type": doc_type,
                "protocol_no":   metadata.get("protocol_no", ""),
                "study_title":   study_name,
                "sponsor":       metadata.get("sponsor", ""),
                "match_status":  "FOUND",
                "tax_id":        tax_id,
                "action":        "DUPLICATE",
                "final_location": str(PDF_DIR / canonical_name),
                "error":         "Already in trial_data.py",
            })
            return {
                "ok": True,
                "tax_id": tax_id,
                "pdf_filename": canonical_name,
                "message": f"{tax_id} ({study_name}) already registered — re-indexing"
            }

        # ── Write new study entry to trial_data.py ─────────────────────────────
        today    = datetime.now().strftime("%Y-%m-%d")
        countries = metadata.get("countries", ["See protocol"])
        if isinstance(countries, str):
            countries = [c.strip() for c in countries.split(",")]
        if not isinstance(countries, list):
            countries = ["See protocol"]

        def _safe(val, default="See protocol"):
            return str(val or default).replace('"', "'")

        # ── Version/date — never hardcode. Use extracted values or sentinel ──────
        extracted_version      = metadata.get("version")
        extracted_version_date = metadata.get("version_date")
        extracted_protocol_date= metadata.get("protocol_date") or extracted_version_date

        def _is_blank(v):
            return not v or str(v).strip().lower() in ("null","none","n/a","","unknown","version 1.0","v1.0")

        if _is_blank(extracted_version):
            latest_amendment      = "Needs Metadata Review"
            audit_version_warning = "version not extracted from PDF"
        else:
            latest_amendment      = extracted_version
            audit_version_warning = ""

        if _is_blank(extracted_version_date):
            latest_amendment_date = None
            protocol_date         = None
            audit_date_warning    = "version_date not extracted from PDF"
        else:
            latest_amendment_date = extracted_version_date
            protocol_date         = extracted_protocol_date or extracted_version_date
            audit_date_warning    = ""

        # Warn in audit log if metadata is incomplete
        audit_warning = " | ".join(filter(None, [audit_version_warning, audit_date_warning]))

        # Protocol (Final) tmf_documents entry uses extracted values
        protocol_tmf_version = latest_amendment if latest_amendment != "Needs Metadata Review" else "See protocol"
        protocol_tmf_date    = latest_amendment_date or today

        amend_entry_version = latest_amendment if latest_amendment != "Needs Metadata Review" else "Unknown"
        amend_entry_date    = latest_amendment_date or "Unknown"

        new_entry = f'''
    "{tax_id}": {{
        "tax_id": "{tax_id}",
        "nct_id": "{_safe(metadata.get('nct_id'), 'N/A')}",
        "eudract": "{_safe(metadata.get('eudract'), 'N/A')}",
        "protocol_no": "{_safe(metadata.get('protocol_no'), 'N/A')}",
        "study_number": "{_safe(metadata.get('study_number'), 'N/A')}",
        "short_name": "{_safe(metadata.get('short_name'), tax_id)}",
        "drug": "{_safe(metadata.get('drug'), 'Unknown')}",
        "sponsor": "{_safe(metadata.get('sponsor'), 'Unknown')}",
        "phase": "{_safe(metadata.get('phase'), 'Unknown')}",
        "condition": "{_safe(metadata.get('condition'), 'Unknown')}",
        "condition_type": [],
        "design": "See protocol",
        "duration": "See protocol",
        "ind_number": "{_safe(metadata.get('ind_number'), 'On file')}",
        "protocol_date": {json.dumps(protocol_date)},
        "latest_amendment": "{latest_amendment}",
        "latest_amendment_date": {json.dumps(latest_amendment_date)},
        "countries": {json.dumps(countries)},
        "patients_screened": None,
        "patients_randomized": None,
        "primary_objective": "{_safe(metadata.get('primary_objective'))}",
        "primary_endpoint": "{_safe(metadata.get('primary_endpoint'))}",
        "pdf_filename": "{canonical_name}",
        "inclusion_criteria": ["See protocol"],
        "exclusion_criteria": ["See protocol"],
        "amendment_history": [{{"version": "{amend_entry_version}", "date": "{amend_entry_date}", "patients_at_time": "0"}}],
        "tmf_documents": {{
            "Protocol (Final)": {{"status": "Complete", "date": "{protocol_tmf_date}", "version": "{protocol_tmf_version}"}},
            "Investigator Agreement": {{"status": "Missing", "date": None, "version": None}},
            "Ethics Committee Approval": {{"status": "Missing", "date": None, "version": None}},
            "IND Approval": {{"status": "Missing", "date": None, "version": None}},
            "Informed Consent Form": {{"status": "Missing", "date": None, "version": None}},
            "Monitoring Plan": {{"status": "Missing", "date": None, "version": None}},
        }},
        "risk_level": "Medium",
        "notes": "Auto-ingested via TMF Intelligence System.",
    }},'''

        # Find closing brace of TRIALS dict specifically — not FLAG_RULES or any other dict
        trials_match = content.find("TRIALS = {")
        if trials_match == -1:
            trials_match = content.find("TRIALS={")
        if trials_match == -1:
            return {"ok": False, "message": "Could not find TRIALS dict in trial_data.py"}

        depth = 0
        i = trials_match + content[trials_match:].find("{")
        insert_point = -1
        while i < len(content):
            if content[i] == "{":
                depth += 1
            elif content[i] == "}":
                depth -= 1
                if depth == 0:
                    insert_point = i
                    break
            i += 1

        if insert_point == -1:
            return {"ok": False, "message": "Could not find TRIALS closing brace in trial_data.py"}

        content = content[:insert_point] + new_entry + "\n" + content[insert_point:]
        with open(td_path, "w", encoding="utf-8") as f:
            f.write(content)
        os.utime(td_path, None)

        write_audit_log({
            "source_file":   original_filename,
            "document_type": doc_type,
            "protocol_no":   metadata.get("protocol_no", ""),
            "study_title":   study_name,
            "sponsor":       metadata.get("sponsor", ""),
            "match_status":  "FOUND",
            "tax_id":        tax_id,
            "action":        "INGESTED",
            "final_location": str(PDF_DIR / canonical_name),
            "error":         audit_warning,
        })

        return {
            "ok": True,
            "tax_id": tax_id,
            "pdf_filename": canonical_name,
            "message": f"{tax_id} ({study_name}) registered — {canonical_name}"
        }

    def _quarantine(self, original_filename: str):
        """Move file from incoming/ to unregistered/. Never rename with TAX ID."""
        if not original_filename:
            return
        UNREGISTERED_DIR.mkdir(parents=True, exist_ok=True)
        src = INCOMING_DIR / original_filename
        dst = UNREGISTERED_DIR / original_filename
        if src.exists():
            shutil.move(str(src), str(dst))


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 4 — INDEXING AGENT
# ══════════════════════════════════════════════════════════════════════════════
class IndexingAgent:
    CHUNK_SIZE    = 1500
    CHUNK_OVERLAP = 200
    MAX_CHUNKS    = 40

    def run(self, full_text: str, metadata: dict, progress_callback=None) -> dict:
        tax_id     = metadata.get("tax_id", "UNKNOWN")
        short_name = metadata.get("short_name", tax_id)
        drug       = metadata.get("drug", "Unknown")
        condition  = metadata.get("condition", "Unknown")

        chunks, start = [], 0
        while start < len(full_text):
            chunk = full_text[start:start + self.CHUNK_SIZE].strip()
            if chunk:
                chunks.append(chunk)
            start += self.CHUNK_SIZE - self.CHUNK_OVERLAP
        chunks = chunks[:self.MAX_CHUNKS]

        client     = anthropic.Anthropic()
        collection = get_chroma_collection()
        new_chunks = []

        # Remove existing chunks for this TAX ID
        try:
            existing = collection.get(where={"tax_id": tax_id})["ids"]
            if existing:
                collection.delete(ids=existing)
        except Exception:
            pass

        for i, chunk in enumerate(chunks):
            chunk_id = f"{tax_id}_{i}"
            try:
                resp = client.messages.create(
                    model=MODEL, max_tokens=100,
                    messages=[{"role": "user",
                               "content": f"Summarize this clinical trial excerpt in one sentence:\n\n{chunk[:600]}"}]
                )
                summary = resp.content[0].text.strip()
                time.sleep(0.1)
            except Exception:
                summary = ""

            embed_input = f"{summary}\n\n{chunk[:800]}"
            embedding   = embed_text(embed_input)

            chunk_record = {
                "chunk_id": chunk_id, "tax_id": tax_id,
                "short_name": short_name, "drug": drug,
                "condition": condition, "chunk_index": i,
                "text": chunk, "summary": summary,
            }
            new_chunks.append(chunk_record)

            try:
                collection.upsert(
                    ids=[chunk_id],
                    embeddings=[embedding],
                    documents=[embed_input],
                    metadatas=[{
                        "tax_id": tax_id, "short_name": short_name,
                        "drug": drug, "condition": condition,
                        "chunk_index": i, "summary": summary,
                        "text": chunk[:1000],
                    }]
                )
            except Exception:
                pass

            if progress_callback:
                progress_callback((i + 1) / len(chunks))

        # Write JSON fallback index
        INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
        existing_json = []
        if INDEX_FILE.exists():
            try:
                with open(INDEX_FILE) as f:
                    existing_json = json.load(f)
            except Exception:
                existing_json = []
        existing_json = [c for c in existing_json if c.get("tax_id") != tax_id]
        existing_json.extend(new_chunks)
        with open(INDEX_FILE, "w") as f:
            json.dump(existing_json, f, indent=2)

        return {"ok": True, "chunks": len(new_chunks),
                "message": f"{len(new_chunks)} chunks indexed for {tax_id}"}


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 5 — PORTFOLIO SYNC AGENT
# ══════════════════════════════════════════════════════════════════════════════
class PortfolioSyncAgent:
    def run(self):
        import sys
        for key in list(sys.modules.keys()):
            if "trial_data" in key:
                del sys.modules[key]
        return {"ok": True, "message": "Portfolio cache cleared — dashboard updated"}


# ══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════
class TMFOrchestrator:
    def run(self, uploaded_file=None, url=None, inbox_path=None,
            existing_trials=None, progress_bar=None):
        existing_trials = existing_trials or {}

        yield "📥 **Upload Agent** — receiving document..."
        result = UploadAgent().run(
            uploaded_file=uploaded_file, url=url, inbox_path=inbox_path
        )
        if not result["ok"]:
            yield f"❌ {result['message']}"
            return
        yield f"✓ {result['message']}"
        pdf_bytes         = result["pdf_bytes"]
        original_filename = result.get("original_filename", "protocol.pdf")

        yield "🔍 **Metadata Agent** — extracting identifiers..."
        result = MetadataAgent().run(pdf_bytes)
        if not result["ok"]:
            yield f"❌ {result['message']}"
            return
        metadata  = result["metadata"]
        full_text = result["full_text"]
        yield f"✓ {result['message']}"

        if not result.get("has_identifier"):
            yield "⚠ No standard identifier found — will attempt Excel lookup by study name."

        yield "📋 **Registry Agent** — checking eTMF registry (read-only)..."
        result = RegistryAgent().run(metadata, original_filename)

        if result.get("duplicate"):
            yield f"⚠ {result['message']}"
            yield "__DUPLICATE__"
            return

        if result.get("unregistered"):
            yield f"🚨 **Unregistered** — {result['message']}"
            yield "__UNREGISTERED__"
            return

        if not result["ok"]:
            yield f"❌ {result['message']}"
            return

        metadata["tax_id"] = result["tax_id"]
        yield f"✓ {result['message']}"

        yield f"📚 **Indexing Agent** — chunking and embedding protocol..."
        def _prog(pct):
            if progress_bar:
                progress_bar.progress(pct)
        result = IndexingAgent().run(full_text, metadata, progress_callback=_prog)
        if progress_bar:
            progress_bar.empty()
        yield f"✓ {result['message']}"

        yield "🔄 **Portfolio Sync Agent** — refreshing dashboard..."
        PortfolioSyncAgent().run()
        yield "✓ Dashboard will reload automatically"

        yield (f"🎉 **{metadata.get('drug', '?')} ({metadata['tax_id']})** "
               f"successfully added to portfolio.")
        yield "__SUCCESS__"