import json
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import ChatSession, ChatMessage, Document

router = APIRouter()

class SessionResponse(BaseModel):
    id: str
    title: str
    session_type: str
    created_at: str
    updated_at: str

class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    timestamp: str
    sources: Optional[list] = []

@router.get("/sessions", response_model=List[SessionResponse])
def get_sessions(session_type: Optional[str] = None, db: Session = Depends(get_db)):
    """Fetch all sessions ordered by most recent update, optionally filtered by type."""
    query = db.query(ChatSession)
    if session_type:
        query = query.filter(ChatSession.session_type == session_type)
    sessions = query.order_by(ChatSession.updated_at.desc()).all()
    
    result = []
    for s in sessions:
        result.append({
            "id": s.id,
            "title": s.title or "New Chat",
            "session_type": s.session_type or "chat",
            "created_at": s.created_at.isoformat() if s.created_at else "",
            "updated_at": s.updated_at.isoformat() if s.updated_at else ""
        })
    return result

@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
def get_session_messages(session_id: str, db: Session = Depends(get_db)):
    """Fetch all messages for a specific session."""
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()
    
    result = []
    for m in messages:
        sources = []
        if m.sources:
            try:
                sources = json.loads(m.sources)
            except Exception:
                pass
                
        result.append({
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "timestamp": m.created_at.isoformat() if m.created_at else "",
            "sources": sources
        })
    return result

@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    """Delete a session, its messages, and clear documents from DB."""
    # Delete messages
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    
    # Delete documents reference
    db.query(Document).filter(Document.session_id == session_id).delete()
    
    # Delete session
    db.query(ChatSession).filter(ChatSession.id == session_id).delete()
    
    db.commit()
    return {"status": "success", "message": "Session deleted"}
