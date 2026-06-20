import json
import logging
import os
from typing import List, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Document, ExcelMeta, ChatSession, ChatMessage
import uuid
from sqlalchemy.sql import func
from models.schemas import ChatRequest
from services.embedder import embed_query
from services.vector_store import query_chunks
from services.reranker import rerank_chunks
from services.llm import stream_response, get_model_for_file_type, get_prompt_for_file_type, build_rag_prompt, _TEXT_MODEL, client as llm_client, SYSTEM_PROMPT
from services.intent_classifier import classify_intent
from services.excel_agent import run_calculation
from services.excel_updater import run_update
from services.excel_processor import load_excel_meta_from_db
from services.docx_editor import stream_docx_edit

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Helpers ────────────────────────────────────────────────────────────────────

def normalize_scores(chunks: list) -> list:
    if not chunks:
        return chunks
    scores = [c["rerank_score"] for c in chunks]
    lo, hi = min(scores), max(scores)
    diff = hi - lo
    for c in chunks:
        c["rerank_score"] = (
            1.0 if diff == 0
            else round((c["rerank_score"] - lo) / diff, 3)
        )
    return chunks

def _save_message(db: Session, session_id: str, role: str, content: str, sources: list = None, session_type: str = "chat"):
    try:
        # 1. Ensure the parent ChatSession exists first to avoid FK constraint violation in MySQL
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            title = content[:40] + "..." if len(content) > 40 else content
            session = ChatSession(id=session_id, title=title, session_type=session_type)
            db.add(session)
            db.flush()  # Insert ChatSession first
        else:
            session.updated_at = func.now()
            if session_type != "chat" or not session.session_type:
                session.session_type = session_type
            db.flush()

        # 2. Add the child ChatMessage safely
        msg = ChatMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            sources=json.dumps(sources) if sources else None
        )
        db.add(msg)
        db.commit()
    except Exception as e:
        logger.error(f"[Chat] Failed to save message: {e}")
        db.rollback()


def _get_excel_docs(
    session_id: str,
    doc_ids: Optional[List[str]],
    db: Session,
) -> List[Document]:
    """Return Document rows that are Excel files for this session."""
    q = (
        db.query(Document)
        .filter(
            Document.session_id == session_id,
            Document.is_excel   == True,
            Document.status     == "ready",
        )
    )
    if doc_ids:
        q = q.filter(Document.id.in_(doc_ids))
    return q.all()


def _collect_excel_columns(excel_docs: List[Document], db: Session) -> List[str]:
    """Gather all column names from every active Excel document."""
    all_cols: List[str] = []
    for doc in excel_docs:
        meta = load_excel_meta_from_db(doc.id, db)
        for sheet_cols in meta.get("columns", {}).values():
            all_cols.extend(sheet_cols)
    return list(dict.fromkeys(all_cols))   # deduplicate, preserve order


def _pick_excel_meta(
    excel_docs: List[Document],
    db: Session,
    sheet_hint: Optional[str] = None,
) -> tuple:
    """
    Pick the best Excel document to operate on and return (meta_dict, storage_path).
    Strategy: most recently uploaded, or the one whose sheet names match sheet_hint.
    """
    if not excel_docs:
        return {}, ""

    target_doc = excel_docs[0]   # sorted desc by upload (most recent first)

    if sheet_hint:
        for doc in excel_docs:
            m = load_excel_meta_from_db(doc.id, db)
            if any(sheet_hint.lower() in s.lower() for s in m.get("sheet_names", [])):
                target_doc = doc
                break

    meta = load_excel_meta_from_db(target_doc.id, db)
    return meta, meta.get("storage_path", "")


# ── Main endpoint ──────────────────────────────────────────────────────────────

