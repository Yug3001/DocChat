"""
routers/medical_upload.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Endpoint: POST /api/upload/medical

Dedicated upload handler for medical images (X-ray / MRI / CT / ultrasound).

FLOW:
  1. Validate that the uploaded file is an image (PNG, JPG, WEBP).
  2. Save the file to disk.
  3. Create a Document DB record with file_type = "medical_image".
  4. Call medical_vision.analyze_medical_image() → get structured analysis text.
  5. Chunk + embed the analysis text through the standard pipeline.
  6. Store chunks in ChromaDB so chat.py's RAG path can retrieve them.

This endpoint is intentionally separate from /api/upload so that:
  • Medical images ALWAYS go through the vision model, never OCR.
  • Regular images (screenshots, diagrams) still use /api/upload normally.
  • The document's file_type = "medical_image" lets chat.py use the correct
    system prompt for any follow-up RAG queries.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import logging
import os
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import ChatSession, Document
from models.schemas import DocumentOut, UploadResponse
from services.chunker import chunk_text
from services.embedder import embed_chunks
from services.medical_vision import analyze_medical_image
from services.vector_store import add_chunks

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Allowed image MIME types for medical uploads ──────────────────────────────
ALLOWED_MEDICAL_TYPES = {
    "image/png":  "png",
    "image/jpeg": "jpg",
    "image/jpg":  "jpg",
    "image/webp": "webp",
}

MEDICAL_EXTENSION_MAP = {
    ".png":  "png",
    ".jpg":  "jpg",
    ".jpeg": "jpg",
    ".webp": "webp",
}

STORAGE_PATH = os.getenv("STORAGE_PATH", "./storage")


def _safe_name(name: str) -> str:
    """Sanitize a filename — keep letters, digits, dots, hyphens, underscores."""
    stem = Path(name).stem
    safe = re.sub(r"[^\w\-.]", "_", stem)[:80].strip("_")
    return safe or "medical_image"


def _resolve_image_type(file: UploadFile) -> str:
    """
    Validate the uploaded file is an image and return its extension string.
    Raises 400 if the file is not an allowed image type.
    """
    ct = (file.content_type or "").split(";")[0].strip().lower()
    if ct in ALLOWED_MEDICAL_TYPES:
        return ALLOWED_MEDICAL_TYPES[ct]
    if file.filename:
        ext = Path(file.filename).suffix.lower()
        if ext in MEDICAL_EXTENSION_MAP:
            return MEDICAL_EXTENSION_MAP[ext]
    raise HTTPException(
        status_code=400,
        detail=(
            f"Unsupported file type for medical upload: '{file.content_type}'. "
            "Only image files are accepted here (PNG, JPG, JPEG, WEBP). "
            "Please upload an X-ray, MRI, CT scan, or ultrasound image."
        ),
    )


@router.post("/upload/medical", response_model=UploadResponse)
async def upload_medical_image(
    file:       UploadFile = File(...),
    session_id: str        = Form(...),
    db:         Session    = Depends(get_db),
):
    """
    Upload a medical image and perform automated clinical-style vision analysis.

    The analysis text is chunked, embedded, and stored in ChromaDB exactly
    like any other document — so chat.py's standard RAG pipeline can retrieve
    the findings when the user asks follow-up questions.
    """
    # ── 1. Validate file type ────────────────────────────────────────────────
    image_ext = _resolve_image_type(file)
    doc_id    = str(uuid.uuid4())

    # ── 2. Save file to disk ─────────────────────────────────────────────────
    os.makedirs(STORAGE_PATH, exist_ok=True)
    safe_stem     = _safe_name(file.filename or "medical_image")
    save_filename = f"{doc_id}_{safe_stem}.{image_ext}"
    save_path     = os.path.join(STORAGE_PATH, save_filename)

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)
    file_size = len(content)

    # ── 3. Create DB record — file_type = "medical_image" ────────────────────
    # This is the critical field: chat.py reads file_type from the Document
    # record and uses it to select the correct system prompt for RAG queries.
    db_doc = Document(
        id                = doc_id,
        filename          = file.filename,
        original_filename = file.filename,
        file_type         = "medical_image",   # ← key: distinguishes from plain images
        session_id        = session_id,
        storage_path      = save_path,
        file_size         = file_size,
        is_excel          = False,
        status            = "processing",
    )
    db.add(db_doc)

    # Create or update ChatSession title
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        title = Path(file.filename).stem if file.filename else "Medical Image"
        session = ChatSession(id=session_id, title=title, session_type="medical")
        db.add(session)
    else:
        session.session_type = "medical"
        if not session.title or session.title == "New Chat":
            session.title = Path(file.filename).stem if file.filename else "Medical Image"

    db.commit()

    # ── 4. Vision analysis + RAG ingestion ───────────────────────────────────
    num_chunks = 0
    try:
        logger.info(
            "[MedicalUpload] Starting vision analysis for %s (doc_id=%s)",
            file.filename, doc_id,
        )

        # Step 4a — call the Groq vision model to get clinical analysis text
        analysis_text = analyze_medical_image(save_path, file.filename or safe_stem)

        # Step 4b — prepend a clear header so retrieved chunks are clearly
        #            identified as medical image analysis in chat responses
        full_text = (
            f"[Medical Image Analysis: {file.filename}]\n"
            f"File type: {image_ext.upper()} medical image\n"
            f"{'=' * 60}\n\n"
            f"{analysis_text}"
        )

        # Step 4c — chunk → embed → store (identical pipeline to all other docs)
        chunks                 = chunk_text(full_text, doc_id, file.filename)
        chunks_with_embeddings = embed_chunks(chunks)
        add_chunks(session_id, chunks_with_embeddings)
        num_chunks = len(chunks)

        logger.info(
            "[MedicalUpload] Stored %d chunks for %s", num_chunks, file.filename
        )

        db_doc.chunk_count = num_chunks
        db_doc.status      = "ready"
        db.commit()

    except Exception as exc:
        logger.error("[MedicalUpload] Processing failed for %s: %s", file.filename, exc)
        db_doc.status = "error"
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Medical image analysis failed: {str(exc)}",
        )

    db.refresh(db_doc)
    return UploadResponse(
        document=DocumentOut.model_validate(db_doc),
        message=(
            f"Medical image analysed and indexed successfully "
            f"({num_chunks} chunks stored). "
            "You can now ask questions about the findings."
        ),
    )
