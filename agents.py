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

    def _call_claude(self, text: str, client: anthropic.Anthropic, pass_name: str) -> dict:
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=700,
                system="""You are a clinical trial document identifier specialist.
Extract study identifiers from clinical trial protocol documents.
Return ONLY a valid JSON object — no explanation, no markdown, no code fences.
If a field is not found, use null.""",
                messages=[{"role": "user", "content": f"""Extract all study identifiers from this clinical trial protocol text.

Fields to extract:
- document_type: "Protocol", "SAP", "Amendment", "ICF", or "Unknown"
- protocol_no: Protocol number / Protocol ID
- study_number: Study number / study code / sponsor reference
- parent_protocol_no: Parent protocol number (for SAPs only, else null)
- nct_id: ClinicalTrials.gov ID (NCT followed by 8 digits)
- eudract: EudraCT number (format YYYY-NNNNNN-NN)
- ind_number: FDA IND number
- short_name: Study acronym or short name
- full_title: Full protocol title
- drug: Drug or compound name
- sponsor: Sponsoring organization
- phase: Trial phase
- condition: Disease or condition
- version: Version or amendment number (e.g. "Amendment 2.0")
- version_date: Version date (YYYY-MM-DD if possible)
- primary_objective: One sentence
- primary_endpoint: One sentence
- countries: Array of country names

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

        # Clean NCT ID
        nct = str(meta.get("nct_id") or "").strip().upper()
        meta["nct_id"] = nct if re.match(r'^NCT\d{8}$', nct) else None

        # Normalise document type
        raw_type = str(meta.get("document_type") or "").strip()
        for dt in ["Protocol", "SAP", "Amendment", "ICF"]:
            if dt.lower() in raw_type.lower():
                meta["document_type"] = dt
                break
        else:
            meta["document_type"] = "Unknown"

        primary = (meta.get("protocol_no") or meta.get("study_number") or
                   meta.get("nct_id") or meta.get("eudract") or "Unknown")
        msg = (f"{meta.get('short_name','?')} | {meta.get('drug','?')} | "
               f"{meta.get('phase','?')} | {meta.get('document_type','?')} | Ref: {primary}")

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

        # ── Version-aware duplicate / update check ────────────────────────────
        incoming_version = str(metadata.get("version") or "").strip()
        is_update        = False
        stored_version   = ""

        try:
            collection     = get_chroma_collection()
            existing_ids   = collection.get(where={"tax_id": tax_id, "is_current": 1})["ids"]
            # Also catch old chunks that predate versioning (no is_current field)
            if not existing_ids:
                existing_ids = collection.get(where={"tax_id": tax_id})["ids"]

            if existing_ids:
                # Read stored version from trial_data.py
                try:
                    _ns = {}
                    with open(td_path, "r", encoding="utf-8") as _f:
                        exec(compile(_f.read(), str(td_path), "exec"), _ns)
                    stored_version = str(
                        _ns.get("TRIALS", {}).get(tax_id, {}).get("latest_amendment") or ""
                    ).strip()
                except Exception:
                    pass

                if incoming_version and stored_version and incoming_version == stored_version:
                    # True duplicate — exact same version already indexed
                    if original_filename:
                        src = INCOMING_DIR / original_filename
                        if src.exists():
                            src.unlink()
                    write_audit_log({
                        "source_file":    original_filename,
                        "document_type":  doc_type,
                        "protocol_no":    metadata.get("protocol_no", ""),
                        "study_title":    study_name,
                        "sponsor":        metadata.get("sponsor", ""),
                        "match_status":   "DUPLICATE",
                        "tax_id":         tax_id,
                        "action":         "DUPLICATE",
                        "final_location": "",
                        "error":          f"Version '{incoming_version}' already indexed",
                    })
                    return {"ok": True, "duplicate": True, "tax_id": tax_id,
                            "message": f"{tax_id} v{incoming_version} already indexed — skipping"}
                else:
                    # New or unknown version — mark existing current chunks as superseded
                    try:
                        old = collection.get(
                            where={"tax_id": tax_id, "is_current": 1},
                            include=["metadatas"],
                        )
                        if old["ids"]:
                            collection.update(
                                ids=old["ids"],
                                metadatas=[{**m, "is_current": 0} for m in old["metadatas"]],
                            )
                    except Exception:
                        pass
                    is_update = True
                    metadata["is_update"]         = True
                    metadata["previous_version"]  = stored_version
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
            if is_update and incoming_version:
                self._update_trial_amendment(
                    td_path, tax_id, incoming_version,
                    metadata.get("version_date", ""), canonical_name,
                )
            action_label = f"updated to {incoming_version}" if is_update else "already registered"
            write_audit_log({
                "source_file":    original_filename,
                "document_type":  doc_type,
                "protocol_no":    metadata.get("protocol_no", ""),
                "study_title":    study_name,
                "sponsor":        metadata.get("sponsor", ""),
                "match_status":   "FOUND",
                "tax_id":         tax_id,
                "action":         "INGESTED",
                "final_location": str(PDF_DIR / canonical_name),
                "error":          "",
            })
            return {
                "ok": True,
                "tax_id": tax_id,
                "pdf_filename": canonical_name,
                "message": f"{tax_id} ({study_name}) {action_label} — re-indexing"
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
        "protocol_date": "{_safe(metadata.get('version_date'), today)}",
        "latest_amendment": "{_safe(metadata.get('version'), 'Version 1.0')}",
        "latest_amendment_date": "{_safe(metadata.get('version_date'), today)}",
        "countries": {json.dumps(countries)},
        "patients_screened": None,
        "patients_randomized": None,
        "primary_objective": "{_safe(metadata.get('primary_objective'))}",
        "primary_endpoint": "{_safe(metadata.get('primary_endpoint'))}",
        "pdf_filename": "{canonical_name}",
        "inclusion_criteria": ["See protocol"],
        "exclusion_criteria": ["See protocol"],
        "amendment_history": [{{"version": "{_safe(metadata.get('version'), 'Version 1.0')}", "date": "{_safe(metadata.get('version_date'), today)}", "patients_at_time": "0"}}],
        "tmf_documents": {{
            "Protocol (Final)": {{"status": "Complete", "date": "{today}", "version": "{_safe(metadata.get('version'), 'v1.0')}"}},
            "Investigator Agreement": {{"status": "Missing", "date": None, "version": None}},
            "Ethics Committee Approval": {{"status": "Missing", "date": None, "version": None}},
            "IND Approval": {{"status": "Missing", "date": None, "version": None}},
            "Informed Consent Form": {{"status": "Missing", "date": None, "version": None}},
            "Monitoring Plan": {{"status": "Missing", "date": None, "version": None}},
        }},
        "risk_level": "Medium",
        "notes": "Auto-ingested via TMF Intelligence System.",
    }},'''

        insert_point = content.rfind("\n}")
        if insert_point == -1:
            return {"ok": False, "message": "Could not find insertion point in trial_data.py"}

        content = content[:insert_point] + new_entry + "\n}" + content[insert_point + 2:]
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
            "error":         "",
        })

        return {
            "ok": True,
            "tax_id": tax_id,
            "pdf_filename": canonical_name,
            "message": f"{tax_id} ({study_name}) registered — {canonical_name}"
        }

    def _update_trial_amendment(self, td_path, tax_id, new_version,
                                version_date, pdf_filename):
        """Update amendment history for an existing study in trial_data.py."""
        try:
            import pprint as _pprint
            _ns = {}
            with open(td_path, "r", encoding="utf-8") as _f:
                exec(compile(_f.read(), str(td_path), "exec"), _ns)
            trials     = _ns.get("TRIALS", {})
            tmf_zones  = _ns.get("TMF_ZONES")
            flag_rules = _ns.get("FLAG_RULES")
            if tax_id not in trials:
                return
            today = datetime.now().strftime("%Y-%m-%d")
            t = trials[tax_id]
            t["latest_amendment"]      = new_version
            t["latest_amendment_date"] = version_date or today
            t["pdf_filename"]          = pdf_filename
            history = t.get("amendment_history", [])
            if not any(h.get("version") == new_version for h in history):
                history.append({"version": new_version,
                                 "date": version_date or today,
                                 "patients_at_time": "0"})
            t["amendment_history"] = history
            if "tmf_documents" in t and "Protocol (Final)" in t["tmf_documents"]:
                t["tmf_documents"]["Protocol (Final)"]["version"] = new_version
                t["tmf_documents"]["Protocol (Final)"]["date"]    = today
            src = (
                f"# Last eTMF sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                '"""\nTMF Intelligence System — Trial Portfolio\n'
                'Primary Key: TAX Study ID (assigned by TrialAxis CRO internal system)\n'
                'External IDs (NCT, EudraCT, Protocol No) are reference fields only.\n'
                'Statuses driven by eTMF Excel import — not hardcoded.\n"""\n\n'
                f"TRIALS = {_pprint.pformat(trials, indent=4, width=100, sort_dicts=False)}\n"
            )
            if tmf_zones:
                src += f"\nTMF_ZONES = {_pprint.pformat(tmf_zones, indent=4)}\n"
            if flag_rules:
                src += f"\nFLAG_RULES = {_pprint.pformat(flag_rules, indent=4)}\n"
            with open(td_path, "w", encoding="utf-8") as _f:
                _f.write(src)
            os.utime(td_path, None)
        except Exception:
            pass  # Non-fatal — indexing still proceeds

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

        client        = anthropic.Anthropic()
        collection    = get_chroma_collection()
        new_chunks    = []
        doc_version   = str(metadata.get("version") or "v1.0").strip()
        version_slug  = re.sub(r'[^\w\-]', '-', doc_version).strip('-') or "v1"

        # Mark existing current chunks as superseded (keep for version history)
        try:
            old = collection.get(where={"tax_id": tax_id, "is_current": 1},
                                 include=["metadatas"])
            if old["ids"]:
                collection.update(
                    ids=old["ids"],
                    metadatas=[{**m, "is_current": 0} for m in old["metadatas"]],
                )
        except Exception:
            pass

        for i, chunk in enumerate(chunks):
            chunk_id = f"{tax_id}_{version_slug}_{i}"
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
                "doc_version": doc_version, "is_current": 1,
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
                        "doc_version": doc_version, "is_current": 1,
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
        # Replace only current-version chunks; keep old version chunks for history
        existing_json = [c for c in existing_json
                         if not (c.get("tax_id") == tax_id and c.get("is_current", 1) == 1)]
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