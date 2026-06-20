import chromadb
import os
from typing import List, Optional

_client = None

def get_chroma_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=os.getenv("CHROMA_PATH", "./chroma_db")
        )
    return _client

def get_collection(session_id: str):
    client = get_chroma_client()
    safe_id = "".join(
        c if c.isalnum() or c == "_" else "_" for c in session_id
    )
    return client.get_or_create_collection(
        name=f"session_{safe_id}",
        metadata={"hnsw:space": "cosine", "dimension": 384},
    )

def add_chunks(session_id: str, chunks: List[dict]):
    collection = get_collection(session_id)
    collection.add(
        ids=[f"{c['doc_id']}_chunk_{c['chunk_index']}" for c in chunks],
        embeddings=[c["embedding"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[
            {
                "doc_id": c["doc_id"],
                "filename": c["filename"],
                "chunk_index": c["chunk_index"],
            }
            for c in chunks
        ],
    )

def query_chunks(
    session_id: str,
    query_embedding: List[float],
    n_results: int = 5,
    doc_ids: Optional[List[str]] = None,
):
    collection = get_collection(session_id)

    # Build the where filter scoped to the provided doc_ids
    # ChromaDB's $in operator requires at least 2 values — handle 0 and 1 separately
    where = None
    if doc_ids:
        if len(doc_ids) == 1:
            where = {"doc_id": {"$eq": doc_ids[0]}}
        else:
            where = {"doc_id": {"$in": doc_ids}}

    # Clamp n_results so it never exceeds the number of items in the collection
    try:
        count = collection.count()
    except Exception:
        count = n_results

    # If the collection is empty or scoped doc has no chunks, return empty
    if count == 0:
        return []

    effective_n = min(n_results, count)

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=effective_n,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        return []

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append({
            "text": doc,
            "metadata": meta,
            "score": round(1 - dist, 4),
        })
    return chunks

def delete_doc_chunks(session_id: str, doc_id: str):
    collection = get_collection(session_id)
    try:
        collection.delete(where={"doc_id": doc_id})
    except Exception:
        pass

def clear_session_chunks(session_id: str):
    """Delete ALL chunks for a session (used when resetting)."""
    client = get_chroma_client()
    safe_id = "".join(
        c if c.isalnum() or c == "_" else "_" for c in session_id
    )
    name = f"session_{safe_id}"
    try:
        client.delete_collection(name)
    except Exception:
        pass