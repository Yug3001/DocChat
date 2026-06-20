"""
excel_processor.py
──────────────────
Called at upload time for .xlsx / .xls files.
Extracts structural metadata (sheets, columns, dtypes, row counts)
and stores it in the excel_metadata table.

Also builds a text summary for ChromaDB so RETRIEVAL queries
("what columns does this sheet have?") still work via RAG.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any

import pandas as pd

logger = logging.getLogger(__name__)

# Maximum rows to read when building the RAG summary sample
_SAMPLE_ROWS = 5
# Maximum sheets we'll process (guard against huge workbooks)
_MAX_SHEETS = 20


def process_excel(
    file_path: str,
    doc_id: str,
    session_id: str,
    filename: str,
    db,
) -> Dict[str, Any]:
    """
    Parse an Excel file, persist its metadata to `excel_metadata`,
    and return the metadata dict.

    Parameters
    ----------
    file_path   : Absolute path to the saved .xlsx file on disk.
    doc_id      : UUID of the document record.
    session_id  : Session the upload belongs to.
    filename    : Original filename shown to the user.
    db          : SQLAlchemy session.

    Returns
    -------
    dict with keys: sheet_names, columns, row_counts, dtypes, storage_path
    """
    from db.models import ExcelMeta  # local import avoids circular deps

    path = Path(file_path).resolve()

    # ── Load workbook ───────────────────────────────────────────────────────
    try:
        xl = pd.ExcelFile(str(path))
        sheet_names: list = xl.sheet_names[:_MAX_SHEETS]
    except Exception as exc:
        logger.error("[ExcelProcessor] Cannot open %s: %s", file_path, exc)
        raise ValueError(f"Cannot open Excel file: {exc}") from exc

    columns: Dict[str, list]   = {}
    row_counts: Dict[str, int]  = {}
    dtypes: Dict[str, dict]     = {}

    for sheet in sheet_names:
        try:
            df = pd.read_excel(str(path), sheet_name=sheet)
            columns[sheet]    = [str(c) for c in df.columns]
            row_counts[sheet] = int(len(df))
            dtypes[sheet]     = {str(c): str(t) for c, t in df.dtypes.items()}
        except Exception as exc:
            logger.warning("[ExcelProcessor] Cannot read sheet '%s': %s", sheet, exc)
            columns[sheet]    = []
            row_counts[sheet] = 0
            dtypes[sheet]     = {}

    meta_dict = {
        "sheet_names":   sheet_names,
        "columns":       columns,
        "row_counts":    row_counts,
        "dtypes":        dtypes,
        "storage_path":  str(path),
    }

    # ── Persist to DB ───────────────────────────────────────────────────────
    # Upsert: delete stale record if re-uploading same doc_id
    existing = db.query(ExcelMeta).filter(ExcelMeta.doc_id == doc_id).first()
    if existing:
        db.delete(existing)
        db.flush()

    meta_row = ExcelMeta(
        id           = doc_id,
        doc_id       = doc_id,
        session_id   = session_id,
        filename     = filename,
        sheet_names  = json.dumps(sheet_names),
        columns      = json.dumps(columns),
        row_counts   = json.dumps(row_counts),
        dtypes       = json.dumps(dtypes),
        storage_path = str(path),
    )
    db.add(meta_row)
    db.commit()

    logger.info(
        "[ExcelProcessor] Stored metadata for %s | sheets=%s | rows=%s",
        filename, sheet_names, row_counts,
    )
    return meta_dict


def build_excel_summary(meta: Dict[str, Any], filename: str) -> str:
    """
    Build a human-readable text summary of the Excel structure.
    This is chunked and embedded into ChromaDB so RETRIEVAL queries
    about the file's structure still work via RAG.
    """
    storage_path = meta.get("storage_path", "")
    lines = [
        f"Excel file: {filename}",
        f"Total sheets: {len(meta['sheet_names'])}",
    ]

    for sheet in meta["sheet_names"]:
        cols       = meta["columns"].get(sheet, [])
        row_count  = meta["row_counts"].get(sheet, 0)
        dtype_info = meta["dtypes"].get(sheet, {})

        lines.append(f"\n--- Sheet: {sheet} ---")
        lines.append(f"Rows: {row_count:,}")
        lines.append(f"Columns ({len(cols)}): {', '.join(cols)}")

        # Column types
        num_cols = [c for c, t in dtype_info.items() if "int" in t or "float" in t]
        str_cols = [c for c, t in dtype_info.items() if "object" in t]
        if num_cols:
            lines.append(f"Numeric columns: {', '.join(num_cols)}")
        if str_cols:
            lines.append(f"Text columns: {', '.join(str_cols)}")

        # Sample data
        if storage_path and os.path.exists(storage_path):
            try:
                sample = pd.read_excel(storage_path, sheet_name=sheet, nrows=_SAMPLE_ROWS)
                lines.append(f"Sample data (first {len(sample)} rows):")
                lines.append(sample.to_string(index=False, max_cols=10))
            except Exception:
                pass

    return "\n".join(lines)


def load_excel_meta_from_db(doc_id: str, db) -> Dict[str, Any]:
    """
    Load ExcelMeta from DB and deserialise JSON fields.
    Returns {} if not found.
    """
    from db.models import ExcelMeta

    row = db.query(ExcelMeta).filter(ExcelMeta.doc_id == doc_id).first()
    if not row:
        return {}

    return {
        "sheet_names":   json.loads(row.sheet_names),
        "columns":       json.loads(row.columns),
        "row_counts":    json.loads(row.row_counts),
        "dtypes":        json.loads(row.dtypes),
        "storage_path":  row.storage_path,
        "filename":      row.filename,
    }
