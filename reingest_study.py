"""
Re-ingest a study cleanly.
Usage:
    python reingest_study.py TAX-2026-008
    python reingest_study.py TAX-2026-008 --pdf data/pdfs/TAX-2026-008_GLADIATOR-UC_APD334-210.pdf

What it does:
1. Removes TAX ID entry from trial_data.py
2. Removes all chunks from ChromaDB
3. Removes from trial_index.json
4. Copies PDF back to inbox/
5. Runs ingest_protocol.py
"""

import sys
import re
import json
import shutil
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

ROOT = Path(__file__).parent
TRIAL_DATA  = ROOT / "trial_data.py"
CHROMA_DIR  = ROOT / "data" / "chroma_db"
INDEX_FILE  = ROOT / "data" / "trial_index.json"
PDF_DIR     = ROOT / "data" / "pdfs"
INBOX       = ROOT / "TMF_Ingestion_Agent" / "inbox"

def remove_from_trial_data(tax_id: str) -> bool:
    content = TRIAL_DATA.read_text(encoding="utf-8")
    if f'"{tax_id}"' not in content:
        print(f"  {tax_id} not found in trial_data.py — skipping")
        return False

    # Match the full dict entry including nested braces
    pattern = rf'(\n\s*"{re.escape(tax_id)}":\s*\{{)'
    match = re.search(pattern, content)
    if not match:
        print(f"  Could not locate {tax_id} block — skipping")
        return False

    start = match.start()
    # Walk forward counting braces to find end of this entry
    depth = 0
    i = match.start()
    in_entry = False
    while i < len(content):
        if content[i] == '{':
            depth += 1
            in_entry = True
        elif content[i] == '}':
            depth -= 1
            if in_entry and depth == 0:
                end = i + 1
                # Also consume trailing comma and newline
                while end < len(content) and content[end] in (',', '\n', '\r'):
                    end += 1
                break
        i += 1

    new_content = content[:start] + content[end:]
    TRIAL_DATA.write_text(new_content, encoding="utf-8")
    print(f"  ✓ Removed {tax_id} from trial_data.py")
    return True

def remove_from_chromadb(tax_id: str) -> int:
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        col = client.get_collection("trial_chunks")
        ids = col.get(where={"tax_id": tax_id})["ids"]
        if ids:
            col.delete(ids=ids)
            print(f"  ✓ Removed {len(ids)} chunks from ChromaDB")
            return len(ids)
        else:
            print(f"  {tax_id} not found in ChromaDB — skipping")
            return 0
    except Exception as e:
        print(f"  ChromaDB error: {e}")
        return 0

def remove_from_json_index(tax_id: str) -> int:
    if not INDEX_FILE.exists():
        return 0
    with open(INDEX_FILE) as f:
        chunks = json.load(f)
    before = len(chunks)
    chunks = [c for c in chunks if c.get("tax_id") != tax_id]
    removed = before - len(chunks)
    with open(INDEX_FILE, "w") as f:
        json.dump(chunks, f, indent=2)
    if removed:
        print(f"  ✓ Removed {removed} chunks from trial_index.json")
    return removed

def find_pdf(tax_id: str, explicit_path: str = None) -> Path:
    if explicit_path:
        p = Path(explicit_path)
        if p.exists():
            return p
        print(f"  ERROR: specified PDF not found: {explicit_path}")
        return None

    # Search data/pdfs/ for a file starting with this TAX ID
    matches = list(PDF_DIR.glob(f"{tax_id}*.pdf"))
    if matches:
        return matches[0]

    print(f"  ERROR: No PDF found for {tax_id} in {PDF_DIR}")
    print(f"  Specify path explicitly: python reingest_study.py {tax_id} --pdf <path>")
    return None

def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: python reingest_study.py TAX-2026-008 [--pdf path/to/file.pdf]")
        sys.exit(1)

    tax_id = args[0].upper()
    explicit_pdf = None
    if "--pdf" in args:
        idx = args.index("--pdf")
        explicit_pdf = args[idx + 1] if idx + 1 < len(args) else None

    print(f"\n{'='*60}")
    print(f"  RE-INGEST: {tax_id}")
    print(f"{'='*60}\n")

    # Step 1 — Find PDF before we delete anything
    pdf_path = find_pdf(tax_id, explicit_pdf)
    if not pdf_path:
        sys.exit(1)
    print(f"  PDF: {pdf_path.name}\n")

    # Step 2 — Remove from all stores
    print("  Removing existing data...")
    remove_from_trial_data(tax_id)
    remove_from_chromadb(tax_id)
    remove_from_json_index(tax_id)

    # Step 3 — Copy PDF to inbox
    INBOX.mkdir(parents=True, exist_ok=True)
    dest = INBOX / pdf_path.name
    shutil.copy2(str(pdf_path), str(dest))
    print(f"\n  ✓ Copied to inbox: {dest.name}")

    # Step 4 — Run ingest
    print(f"\n  Running ingestion pipeline...\n")
    import subprocess
    result = subprocess.run(
        [sys.executable, "TMF_Ingestion_Agent/ingest_protocol.py"],
        cwd=str(ROOT)
    )

    print(f"\n{'='*60}")
    if result.returncode == 0:
        print(f"  ✓ {tax_id} re-ingested successfully")
    else:
        print(f"  ✗ Ingestion failed — check output above")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()