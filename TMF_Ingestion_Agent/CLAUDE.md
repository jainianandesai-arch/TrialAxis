# TMF Ingestion Agent — Claude Code Instructions

## What this is
A governed protocol ingestion agent for the TMF Intelligence System.
When a new clinical trial PDF is dropped into the `inbox/` folder,
this agent identifies it, checks it against the approved eTMF Excel registry,
and enforces registry governance before ingesting anything.

The Excel registry is the source of truth. It is read-only. The pipeline never writes to it.

---

## Location
This file lives at:
```
Alimentiv/TMF_Ingestion_Agent/CLAUDE.md
```

All paths below are relative to this subfolder.
The main project root is one level up: `../`

---

## Your job
When the user says a new protocol has arrived (or says "run the ingest" / "check inbox"):

```
python ingest_protocol.py
```

No arguments needed. The script auto-detects PDFs in `inbox/` and also rechecks
any files sitting in `../data/pdfs/unregistered/` against the latest Excel registry.

---

## Critical rules — follow exactly, no exceptions

1. Do NOT assign a TAX Study ID inside the pipeline. TAX IDs come from Excel only.
2. Do NOT append to, edit, save, or update the Excel registry from the pipeline.
3. If a study is NOT found in the Excel registry — stop ingestion immediately.
4. Move the unregistered file to `../data/pdfs/unregistered/`.
5. Write an audit log record to `../logs/ingestion_audit.log`.
6. Do NOT write to `../trial_data.py` for unregistered studies.
7. Do NOT rename unregistered files using a TAX ID.
8. On every run, also recheck files in `../data/pdfs/unregistered/` against the latest Excel.
9. If a previously unregistered file is now found in the registry, ingest it automatically.
10. Official file renaming happens ONLY after a successful registry match.

---

## File structure
```
Alimentiv/                                   ← project root (one level up)
├── agents.py                                ← pipeline logic — import from here
├── app.py                                   ← DO NOT MODIFY
├── trial_data.py                            ← updated only on successful ingestion
├── tmf_importer.py                          ← DO NOT MODIFY
├── pdf_generator.py                         ← DO NOT MODIFY
├── query_engine.py                          ← DO NOT MODIFY
├── CLAUDE_CODE_INSTRUCTIONS.md             ← old file — IGNORE, do not read
├── .env                                     ← ANTHROPIC_API_KEY
│
├── data/                                    ← shared data folder at root
│   ├── exports/
│   │   └── eTMF_Status_Report.xlsx          ← read-only registry (source of truth)
│   ├── pdfs/                                ← registered + renamed PDFs live here
│   │   ├── incoming/                        ← internal staging only
│   │   └── unregistered/                    ← failed registry match
│   ├── chroma_db/                           ← vector index
│   └── trial_index.json                     ← keyword fallback index
│
├── logs/
│   └── ingestion_audit.log                  ← audit record of every run
│
└── TMF_Ingestion_Agent/                     ← you are here
    ├── CLAUDE.md                            ← this file
    ├── ingest_protocol.py                   ← run this
    ├── inbox/                               ← drop new PDFs here
    └── files/                               ← staging area (internal use only)
```

---

## Path reference — always use these exact paths

| Resource | Path from TMF_Ingestion_Agent/ |
|---|---|
| agents.py | `../agents.py` |
| trial_data.py | `../trial_data.py` |
| eTMF Excel registry | `../data/exports/eTMF_Status_Report.xlsx` |
| Registered PDFs | `../data/pdfs/` |
| Incoming staging | `../data/pdfs/incoming/` |
| Unregistered queue | `../data/pdfs/unregistered/` |
| ChromaDB | `../data/chroma_db/` |
| JSON fallback index | `../data/trial_index.json` |
| Audit log | `../logs/ingestion_audit.log` |

---

## What the pipeline does — in order

**Agent 1 — UploadAgent** (`../agents.py`)
- Picks up PDF from `inbox/` (or `../data/pdfs/unregistered/` on recheck)
- Stages it to `../data/pdfs/incoming/`
- Removes original from inbox immediately — inbox is always empty after each run
- Returns: pdf_bytes, original_filename

**Agent 2 — MetadataAgent** (`../agents.py`)
- Tiered extraction using Claude Sonnet 4.6:
  - Pass 1: Cover page (first 3 pages)
  - Pass 2: Page headers/footers
  - Pass 3: Full document (first 15,000 chars)