@router.post("/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):

    # Deduce session type: if there are documents, it is "docs". Otherwise, it is "chat" (General).
    has_docs = db.query(Document).filter(Document.session_id == request.session_id).count() > 0
    has_medical = db.query(Document).filter(
        Document.session_id == request.session_id,
        Document.file_type == "medical_image"
    ).count() > 0
    session_type = "medical" if has_medical else ("docs" if has_docs else "chat")

    # ── 1. Find Excel docs active in this session ────────────────────────────
    excel_docs = _get_excel_docs(request.session_id, request.document_ids, db)
    has_excel  = len(excel_docs) > 0

    # Save user message immediately
    _save_message(db, request.session_id, "user", request.message, session_type=session_type)

    # ── 2. Classify intent ───────────────────────────────────────────────────
    excel_cols    = _collect_excel_columns(excel_docs, db) if has_excel else []
    intent_result = classify_intent(
        query         = request.message,
        has_excel     = has_excel,
        excel_columns = excel_cols,
    )

    logger.info(
        "[Chat] session=%s intent=%s has_excel=%s",
        request.session_id[:8], intent_result.intent, has_excel,
    )

    # ── 3a. CALCULATION path ─────────────────────────────────────────────────
    if intent_result.intent == "CALCULATION" and has_excel:
        meta, storage_path = _pick_excel_meta(
            excel_docs, db, intent_result.sheet_hint
        )
        if not storage_path or not os.path.exists(storage_path):
            logger.warning("[Chat] Excel file not found on disk — falling back to RAG")
        else:
            def calc_stream():
                full_text = ""
                # No source citations for calculations — data comes directly from the file
                yield f"data: {json.dumps({'type': 'sources', 'sources': []})}\n\n"
                for chunk in run_calculation(
                    query        = request.message,
                    excel_meta   = meta,
                    storage_path = storage_path,
                    sheet_hint   = intent_result.sheet_hint,
                ):
                    full_text += chunk.get("text", "")
                    yield f"data: {json.dumps(chunk)}\n\n"
                yield "data: [DONE]\n\n"
                _save_message(db, request.session_id, "assistant", full_text, session_type=session_type)

            return StreamingResponse(calc_stream(), media_type="text/event-stream")

    # ── 3b. UPDATE path ──────────────────────────────────────────────────────
    if intent_result.intent == "UPDATE" and has_excel:
        meta, storage_path = _pick_excel_meta(
            excel_docs, db, intent_result.sheet_hint
        )
        excel_doc_id = excel_docs[0].id if excel_docs else None

        if not storage_path or not os.path.exists(storage_path):
            logger.warning("[Chat] Excel file not found on disk — falling back to RAG")
        else:
            def update_stream():
                full_text = ""
                # No source citations for updates — changes go directly to the file
                yield f"data: {json.dumps({'type': 'sources', 'sources': []})}\n\n"
                for chunk in run_update(
                    query        = request.message,
                    excel_meta   = meta,
                    storage_path = storage_path,
                    sheet_hint   = intent_result.sheet_hint,
                ):
                    full_text += chunk.get("text", "")
                    yield f"data: {json.dumps(chunk)}\n\n"
                # After a successful update, emit a download event so the UI shows a button
                if excel_doc_id and "\u2705" in full_text:
                    yield f"data: {json.dumps({'type': 'download', 'doc_id': excel_doc_id})}\n\n"
                yield "data: [DONE]\n\n"
                _save_message(db, request.session_id, "assistant", full_text, session_type=session_type)

            return StreamingResponse(update_stream(), media_type="text/event-stream")

    # ── 3c. DOCX_EDIT path ───────────────────────────────────────────────────
    if intent_result.intent == "DOCX_EDIT":
        query_embedding = embed_query(request.message)
        candidates = query_chunks(
            session_id      = request.session_id,
            query_embedding = query_embedding,
            n_results       = 8,
            doc_ids         = request.document_ids,
        )
        chunks = rerank_chunks(query=request.message, chunks=candidates, top_k=5) if candidates else []

        def docx_edit_stream():
            full_text = ""
            # No source citations — AI is editing content, not citing it
            yield "data: " + json.dumps({"type": "sources", "sources": []}) + "\n\n"
            # Signal frontend to render this as a styled DOCX edit block
            yield "data: " + json.dumps({"type": "docx_edit_start"}) + "\n\n"
            for token in stream_docx_edit(
                instruction = request.message,
                chunks      = chunks,
            ):
                full_text += token.get("text", "")
                yield "data: " + json.dumps(token) + "\n\n"
            yield "data: [DONE]\n\n"
            _save_message(db, request.session_id, "assistant", full_text, session_type=session_type)

        return StreamingResponse(docx_edit_stream(), media_type="text/event-stream")

    # ── 3d. RETRIEVAL path (RAG) ─────────────────────────────────────────────
    query_embedding = embed_query(request.message)

    candidates = query_chunks(
        session_id      = request.session_id,
        query_embedding = query_embedding,
        n_results       = 20,
        doc_ids         = request.document_ids,
    )

    if not candidates:
        def empty_stream():
            msg = "No documents found for this session. Please upload a document first."
            yield f"data: {json.dumps({'type': 'sources', 'sources': []})}\n\n"
            yield f"data: {json.dumps({'type': 'text', 'text': msg})}\n\n"
            yield "data: [DONE]\n\n"
            _save_message(db, request.session_id, "assistant", msg, session_type=session_type)
        return StreamingResponse(empty_stream(), media_type="text/event-stream")

    chunks = rerank_chunks(query=request.message, chunks=candidates, top_k=5)
    chunks = normalize_scores(chunks)

    # ── Detect dominant file_type for model/prompt routing ───────────────────
    # If any document in the result set is a medical_image, we use the
    # medical system prompt so the answer reads as a clinical/educational
    # response — not a generic text-document RAG reply.
    #
    # Strategy: pick the file_type of the highest-scoring retrieved chunk,
    # or fall back to querying the DB for the session's documents.
    dominant_file_type = "default"
    if request.document_ids:
        # Check each doc_id against the DB to find any medical_image
        for doc_id in request.document_ids:
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if doc and doc.file_type == "medical_image":
                dominant_file_type = "medical_image"
                break
    else:
        # No specific doc_ids — check all ready docs in the session
        session_docs = (
            db.query(Document)
            .filter(
                Document.session_id == request.session_id,
                Document.status     == "ready",
            )
            .all()
        )
        for doc in session_docs:
            if doc.file_type == "medical_image":
                dominant_file_type = "medical_image"
                break

    selected_model  = get_model_for_file_type(dominant_file_type)
    selected_prompt = get_prompt_for_file_type(dominant_file_type)

    logger.info(
        "[Chat] RAG routing — file_type=%s model=%s session=%s",
        dominant_file_type, selected_model, request.session_id[:8],
    )

    def rag_stream():
        sources = [
            {
                "filename": c["metadata"]["filename"],
                "text":     c["text"][:200],
                "score":    c["rerank_score"],
            }
            for c in chunks
        ]
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

        full_text = ""

        if selected_model == _TEXT_MODEL:
            # Standard text RAG — use existing stream_response() helper
            for token in stream_response(request.message, chunks):
                full_text += token.get("text", "")
                yield f"data: {json.dumps(token)}\n\n"
        else:
            # Vision-capable model path — build the same RAG prompt but send
            # it with the correct model and system prompt via the Groq client.
            prompt = build_rag_prompt(request.message, chunks)
            try:
                stream = llm_client.chat.completions.create(
                    model=selected_model,
                    messages=[
                        {"role": "system", "content": selected_prompt},
                        {"role": "user",   "content": prompt},
                    ],
                    stream=True,
                    max_tokens=4096,
                    temperature=0.1,
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        token = {"type": "text", "text": delta.content}
                        full_text += delta.content
                        yield f"data: {json.dumps(token)}\n\n"
            except Exception as exc:
                logger.error("[Chat] Vision RAG stream error: %s", exc)
                err_token = {
                    "type": "text",
                    "text": f"Sorry, an error occurred generating the response. ({str(exc)[:120]})"
                }
                full_text += err_token["text"]
                yield f"data: {json.dumps(err_token)}\n\n"

        yield "data: [DONE]\n\n"
        _save_message(db, request.session_id, "assistant", full_text, sources, session_type=session_type)

    return StreamingResponse(rag_stream(), media_type="text/event-stream")