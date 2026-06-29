"""
TMF Ingestion Agent — CLI Entrypoint
=====================================
Usage:
    python ingest_protocol.py                        # process all inbox PDFs + recheck unregistered/
    python ingest_protocol.py inbox/my_protocol.pdf  # single file
    python ingest_protocol.py https://...            # URL

All pipeline logic lives in ../agents.py.
"""

import sys
import os
from pathlib import Path

# ── Load .env ─────────────────────────────────────────────────────────────────
from dotenv import load_dotenv
_env = Path(__file__).parent / ".env"
if not _env.exists():
    _env = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_env, override=True)

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("ERROR: ANTHROPIC_API_KEY not found.")
    print(f"  Looked for .env at: {_env}")
    print("  Add your key to .env as: ANTHROPIC_API_KEY=sk-ant-...")
    sys.exit(1)

# ── Import pipeline from parent folder ────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))
from agents import TMFOrchestrator, UNREGISTERED_DIR

INBOX        = Path(__file__).parent / "inbox"
SINGLE_ARG   = len(sys.argv) >= 2


def _clean_msg(msg):
    """Strip markdown and emoji for Windows cp1252 console output."""
    replacements = [
        ("**", ""), ("\U0001f4e5", "[Upload]"), ("\U0001f50d", "[Meta]"),
        ("\U0001f4cb", "[Registry]"), ("\U0001f4da", "[Index]"), ("\U0001f504", "[Sync]"),
        ("\U0001f6a8", "ALERT"), ("\U0001f389", ">>"),
        ("✓", "OK"), ("✗", "FAIL"), ("⚠", "!"), ("❌", "FAIL"),
        ("—", "--"), ("→", "->"),
    ]
    for old, new in replacements:
        msg = msg.replace(old, new)
    return msg.encode("ascii", errors="replace").decode("ascii")


def run_pipeline(pdf_path: Path = None, url: str = None) -> str:
    """Run one file through the orchestrator. Returns 'ingested', 'duplicate', 'unregistered', or 'failed'."""
    orchestrator = TMFOrchestrator()

    class FileWrapper:
        def __init__(self, p):
            self.name = p.name
            self._path = p
        def read(self):
            return self._path.read_bytes()

    if url:
        generator = orchestrator.run(url=url)
    else:
        generator = orchestrator.run(inbox_path=str(pdf_path))

    outcome = "failed"
    for message in generator:
        if message == "__SUCCESS__":
            outcome = "ingested"
            continue
        if message == "__DUPLICATE__":
            outcome = "duplicate"
            continue
        if message == "__UNREGISTERED__":
            outcome = "unregistered"
            continue
        print(_clean_msg(message))

    return outcome


def print_header(title: str):
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_file_banner(name: str, size_kb: int):
    print()
    print(f"  -- {name} ({size_kb} KB) --")
    print()


# ══════════════════════════════════════════════════════════════════════════════
# SINGLE-FILE / URL MODE
# ══════════════════════════════════════════════════════════════════════════════
if SINGLE_ARG:
    source = sys.argv[1]
    is_url = source.startswith("http://") or source.startswith("https://")

    print_header("TMF INGESTION AGENT  |  TrialAxis CRO")

    if is_url:
        print(f"  Source: {source}")
        print("=" * 60)
        outcome = run_pipeline(url=source)
    else:
        pdf_path = Path(source)
        if not pdf_path.exists():
            pdf_path = INBOX / source
        if not pdf_path.exists():
            print(f"ERROR: File not found: {source}")
            sys.exit(1)
        print(f"  Source: {pdf_path.name}  ({pdf_path.stat().st_size // 1024} KB)")
        print("=" * 60)
        outcome = run_pipeline(pdf_path=pdf_path)
        # Safety net: remove from inbox regardless of outcome
        if pdf_path.exists() and pdf_path.parent == INBOX:
            pdf_path.unlink()

    print()
    if outcome == "ingested":
        print("=" * 60)
        print("  INGESTION COMPLETE -- study added to portfolio.")
        print("  Restart Streamlit to see it in the dashboard.")
        print("=" * 60)
    elif outcome == "duplicate":
        print("  Study already in portfolio -- no changes made.")
    elif outcome == "unregistered":
        print("=" * 60)
        print("  UNREGISTERED -- add study to Excel registry and rerun.")
        print("=" * 60)
        sys.exit(1)
    else:
        print("=" * 60)
        print("  INGESTION FAILED -- see errors above.")
        print("=" * 60)
        sys.exit(1)

    sys.exit(0)


