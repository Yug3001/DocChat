from fastapi import APIRouter
from services.vector_store import get_chroma_client

router = APIRouter()


@router.get("/debug/collections")
def list_collections():
    client = get_chroma_client()
    collections = client.list_collections()
    result = []
    for col in collections:
        collection = client.get_collection(col.name)
        count = collection.count()
        if count > 0:
            sample = collection.peek(limit=5)
            chunks_preview = [
                {
                    "id": sample["ids"][i],
                    "text_preview": sample["documents"][i][:150] + "...",
                    "metadata": sample["metadatas"][i],
                }
                for i in range(len(sample["ids"]))
            ]
        else:
            chunks_preview = []

        result.append({
            "collection_name": col.name,
            "total_chunks": count,
            "sample_chunks": chunks_preview,
        })
    return {"total_collections": len(result), "collections": result}


@router.get("/debug/collections/{collection_name}")
def get_collection_detail(collection_name: str):
    client = get_chroma_client()
    try:
        collection = client.get_collection(collection_name)
        count = collection.count()
        all_data = collection.get(
            include=["documents", "metadatas"]
        )
        chunks = [
            {
                "id": all_data["ids"][i],
                "text": all_data["documents"][i],
                "metadata": all_data["metadatas"][i],
            }
            for i in range(len(all_data["ids"]))
        ]
        return {
            "collection_name": collection_name,
            "total_chunks": count,
            "chunks": chunks,
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/debug/vectors/{collection_name}")
def get_vectors(collection_name: str, limit: int = 3):
    """
    Shows actual numerical vector data for chunks.
    limit = how many chunks to show (default 3, keep small)
    """
    client = get_chroma_client()
    try:
        collection = client.get_collection(collection_name)
        count = collection.count()

        data = collection.get(
            limit=limit,
            include=["documents", "metadatas", "embeddings"]
        )

        result = []
        for i in range(len(data["ids"])):
            vector = data["embeddings"][i]
            result.append({
                "chunk_id": data["ids"][i],
                "filename": data["metadatas"][i]["filename"],
                "chunk_index": data["metadatas"][i]["chunk_index"],
                "original_text": data["documents"][i],
                "vector_dimensions": len(vector),
                "vector_preview_first_10": [
                    round(v, 6) for v in vector[:10]
                ],
                "vector_preview_last_10": [
                    round(v, 6) for v in vector[-10:]
                ],
                "vector_full": [round(v, 6) for v in vector],
            })

        return {
            "collection_name": collection_name,
            "total_chunks_in_collection": count,
            "showing_chunks": limit,
            "explanation": (
                "Each chunk of text is converted into a list of "
                f"{len(data['embeddings'][0])} numbers (384-dimensional vector). "
                "Similar texts produce similar vectors. "
                "ChromaDB finds the closest vectors when you ask a question."
            ),
            "chunks_with_vectors": result,
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/debug/summary")
def get_summary():
    """
    Clean summary of everything stored — good for mentor demo
    """
    client = get_chroma_client()
    collections = client.list_collections()
    total_vectors = 0
    summary = []

    for col in collections:
        collection = client.get_collection(col.name)
        count = collection.count()
        total_vectors += count

        if count > 0:
            sample = collection.peek(limit=1)
            filenames = list(set([
                m["filename"]
                for m in sample["metadatas"]
            ]))
            # Get all metadatas to find unique files
            all_meta = collection.get(include=["metadatas"])
            unique_files = list(set([
                m["filename"] for m in all_meta["metadatas"]
            ]))
        else:
            unique_files = []

        summary.append({
            "session": col.name,
            "documents_uploaded": unique_files,
            "total_chunks_stored": count,
            "total_vectors_stored": count,
            "vector_size": "384 dimensions per vector",
        })

    return {
        "message": (
            "This is the ChromaDB vector database. "
            "Every document uploaded is split into chunks "
            "and each chunk is stored as a 384-dimensional vector."
        ),
        "total_vectors_in_database": total_vectors,
        "sessions": summary,
    }