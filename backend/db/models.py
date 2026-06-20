from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean
from sqlalchemy.sql import func
from .database import Base


class Document(Base):
    __tablename__ = "documents"

    id                = Column(String(36), primary_key=True)
    filename          = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=True)
    file_type         = Column(String(20), nullable=False)
    session_id        = Column(String(36), nullable=False, index=True)
    storage_path      = Column(String(512), nullable=False)
    chunk_count       = Column(Integer, default=0)
    file_size         = Column(Integer, default=0)
    is_excel          = Column(Boolean, default=False)          # fast Excel flag
    uploaded_at       = Column(DateTime(timezone=True), server_default=func.now())
    status            = Column(String(20), default="processing")


class ExcelMeta(Base):
    """Stores structural metadata for every uploaded Excel file."""
    __tablename__ = "excel_metadata"

    id           = Column(String(36), primary_key=True)   # same as documents.id
    doc_id       = Column(String(36), nullable=False, index=True)
    session_id   = Column(String(36), nullable=False, index=True)
    filename     = Column(String(255), nullable=False)
    # JSON-serialised strings (Text works across MySQL 5.6+, SQLite, Postgres)
    sheet_names  = Column(Text, nullable=False)            # JSON list
    columns      = Column(Text, nullable=False)            # JSON {sheet: [cols]}
    row_counts   = Column(Text, nullable=False)            # JSON {sheet: n}
    dtypes       = Column(Text, nullable=False)            # JSON {sheet: {col: dtype}}
    storage_path = Column(String(512), nullable=False)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id           = Column(String(36), primary_key=True)
    title        = Column(String(255), default="New Chat")
    session_type = Column(String(20), default="chat", nullable=False)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id         = Column(String(36), primary_key=True)
    session_id = Column(String(36), nullable=False, index=True)
    role       = Column(String(20), nullable=False)
    content    = Column(Text, nullable=False)
    sources    = Column(Text, nullable=True)   # JSON string for citations
    created_at = Column(DateTime(timezone=True), server_default=func.now())