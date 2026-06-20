from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from db.database import get_db
from db.models import Document, ExcelMeta
from models.schemas import DocumentOut
from services.vector_store import delete_doc_chunks, clear_session_chunks
from fastapi.responses import FileResponse
import os

router = APIRouter()

@router.get("/documents/{session_id}", response_model=List[DocumentOut])
def list_documents(session_id: str, db: Session = Depends(get_db)):
    docs = (
        db.query(Document)
        .filter(Document.session_id == session_id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )
    return docs

@router.delete("/documents/{doc_id}")
def delete_document(doc_id: str, session_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    delete_doc_chunks(session_id, doc_id)
    db.delete(doc)
    db.commit()
    return {"message": "Deleted successfully"}

@router.delete("/session/{session_id}/clear")
def clear_session(session_id: str, db: Session = Depends(get_db)):
    """
    Delete ALL documents and vector data for a session.
    Called when the user starts a fresh session.
    """
    docs = db.query(Document).filter(Document.session_id == session_id).all()
    for doc in docs:
        db.delete(doc)
    db.commit()
    # Also wipe the ChromaDB collection for this session
    clear_session_chunks(session_id)
    return {"message": f"Session {session_id} cleared successfully"}

@router.get("/download/{doc_id}")
def download_document(doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Prefer the storage_path field stored at upload time
    file_path = doc.storage_path if doc.storage_path else None

    # Fallback: check excel_metadata for the path
    if not file_path or not os.path.exists(file_path):
        if doc.is_excel:
            meta = db.query(ExcelMeta).filter(ExcelMeta.doc_id == doc_id).first()
            if meta and meta.storage_path and os.path.exists(meta.storage_path):
                file_path = meta.storage_path

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=file_path,
        filename=doc.original_filename or doc.filename,
        media_type="application/octet-stream",
    )