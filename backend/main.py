from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import sqlalchemy as sa

load_dotenv()

from routers import upload, chat, documents, debug, sessions, website, medical_upload, dataset
from db.database import engine
from db import models
from services.embedder import get_model
from services.reranker import get_reranker

# ── Step 1: Create tables that don't exist yet ────────────────────────────────
models.Base.metadata.create_all(bind=engine)

# ── Step 2: Auto-migrate — add any missing columns to existing tables ─────────
_MIGRATIONS = [
    # (table,            column,       DDL type)
    ("documents",  "session_id",        "VARCHAR(36) NOT NULL DEFAULT ''"),
    ("documents",  "original_filename", "VARCHAR(255) NULL"),
    ("documents",  "storage_path",      "VARCHAR(512) NOT NULL DEFAULT ''"),
    ("documents",  "chunk_count",       "INT NOT NULL DEFAULT 0"),
    ("documents",  "file_size",         "INT NOT NULL DEFAULT 0"),
    ("documents",  "status",            "VARCHAR(20) NOT NULL DEFAULT 'processing'"),
    ("documents",  "uploaded_at",       "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"),
    ("documents",  "is_excel",          "TINYINT(1) NOT NULL DEFAULT 0"),
    ("chat_sessions", "session_type",   "VARCHAR(20) NOT NULL DEFAULT 'chat'"),
]
def _col_exists_mysql(conn, db_name, table, column):
    result = conn.execute(sa.text(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = :tbl AND COLUMN_NAME = :col"
    ), {"db": db_name, "tbl": table, "col": column})
    return result.scalar() > 0

def _col_exists_sqlite(conn, table, column):
    result = conn.execute(sa.text(f"PRAGMA table_info({table})"))
    return any(row[1] == column for row in result.fetchall())

def _col_exists_pg(conn, table, column):
    result = conn.execute(sa.text(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_name = :tbl AND column_name = :col"
    ), {"tbl": table, "col": column})
    return result.scalar() > 0

def _run_migrations():
    db_url    = os.getenv("DATABASE_URL", "")
    is_mysql  = "mysql"  in db_url
    is_sqlite = "sqlite" in db_url
    db_name   = db_url.split("/")[-1].split("?")[0] if is_mysql else ""

    with engine.connect() as conn:
        # ── Column migrations ─────────────────────────────────────────────
        for table, column, col_def in _MIGRATIONS:
            try:
                if is_mysql:
                    exists = _col_exists_mysql(conn, db_name, table, column)
                elif is_sqlite:
                    exists = _col_exists_sqlite(conn, table, column)
                else:
                    exists = _col_exists_pg(conn, table, column)

                if not exists:
                    conn.execute(sa.text(
                        f"ALTER TABLE {table} ADD COLUMN {column} {col_def}"
                    ))
                    conn.commit()
                    print(f"[Migration] Added column '{column}' to '{table}'")
                else:
                    print(f"[Migration] '{table}.{column}' OK")

            except Exception as e:
                print(f"[Migration] Warning for '{table}.{column}': {e}")
                try:
                    conn.rollback()
                except Exception:
                    pass

        # ── Index on documents.session_id (MySQL only) ────────────────────
        if is_mysql:
            try:
                result = conn.execute(sa.text(
                    "SELECT COUNT(*) FROM information_schema.STATISTICS "
                    "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = 'documents' "
                    "AND INDEX_NAME = 'ix_documents_session_id'"
                ), {"db": db_name})
                if result.scalar() == 0:
                    conn.execute(sa.text(
                        "ALTER TABLE documents "
                        "ADD INDEX ix_documents_session_id (session_id)"
                    ))
                    conn.commit()
                    print("[Migration] Added index on documents.session_id")
                else:
                    print("[Migration] 'documents.session_id' index OK")
            except Exception as e:
                print(f"[Migration] Index warning: {e}")
                try:
                    conn.rollback()
                except Exception:
                    pass

        # ── excel_metadata table indices (MySQL only) ─────────────────────
        if is_mysql:
            for idx_name, idx_col in [
                ("ix_excel_meta_doc_id",     "doc_id"),
                ("ix_excel_meta_session_id", "session_id"),
            ]:
                try:
                    result = conn.execute(sa.text(
                        "SELECT COUNT(*) FROM information_schema.STATISTICS "
                        "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = 'excel_metadata' "
                        "AND INDEX_NAME = :idx"
                    ), {"db": db_name, "idx": idx_name})
                    if result.scalar() == 0:
                        conn.execute(sa.text(
                            f"ALTER TABLE excel_metadata ADD INDEX {idx_name} ({idx_col})"
                        ))
                        conn.commit()
                        print(f"[Migration] Added index '{idx_name}' on excel_metadata")
                    else:
                        print(f"[Migration] Index '{idx_name}' OK")
                except Exception as e:
                    print(f"[Migration] Index warning '{idx_name}': {e}")
                    try:
                        conn.rollback()
                    except Exception:
                        pass

_run_migrations()

# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(title="DocChat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "*")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def preload_models():
    get_model()
    get_reranker()

app.include_router(upload.router,          prefix="/api")
app.include_router(medical_upload.router,  prefix="/api")
app.include_router(chat.router,            prefix="/api")
app.include_router(documents.router,       prefix="/api")
app.include_router(debug.router,           prefix="/api")
app.include_router(sessions.router,        prefix="/api")
app.include_router(website.router,         prefix="/api")
app.include_router(dataset.router,         prefix="/api/dataset")

@app.get("/health")
def health():
    return {"status": "ok"}