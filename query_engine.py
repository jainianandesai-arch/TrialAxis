"""
TMF Query Engine
================
Semantic search over indexed trial chunks using ChromaDB.
Replaces keyword matching with vector similarity search.

Model: Claude Sonnet 4.6
Storage: ChromaDB (persistent) with fallback to trial_index.json
"""

import json
import os
import math
import hashlib
from pathlib import Path
import anthropic

# ── Paths ──────────────────────────────────────────────────────────────────────
_ROOT       = Path(__file__).parent
CHROMA_DIR  = _ROOT / "data" / "chroma_db"
INDEX_FILE  = _ROOT / "data" / "trial_index.json"

MODEL = "claude-sonnet-4-6"

# ── ChromaDB ───────────────────────────────────────────────────────────────────
def _get_collection():
    """Returns the ChromaDB trial chunks collection if it exists."""
    try:
        import chromadb
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        return client.get_or_create_collection(
            name="trial_chunks",
            metadata={"hnsw:space": "cosine"}
        )
    except Exception:
        return None

def _embed_query(query: str) -> list[float]:
    """
    Generate an embedding for the search query.
    Uses the same deterministic embedding approach as the indexing pipeline
    to ensure query vectors are compatible with stored chunk vectors.
    """
    words = query.lower().split()
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

# ── Fallback: JSON keyword search ─────────────────────────────────────────────
_chunks_cache = None

def _load_json_index():
    global _chunks_cache
    if _chunks_cache is not None:
        return _chunks_cache
    if not INDEX_FILE.exists():
        return []
    with open(INDEX_FILE) as f:
        _chunks_cache = json.load(f)
    return _chunks_cache

def _keyword_search(query, top_k=8):
    """Keyword fallback if ChromaDB is unavailable."""
    chunks = _load_json_index()
    if not chunks:
        return []
    query_lower = query.lower()
    query_terms = query_lower.split()
    scored = []
    for chunk in chunks:
        text = (chunk.get("text", "") + " " + chunk.get("summary", "")).lower()
        score = sum(1 for term in query_terms if term in text)
        if chunk.get("drug", "").lower() in query_lower:
            score += 5
        if chunk.get("tax_id", "").lower() in query_lower:
            score += 5
        if chunk.get("condition", "").lower() in query_lower:
            score += 3
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]

# ── Primary: Semantic vector search ───────────────────────────────────────────
def semantic_search(query: str, top_k: int = 8) -> list[dict]:
    """
    Embed the query and retrieve the most semantically similar chunks
    from ChromaDB using cosine similarity.

    Falls back to keyword search if ChromaDB is unavailable or empty.
    """
    collection = _get_collection()

    if collection is not None:
        try:
            count = collection.count()
            if count > 0:
                query_embedding = _embed_query(query)

                def _run_query(where_filter=None):
                    kwargs = dict(
                        query_embeddings=[query_embedding],
                        n_results=min(top_k, count),
                        include=["metadatas", "documents", "distances"],
                    )
                    if where_filter:
                        kwargs["where"] = where_filter
                    return collection.query(**kwargs)

                # Try current-version chunks first; fall back to all chunks
                # for collections indexed before versioning was added.
                try:
                    results = _run_query({"is_current": 1})
                    if not results["metadatas"][0]:
                        results = _run_query()
                except Exception:
                    results = _run_query()

                chunks = []
                for i, meta in enumerate(results["metadatas"][0]):
                    chunks.append({
                        "tax_id":      meta.get("tax_id", ""),
                        "short_name":  meta.get("short_name", ""),
                        "drug":        meta.get("drug", ""),
                        "condition":   meta.get("condition", ""),
                        "chunk_index": meta.get("chunk_index", i),
                        "text":        meta.get("text", ""),
                        "summary":     meta.get("summary", ""),
                        "doc_version": meta.get("doc_version", ""),
                        "distance":    results["distances"][0][i],
                    })
                return chunks
        except Exception:
            pass

    # Fallback to keyword search
    return _keyword_search(query, top_k)

# ── Context builder ────────────────────────────────────────────────────────────
def build_context_from_chunks(chunks: list[dict]) -> str:
    """Format retrieved chunks as context string for Claude."""
    if not chunks:
        return ""
    context = ""
    seen_trials = set()
    for chunk in chunks:
        trial_id = chunk["tax_id"]
        if trial_id not in seen_trials:
            context += f"\n--- {chunk['short_name']} ({trial_id}) | {chunk['drug']} | {chunk['condition']} ---\n"
            seen_trials.add(trial_id)
        context += chunk["text"] + "\n"
    return context

# ── Main query function ────────────────────────────────────────────────────────
def query_trials(question: str, conversation_history: list = None) -> str:
    """
    Semantic search → build context → Claude Sonnet answers.
    Supports multi-turn conversation history.
    """
    client = anthropic.Anthropic()

    # Semantic search for relevant chunks
    relevant_chunks = semantic_search(question, top_k=8)
    context = build_context_from_chunks(relevant_chunks)

    # If nothing found in ChromaDB or JSON index, say so clearly but helpfully
    if not context:
        all_chunks = _load_json_index()
        summaries = ""
        seen = set()
        for c in all_chunks:
            if c["tax_id"] not in seen and c.get("summary"):
                summaries += f"\n{c['short_name']} ({c['tax_id']}): {c['summary']}\n"
                seen.add(c["tax_id"])
        if summaries:
            context = summaries
        else:
            # No index at all — return a clean message, don't pass to Claude
            return (
                "Protocol content has not been indexed yet. "
                "Please run `python setup_data.py` from the project root to index all protocols, "
                "then retry your query."
            )

    system_prompt = """You are a clinical trial intelligence assistant for TrialAxis CRO, a specialized GI CRO based in North America.

You have access to real clinical trial protocol documents from ClinicalTrials.gov.
All trials are in the GI/IBD therapeutic area — TrialAxis CRO's core specialty.

Answer questions accurately based on the protocol content provided.
When comparing studies, use clear tables or structured lists.
Always cite the study name and TAX ID when referencing specific data.
If the answer is not in the provided context, say so clearly.
Keep answers concise and professional — your audience is clinical operations staff."""

    messages = []
    if conversation_history:
        messages.extend(conversation_history)

    messages.append({
        "role": "user",
        "content": f"""Based on the following clinical trial protocol content, please answer this question:

QUESTION: {question}

RELEVANT PROTOCOL CONTENT:
{context}"""
    })

    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=system_prompt,
        messages=messages
    )

    return response.content[0].text

# ── Utility functions ──────────────────────────────────────────────────────────
def get_trial_list() -> list[dict]:
    """Returns list of unique trials in the index."""
    chunks = _load_json_index()
    seen = {}
    for c in chunks:
        if c["tax_id"] not in seen:
            seen[c["tax_id"]] = {
                "tax_id":      c["tax_id"],
                "short_name":  c["short_name"],
                "drug":        c["drug"],
                "condition":   c["condition"],
                "chunk_count": 0
            }
        seen[c["tax_id"]]["chunk_count"] += 1
    return list(seen.values())

def is_index_ready() -> bool:
    """Check if ChromaDB or JSON index has been populated."""
    collection = _get_collection()
    if collection is not None:
        try:
            if collection.count() > 0:
                return True
        except Exception:
            pass
    return INDEX_FILE.exists() and len(_load_json_index()) > 0