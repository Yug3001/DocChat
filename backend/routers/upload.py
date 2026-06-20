from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid, os, re
from pathlib import Path

from db.database import get_db
from db.models import Document, ChatSession
from models.schemas import UploadResponse, DocumentOut
from services.parser import parse_file
from services.chunker import chunk_text
from services.embedder import embed_chunks
from services.vector_store import add_chunks
from services.excel_processor import process_excel, build_excel_summary

router = APIRouter()

# ── MIME-type → extension ──────────────────────────────────────────────────────
ALLOWED_TYPES = {
    "application/pdf":                                                        "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document":"docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":      "xlsx",
    "application/vnd.ms-excel":                                               "xls",
    "image/png":   "png",
    "image/jpeg":  "jpg",
    "image/jpg":   "jpg",
    "image/webp":  "webp",
    "application/octet-stream": None,   # fall back to extension sniffing
}

EXTENSION_MAP = {
    ".pdf":  "pdf",
    ".docx": "docx",
    ".xlsx": "xlsx",
    ".xls":  "xls",
    ".png":  "png",
    ".jpg":  "jpg",
    ".jpeg": "jpg",
    ".webp": "webp",
}

EXCEL_TYPES = {"xlsx", "xls"}

STORAGE_PATH = os.getenv("STORAGE_PATH", "./storage")


def _safe_name(name: str) -> str:
    """Sanitize a filename — keep letters, digits, dots, hyphens, underscores."""
    stem = Path(name).stem
    safe = re.sub(r'[^\w\-.]', '_', stem)[:80].strip('_')
    return safe or "file"


def _resolve_file_type(file: UploadFile) -> str:
    ct = (file.content_type or "").split(";")[0].strip().lower()
    if ct in ALLOWED_TYPES and ALLOWED_TYPES[ct] is not None:
        return ALLOWED_TYPES[ct]
    if file.filename:
        ext = Path(file.filename).suffix.lower()
        if ext in EXTENSION_MAP:
            return EXTENSION_MAP[ext]
    raise HTTPException(
        status_code=400,
        detail=(
            f"Unsupported file type: '{file.content_type}'. "
            "Allowed: PDF, DOCX, XLSX, XLS, PNG, JPG, JPEG, WEBP."
        ),
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file:       UploadFile = File(...),
    session_id: str        = Form(...),
    db:         Session    = Depends(get_db),
):
    file_type = _resolve_file_type(file)
    doc_id    = str(uuid.uuid4())

    # ── Save file to disk ────────────────────────────────────────────────────
    # Create or update ChatSession title with the original filename
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        session = ChatSession(id=session_id, title=Path(file.filename).stem if file.filename else "New Chat", session_type="docs")
        db.add(session)
    else:
        session.session_type = "docs"
        if not session.title or session.title == "New Chat":
            session.title = Path(file.filename).stem if file.filename else "New Chat"

    # Use format: {doc_id}_{original_safe_name}.{ext}
    # This keeps the file identifiable when opened directly from the folder.
    os.makedirs(STORAGE_PATH, exist_ok=True)
    safe_stem = _safe_name(file.filename or "upload")
    save_filename = f"{doc_id}_{safe_stem}.{file_type}"
    save_path = os.path.join(STORAGE_PATH, save_filename)

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)
    file_size = len(content)

    is_excel = file_type in EXCEL_TYPES

    # ── Create DB record ─────────────────────────────────────────────────────
    db_doc = Document(
        id                = doc_id,
        filename          = file.filename,
        original_filename = file.filename,
        file_type         = file_type,
        session_id        = session_id,
        storage_path      = save_path,
        file_size         = file_size,
        is_excel          = is_excel,
        status            = "processing",
    )
    db.add(db_doc)
    

    
    db.commit()

    num_chunks = 0

    try:
        # ════════════════════════════════════════════════════════════════════
        # EXCEL PATH — structured processing
        # ════════════════════════════════════════════════════════════════════
        if is_excel:
            # 1. Extract metadata and store in excel_metadata table
            meta = process_excel(save_path, doc_id, session_id, file.filename, db)

            # 2. Build a text summary for ChromaDB (RAG fallback)
            summary_text = build_excel_summary(meta, file.filename)

            # 3. Chunk + embed the summary (same pipeline as other docs)
            chunks               = chunk_text(summary_text, doc_id, file.filename)
            chunks_with_embeddings = embed_chunks(chunks)
            add_chunks(session_id, chunks_with_embeddings)
            num_chunks = len(chunks)

        # ════════════════════════════════════════════════════════════════════
        # STANDARD PATH — PDF / DOCX / image (unchanged)
        # ════════════════════════════════════════════════════════════════════
        else:
            text = parse_file(save_path, file_type)
            if not text or not text.strip():
                text = (
                    f"[Image file uploaded: {file.filename}. "
                    "No text could be extracted via OCR. "
                    "Please describe what you see or ask questions about the image content.]"
                )
            chunks               = chunk_text(text, doc_id, file.filename)
            chunks_with_embeddings = embed_chunks(chunks)
            add_chunks(session_id, chunks_with_embeddings)
            num_chunks = len(chunks)

        db_doc.chunk_count = num_chunks
        db_doc.status      = "ready"
        db.commit()

    except Exception as exc:
        db_doc.status = "error"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(exc)}")

    db.refresh(db_doc)
    return UploadResponse(
        document=DocumentOut.model_validate(db_doc),
        message=f"Processed {num_chunks} chunks successfully.",
    )