# ══════════════════════════════════════════════════════════════════════════════
# AUTO MODE — no arguments
# Process all inbox PDFs, then recheck unregistered/
# ══════════════════════════════════════════════════════════════════════════════
INBOX.mkdir(exist_ok=True)
UNREGISTERED_DIR.mkdir(parents=True, exist_ok=True)

inbox_pdfs       = sorted(INBOX.glob("*.pdf"))
unregistered_pdfs = sorted(UNREGISTERED_DIR.glob("*.pdf"))

if not inbox_pdfs and not unregistered_pdfs:
    print("Inbox and unregistered/ are both empty. Nothing to do.")
    sys.exit(0)

print_header("TMF INGESTION AGENT  |  TrialAxis CRO  |  Auto Mode")

# ── Counters ──────────────────────────────────────────────────────────────────
results = {"ingested": 0, "duplicate": 0, "unregistered": 0, "failed": 0}

# ── Pass 1: Inbox ─────────────────────────────────────────────────────────────
if inbox_pdfs:
    print(f"\n  INBOX: {len(inbox_pdfs)} file(s) found")
    print("-" * 60)

    for pdf in inbox_pdfs:
        print_file_banner(pdf.name, pdf.stat().st_size // 1024)
        outcome = run_pipeline(pdf_path=pdf)
        results[outcome] += 1
        # Safety net: remove from inbox regardless of outcome so nothing lingers
        if pdf.exists():
            pdf.unlink()
        print()
        if outcome == "ingested":
            print(f"  >> INGESTED: {pdf.name}")
        elif outcome == "duplicate":
            print(f"  >> DUPLICATE: {pdf.name} already in portfolio.")
        elif outcome == "unregistered":
            print(f"  >> UNREGISTERED: {pdf.name} moved to unregistered/.")
        else:
            print(f"  >> FAILED: {pdf.name}")

# ── Pass 2: Recheck unregistered/ ─────────────────────────────────────────────
# Refresh list — new files may have landed there during Pass 1
unregistered_pdfs = sorted(UNREGISTERED_DIR.glob("*.pdf"))

if unregistered_pdfs:
    print()
    print(f"  RECHECK: {len(unregistered_pdfs)} file(s) in unregistered/")
    print("-" * 60)

    for pdf in unregistered_pdfs:
        print_file_banner(pdf.name, pdf.stat().st_size // 1024)
        outcome = run_pipeline(pdf_path=pdf)
        results[outcome] += 1
        print()
        if outcome == "ingested":
            print(f"  >> NOW REGISTERED: {pdf.name} ingested successfully.")
        elif outcome == "duplicate":
            print(f"  >> DUPLICATE: {pdf.name} already in portfolio.")
        elif outcome == "unregistered":
            print(f"  >> STILL UNREGISTERED: {pdf.name} — add to Excel registry.")
        else:
            print(f"  >> FAILED: {pdf.name}")

# ── Summary ───────────────────────────────────────────────────────────────────
total = sum(results.values())
print()
print("=" * 60)
print("  RUN COMPLETE")
print(f"  Total processed : {total}")
print(f"  Ingested        : {results['ingested']}")
print(f"  Duplicates      : {results['duplicate']}")
print(f"  Unregistered    : {results['unregistered']}")
print(f"  Failed          : {results['failed']}")
if results["ingested"] > 0:
    print()
    print("  Restart Streamlit to see new studies in the dashboard.")
print("=" * 60)

if results["failed"] > 0:
    sys.exit(1)
