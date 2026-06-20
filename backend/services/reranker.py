from sentence_transformers.cross_encoder import CrossEncoder
import os
from typing import List

_reranker = None

def get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        model_name = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        _reranker = CrossEncoder(model_name)
    return _reranker

def rerank_chunks(query: str, chunks: List[dict], top_k: int = 3) -> List[dict]:
    if not chunks:
        return chunks

    reranker = get_reranker()

    # Build (query, chunk_text) pairs for the cross-encoder
    pairs = [[query, chunk["text"]] for chunk in chunks]

    # Score each pair — cross-encoder reads both together
    scores = reranker.predict(pairs)

    # Attach rerank score to each chunk
    for chunk, score in zip(chunks, scores):
        chunk["rerank_score"] = float(score)

    # Sort by rerank score descending, return top_k
    reranked = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)
    return reranked[:top_k]