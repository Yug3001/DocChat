"""
website.py
──────────
Endpoint: POST /api/website/ingest
Accepts a URL + session_id, scrapes the website, and processes it
through the EXACT same chunker/embedder/vector_store pipeline as upload.py.

No new logic is introduced here — only composition of existing services.
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Document, ChatSession
from models.schemas import DocumentOut
from services.web_scraper import scrape_website
from services.chunker import chunk_text
from services.embedder import embed_chunks
from services.vector_store import add_chunks

logger = logging.getLogger(__name__)
router = APIRouter()


class WebsiteIngestRequest(BaseModel):
    url: str
    session_id: str
    crawl_links: bool = True
    max_pages: int = 5


class WebsiteIngestResponse(BaseModel):
    document: DocumentOut
    message: str
    pages_scraped: int


@router.post("/website/ingest", response_model=WebsiteIngestResponse)
def ingest_website(
    request: WebsiteIngestRequest,
    db: Session = Depends(get_db),
):
    """
    Scrape a website and ingest its content into the RAG pipeline.
    Reuses chunker.py, embedder.py, and vector_store.py exactly as upload.py does.
    Stores the result as a Document with file_type='website'.
    """
    # Validate max_pages
    if request.max_pages < 1:
        request.max_pages = 1
    if request.max_pages > 20:
        request.max_pages = 20

    # ── 1. Scrape ─────────────────────────────────────────────────────────────
    try:
        site_title, combined_text, pages_scraped = scrape_website(
            url          = request.url,
            crawl_links  = request.crawl_links,
            max_pages    = request.max_pages,
        )
    except Exception as exc:
        logger.error("[Website] Scrape failed for %s: %s", request.url, exc)
        raise HTTPException(status_code=400, detail=f"Failed to scrape website: {str(exc)}")

    if not combined_text.strip():
        raise HTTPException(status_code=400, detail="No readable content found at the provided URL.")

    # ── 2. Create Document record ─────────────────────────────────────────────
    doc_id   = str(uuid.uuid4())
    filename = site_title[:200] if site_title else request.url[:200]

    db_doc = Document(
        id                = doc_id,
        filename          = filename,
        original_filename = request.url,   # store the URL as original_filename for reference
        file_type         = "website",
        session_id        = request.session_id,
        storage_path      = request.url,   # no file on disk; store URL instead
        file_size         = len(combined_text.encode("utf-8")),
        is_excel          = False,
        status            = "processing",
        chunk_count       = 0,
    )
    db.add(db_doc)

    # Create/update chat session title
    session = db.query(ChatSession).filter(ChatSession.id == request.session_id).first()
    if not session:
        session = ChatSession(id=request.session_id, title=filename, session_type="web")
        db.add(session)
    else:
        session.session_type = "web"
        if not session.title or session.title == "New Chat":
            session.title = filename

    db.commit()

    # ── 3. Chunk → Embed → Store (exact same pipeline as upload.py) ───────────
    try:
        chunks = chunk_text(combined_text, doc_id, filename)
        chunks_with_embeddings = embed_chunks(chunks)
        add_chunks(request.session_id, chunks_with_embeddings)
        num_chunks = len(chunks)

        db_doc.chunk_count = num_chunks
        db_doc.status      = "ready"
        db.commit()

    except Exception as exc:
        logger.error("[Website] Processing failed for %s: %s", request.url, exc)
        db_doc.status = "error"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(exc)}")

    db.refresh(db_doc)
    return WebsiteIngestResponse(
        document      = DocumentOut.model_validate(db_doc),
        message       = f"Scraped {pages_scraped} page(s), processed {num_chunks} chunks.",
        pages_scraped = pages_scraped,
    )