- Extracts:
  - document_type: Protocol / SAP / Amendment / ICF / Unknown
  - protocol_no, study_number, nct_id, eudract, ind_number
  - short_name, drug, sponsor, phase, condition
  - version, version_date
  - parent_protocol_no (for SAPs)

**Agent 3 — RegistryAgent** (`../agents.py`) — gatekeeper
- Looks up study in Excel Study Registry (READ ONLY) using this priority:
  1. Exact TAX Study ID (if present in filename or metadata)
  2. Exact protocol_no match
  3. Exact study_number / sponsor reference match
  4. Exact nct_id match
  5. Exact eudract match
  6. Normalized study title + sponsor (strong match only)
- SAP rule: parent study MUST be in registry first. If not → UNREGISTERED.
- If NO confident match → move to `../data/pdfs/unregistered/`, write audit log, STOP.
- If FOUND:
  - TAX Study ID read from Excel row (never generated)
  - File renamed: `{TAX_ID}_{StudyName}_{PrimaryRef}_{DocType}_{Version}_{Date}.pdf`
  - Moved to `../data/pdfs/`
  - New entry written to `../trial_data.py`
  - Excel is NOT touched

**Agent 4 — IndexingAgent** (`../agents.py`)
- Runs ONLY after successful registry match
- Chunks full_text (chunk_size=1500, overlap=200, max_chunks=40)
- Claude Sonnet 4.6 writes one-sentence summary per chunk
- 384-dim deterministic hash embedding
- Stores in ChromaDB at `../data/chroma_db/`
- Also writes to `../data/trial_index.json` as keyword fallback

**Agent 5 — PortfolioSyncAgent** (`../agents.py`)
- Clears Python module cache for trial_data
- Streamlit dashboard reloads automatically

---

## Audit log

Append one record to `../logs/ingestion_audit.log` for every file processed:

```
timestamp, source_file, document_type, protocol_no, study_title,
sponsor, match_status, tax_id, action, final_location, error
```

Action values: INGESTED | UNREGISTERED | DUPLICATE | FAILED

---

## Unregistered recheck

On every run, after processing inbox/:
1. Scan `../data/pdfs/unregistered/` for any PDFs
2. Re-extract metadata from each one
3. Re-attempt registry lookup against current Excel
4. If now found → ingest, move to `../data/pdfs/`, log as INGESTED
5. If still not found → leave in place, log as UNREGISTERED with new timestamp

---

## File naming

Registered files only:
```
{TAX_ID}_{StudyName}_{PrimaryRef}_{DocType}_{Version}_{Date}.pdf
```
Example: `TAX-2026-008_GLADIATOR-UC_APD334-210_Protocol_Amendment-2.0_2022-08-04.pdf`

Unregistered files: keep original filename, no TAX ID, no rename.

---

## Duplicate prevention

- Check if TAX ID already in ChromaDB → log DUPLICATE, skip
- Check if filename already exists in `../data/pdfs/` → log DUPLICATE, skip

---

## Test scenarios

**Test 1 — Unregistered protocol**
Drop PDF in inbox/, study NOT in Excel.
Expected: moved to ../data/pdfs/unregistered/, no TAX ID, Excel unchanged, trial_data.py unchanged.

**Test 2 — Registered protocol**
Add study to Excel externally, rerun.
Expected: TAX ID from Excel, file renamed, trial_data.py updated, Excel unchanged.

**Test 3 — Unregistered recheck**
Leave file in unregistered/, update Excel, rerun.
Expected: auto-detected, ingested, moved to ../data/pdfs/

**Test 4 — SAP before parent protocol**
Upload SAP when parent NOT in Excel.
Expected: SAP → unregistered, not ingested.

**Test 5 — Duplicate prevention**
Run ingest twice on same file.
Expected: second run logs DUPLICATE, no changes.

---

## After ingestion — report this

- TAX Study ID used (from Excel)
- Drug name and phase
- Document type detected
- Number of chunks indexed
- Audit log location: ../logs/ingestion_audit.log
- Any warnings or errors

---

## Absolute rules — never break these

- Do NOT modify `../app.py`
- Do NOT modify `../pdf_generator.py`
- Do NOT modify `../tmf_importer.py`
- Do NOT modify `../query_engine.py`
- Do NOT write to the Excel file — ever
- Do NOT invent or generate TAX Study IDs
- Do NOT use any model other than claude-sonnet-4-6
- Do NOT use any database other than ChromaDB
- Do NOT delete `../data/pdfs/` contents
- Do NOT read or follow `../CLAUDE_CODE_INSTRUCTIONS.md` — it is outdated
