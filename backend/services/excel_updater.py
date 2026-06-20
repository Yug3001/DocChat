"""
excel_updater.py
────────────────
Handles UPDATE intent: INSERT, UPDATE, DELETE, FILL_EMPTY, FILL_RANDOM rows
in an Excel file.

Safety guarantees
─────────────────
  1. All column names are validated against the stored schema.
  2. Data types are coerced to match the existing column dtype.
  3. DELETE / UPDATE bulk ops are capped at 500 rows.
  4. File writes use a temp-file + os.replace() for atomicity.
  5. Every mutation is logged with timestamp and affected row count.
  6. The LLM only returns a JSON spec — no code is ever executed.

Supported operations
────────────────────
  insert       — append a new row
  update       — update specific rows matching a filter
  delete       — delete rows matching a filter
  fill_empty   — fill NULL/blank cells in a column with a fixed value
  fill_random  — fill NULL/blank cells with random numbers in range
"""

import json
import logging
import os
import random as _random
import re
import tempfile
from datetime import datetime
from typing import Dict, Generator, List, Optional

import pandas as pd
from groq import Groq

from services.excel_agent import _apply_filter, _find_col

logger  = logging.getLogger(__name__)
_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
_MODEL  = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

_MAX_AFFECTED = 500   # safety cap for bulk UPDATE / DELETE

# ── Extraction prompt ──────────────────────────────────────────────────────────
_UPDATE_SYSTEM = """\
You are a data modification extractor for Excel spreadsheets.
Given a user request, extract the modification into a JSON spec.

Return ONLY valid JSON (no extra text, no markdown):
{
  "operation": "insert|update|delete|fill_empty|fill_random|rename_column|rename_value",
  "sheet":      "sheet_name or null",
  "column":     "target_column or null",
  "row_data":   {"col": "val", ...} or null,
  "filter":     {"column":"col","op":"==|>|<|>=|<=|!=|contains","value":"val"} or null,
  "updates":    {"col": "new_val", ...} or null,
  "fill_value": "value to fill empty cells with, or null",
  "min_val":    number_or_null,
  "max_val":    number_or_null,
  "old_name":   "old column header name or old cell value, or null",
  "new_name":   "new column header name or new cell value, or null"
}

Operation rules:
  insert        — append a new row with row_data
  update        — update specific cell values in rows matching filter with updates dict
  delete        — delete rows matching filter
  fill_empty    — fill NULL/blank cells in 'column' with fill_value
  fill_random   — fill NULL/blank cells with random numbers between min_val and max_val
  rename_column — rename a column HEADER from old_name to new_name
  rename_value  — rename/change a CELL VALUE in 'column' from old_name to new_name
                  (use this when user says 'change the name of the row' or 'rename X to Y')

IMPORTANT: When user says:
  "change the name of row X to Y"       → operation=rename_value, find the column that contains X
  "rename row X to Y"                   → operation=rename_value
  "rename column X to Y"                → operation=rename_column, old_name=X, new_name=Y
  "change column header X to Y"         → operation=rename_column
  "change value X to Y in column Z"     → operation=rename_value, column=Z

Examples:
  "Add row: Product D, sales 500"
    → {"operation":"insert","row_data":{"Product":"Product D","Sales":500}}

  "Delete Product B"
    → {"operation":"delete","filter":{"column":"Product","op":"==","value":"Product B"}}

  "Update Product A sales to 900"
    → {"operation":"update","filter":{"column":"Product","op":"==","value":"Product A"},"updates":{"Sales":900}}

  "Change the name of the row from CHESS to MY_CHESS"
    → {"operation":"rename_value","old_name":"CHESS","new_name":"MY_CHESS"}

  "Rename the column Sport to SportType"
    → {"operation":"rename_column","old_name":"Sport","new_name":"SportType"}

  "Fill empty Revenue cells with 0"
    → {"operation":"fill_empty","column":"Revenue","fill_value":0}

  "The Revenue column is empty, fill it with random values"
    → {"operation":"fill_random","column":"Revenue","min_val":null,"max_val":null}\
"""


# ── Type coercion ──────────────────────────────────────────────────────────────

def _coerce(val, dtype: str):
    """Coerce a value to match the column's dtype string from pandas."""
    try:
        if "int" in dtype:
            return int(float(str(val)))
        elif "float" in dtype:
            return float(str(val))
        elif "bool" in dtype:
            return str(val).lower() in ("true", "1", "yes")
        elif "datetime" in dtype:
            return pd.to_datetime(str(val))
    except (ValueError, TypeError):
        pass
    return str(val)


def _validate_and_build_row(
    row_data: dict,
    df: pd.DataFrame,
    dtypes: dict,
) -> dict:
    """
    For INSERT: build a full row dict matching the DataFrame's columns.
    Unknown columns from row_data are ignored.
    Missing columns get None.
    """
    validated: dict = {}
    for col in df.columns:
        col_str = str(col)
        matched_val = None
        found = False
        for k, v in row_data.items():
            if k.lower() == col_str.lower():
                matched_val = v
                found = True
                break
        if found:
            dtype = dtypes.get(col_str, "object")
            validated[col_str] = _coerce(matched_val, dtype)
        else:
            validated[col_str] = None
    return validated


# ── Atomic file write ──────────────────────────────────────────────────────────

def _write_back(modified_df: pd.DataFrame, target_sheet: str, storage_path: str):
    """
    Write the modified sheet back to the Excel file atomically.
    Other sheets are preserved unchanged.
    Uses shutil.copy2 + unlink fallback for Windows compatibility.
    """
    import shutil

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".xlsx")
    os.close(tmp_fd)

    try:
        with pd.ExcelWriter(tmp_path, engine="openpyxl") as writer:
            modified_df.to_excel(writer, sheet_name=target_sheet, index=False)

            # Preserve all other sheets
            try:
                xl = pd.ExcelFile(storage_path)
                for other in xl.sheet_names:
                    if other != target_sheet:
                        other_df = pd.read_excel(storage_path, sheet_name=other)
                        other_df.to_excel(writer, sheet_name=other, index=False)
                xl.close()
            except Exception as exc:
                logger.warning("[ExcelUpdater] Could not preserve other sheets: %s", exc)

        # Atomic replace — use copy2 + unlink for Windows compatibility
        try:
            os.replace(tmp_path, storage_path)
        except OSError:
            shutil.copy2(tmp_path, storage_path)
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        raise



# ── Success response builder ───────────────────────────────────────────────────

def _success_response(
    filename: str,
    sheet: str,
    summary: str,
    details: Optional[str] = None,
) -> str:
    """
    Build the uniform 'changes made' confirmation message.
    """
    lines = [
        f"✅ I have made the changes — you can review them by opening the file.\n",
        f"📁 **File:** {filename}",
        f"📊 **Sheet:** {sheet}",
        f"📝 **Summary:** {summary}",
    ]
    if details:
        lines.append(f"\n**Details:**\n{details}")
    return "\n".join(lines)


# ── Public entry point ─────────────────────────────────────────────────────────

def run_update(
    query: str,
    excel_meta: dict,
    storage_path: str,
    sheet_hint: Optional[str] = None,
) -> Generator[dict, None, None]:
    """
    Execute an UPDATE (insert / update / delete / fill_empty / fill_random).
    Yields SSE-compatible dicts: {"type": "text", "text": "..."}
    """
    sheet_names = excel_meta.get("sheet_names", [])
    columns_map = excel_meta.get("columns", {})
    dtypes_map  = excel_meta.get("dtypes", {})
    filename    = excel_meta.get("filename", "Excel file")

    if not sheet_names:
        yield {"type": "text", "text": "_No sheets found in the Excel file._"}
        return

    # Determine target sheet
    target_sheet = sheet_names[0]
    if sheet_hint:
        for s in sheet_names:
            if s.lower() == sheet_hint.lower() or sheet_hint.lower() in s.lower():
                target_sheet = s
                break

    all_cols: List[str] = []
    for s in sheet_names:
        all_cols.extend(columns_map.get(s, []))
    all_cols = list(dict.fromkeys(all_cols))

    # ── Step 1: Extract modification spec ───────────────────────────────────
    spec_prompt = (
        f"Sheets: {', '.join(sheet_names)}\n"
        f"Columns: {', '.join(all_cols[:30])}\n"
        f"User request: {query}"
    )
    try:
        resp = _client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _UPDATE_SYSTEM},
                {"role": "user",   "content": spec_prompt},
            ],
            max_tokens=400,
            temperature=0.0,
            stream=False,
        )
        raw   = resp.choices[0].message.content.strip()
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        spec  = json.loads(raw[start:end]) if start >= 0 and end > start else {}
    except Exception as exc:
        logger.error("[ExcelUpdater] Spec extraction failed: %s", exc)
        yield {"type": "text", "text": f"Could not parse your request: {exc}"}
        return

    # Override sheet from spec
    if spec.get("sheet"):
        for s in sheet_names:
            if s.lower() == str(spec["sheet"]).lower():
                target_sheet = s
                break

    # ── Step 2: Load DataFrame ───────────────────────────────────────────────
    try:
        df = pd.read_excel(storage_path, sheet_name=target_sheet)
    except Exception as exc:
        yield {"type": "text", "text": f"Could not load sheet '{target_sheet}': {exc}"}
        return

    dtypes     = dtypes_map.get(target_sheet, {})
    op         = str(spec.get("operation", "")).lower().replace("-", "_")
    affected   = 0
    result_msg = ""

    # ── Step 3: Execute operation ────────────────────────────────────────────
    try:

        # ── INSERT ───────────────────────────────────────────────────────────
        if op == "insert":
            row_data = spec.get("row_data") or {}
            if not row_data:
                yield {"type": "text", "text": "⚠️ No data provided for insertion. Please specify column values."}
                return

            validated_row = _validate_and_build_row(row_data, df, dtypes)
            new_row_df    = pd.DataFrame([validated_row])
            df            = pd.concat([df, new_row_df], ignore_index=True)
            affected      = 1

            result_msg = _success_response(
                filename, target_sheet,
                f"Added 1 new row to the sheet.",
                f"New row data: `{json.dumps(row_data, default=str)}`\n"
                f"Total rows now: **{len(df):,}**",
            )

        # ── DELETE ───────────────────────────────────────────────────────────
        elif op == "delete":
            filter_spec = spec.get("filter")
            if not filter_spec:
                yield {"type": "text", "text": "⚠️ No filter provided. Please specify which rows to delete (e.g., 'Delete Product B')."}
                return

            matched  = _apply_filter(df, filter_spec)
            affected = len(matched)

            if affected == 0:
                yield {"type": "text", "text": f"_No rows matched_ `{filter_spec['column']} {filter_spec['op']} {filter_spec['value']}`"}
                return

            if affected > _MAX_AFFECTED:
                yield {"type": "text", "text": f"⚠️ This would delete **{affected:,} rows** which exceeds the safety limit of {_MAX_AFFECTED}. Please narrow your filter."}
                return

            df       = df[~df.index.isin(matched.index)].reset_index(drop=True)

            result_msg = _success_response(
                filename, target_sheet,
                f"Deleted {affected} row(s) where `{filter_spec['column']} {filter_spec['op']} {filter_spec['value']}`.",
                f"Remaining rows: **{len(df):,}**",
            )

        # ── UPDATE (filtered rows) ────────────────────────────────────────────
        elif op == "update":
            updates     = spec.get("updates") or {}
            filter_spec = spec.get("filter")

            if not updates:
                yield {"type": "text", "text": "⚠️ No update values provided."}
                return

            if not filter_spec:
                yield {"type": "text", "text": "⚠️ No filter condition found. Please specify which rows to update (e.g., 'Update Product A sales to 900'). To fill an entire empty column, try: 'Fill the Revenue column with random values'."}
                return

            matched  = _apply_filter(df, filter_spec)
            affected = len(matched)

            if affected == 0:
                yield {"type": "text", "text": f"_No rows matched_ `{filter_spec['column']} {filter_spec['op']} {filter_spec['value']}`"}
                return

            if affected > _MAX_AFFECTED:
                yield {"type": "text", "text": f"⚠️ This would update **{affected:,} rows** which exceeds the safety limit of {_MAX_AFFECTED}. Please narrow your filter."}
                return

            change_summary = []
            for col_hint, new_val in updates.items():
                matched_col = _find_col(df, col_hint)
                if not matched_col:
                    logger.warning("[ExcelUpdater] Unknown column hint '%s'", col_hint)
                    continue
                dtype   = dtypes.get(str(matched_col), "object")
                new_val = _coerce(new_val, dtype)
                df.loc[matched.index, matched_col] = new_val
                change_summary.append(f"Set **{matched_col}** → `{new_val}`")

            result_msg = _success_response(
                filename, target_sheet,
                f"Updated {affected} row(s) where `{filter_spec['column']} {filter_spec['op']} {filter_spec['value']}`.",
                "\n".join(change_summary),
            )

        # ── FILL_EMPTY (fill nulls with a fixed value) ────────────────────────
        elif op == "fill_empty":
            col_hint   = spec.get("column") or ""
            fill_value = spec.get("fill_value")
            col        = _find_col(df, col_hint)

            if not col:
                yield {"type": "text", "text": f"⚠️ Column `{col_hint}` not found. Available columns: {', '.join(str(c) for c in df.columns)}"}
                return

            mask     = df[col].isna() | (df[col].astype(str).str.strip() == "") | (df[col].astype(str).str.strip() == "nan")
            affected = int(mask.sum())

            if affected == 0:
                yield {"type": "text", "text": f"✅ No empty cells found in **{col}** — the column is already fully filled!"}
                return

            fv = fill_value if fill_value is not None else 0
            df.loc[mask, col] = fv

            result_msg = _success_response(
                filename, target_sheet,
                f"Filled {affected} empty cell(s) in **{col}** with `{fv}`.",
            )

        # ── FILL_RANDOM (fill nulls with random numbers) ──────────────────────
        elif op == "fill_random":
            col_hint = spec.get("column") or ""
            col      = _find_col(df, col_hint)

            if not col:
                yield {"type": "text", "text": f"⚠️ Column `{col_hint}` not found. Available columns: {', '.join(str(c) for c in df.columns)}"}
                return

            mask     = df[col].isna() | (df[col].astype(str).str.strip() == "") | (df[col].astype(str).str.strip() == "nan")
            affected = int(mask.sum())

            if affected == 0:
                yield {"type": "text", "text": f"✅ No empty cells found in **{col}** — the column is already fully filled!"}
                return

            # Determine value range: use spec values, or derive from existing data
            min_val_spec = spec.get("min_val")
            max_val_spec = spec.get("max_val")

            existing = pd.to_numeric(df[col], errors="coerce").dropna()
            if min_val_spec is not None and max_val_spec is not None:
                lo, hi = float(min_val_spec), float(max_val_spec)
            elif len(existing) >= 2:
                lo = float(existing.min())
                hi = float(existing.max())
            elif len(existing) == 1:
                lo = float(existing.iloc[0]) * 0.5
                hi = float(existing.iloc[0]) * 1.5
            else:
                lo, hi = 100.0, 10000.0  # fallback

            # Generate random floats rounded to 2dp
            rand_vals = [round(_random.uniform(lo, hi), 2) for _ in range(affected)]
            df.loc[mask, col] = rand_vals

            result_msg = _success_response(
                filename, target_sheet,
                f"Filled {affected} empty cell(s) in **{col}** with random values "
                f"(range: {lo:,.2f} – {hi:,.2f}).",
                f"Sample values generated: {', '.join(str(v) for v in rand_vals[:5])}"
                + (" …" if affected > 5 else ""),
            )

        # ── RENAME_COLUMN (rename a column header) ────────────────────────────
        elif op == "rename_column":
            old_name = str(spec.get("old_name") or spec.get("column") or "")
            new_name = str(spec.get("new_name") or "")

            if not old_name or not new_name:
                yield {"type": "text", "text": "⚠️ Please provide both old and new column names."}
                return

            matched_col = _find_col(df, old_name)
            if not matched_col:
                yield {"type": "text", "text": f"⚠️ Column `{old_name}` not found. Available columns: {', '.join(str(c) for c in df.columns)}"}
                return

            df.rename(columns={matched_col: new_name}, inplace=True)
            affected = 1

            result_msg = _success_response(
                filename, target_sheet,
                f"Renamed column header `{matched_col}` → `{new_name}`.",
            )

        # ── RENAME_VALUE (change a cell value in a column) ────────────────────
        elif op == "rename_value":
            old_name = str(spec.get("old_name") or "")
            new_name = str(spec.get("new_name") or "")
            col_hint = spec.get("column")

            if not old_name or not new_name:
                yield {"type": "text", "text": "⚠️ Please provide both old and new values."}
                return

            # If column not specified, search ALL columns for the old value (case-insensitive)
            if col_hint:
                search_cols = [_find_col(df, col_hint)] if _find_col(df, col_hint) else []
            else:
                # Auto-detect: find which column actually contains this value
                search_cols = []
                for c in df.columns:
                    if df[c].astype(str).str.strip().str.lower().eq(old_name.strip().lower()).any():
                        search_cols.append(str(c))

            if not search_cols:
                all_cols_str = ", ".join(str(c) for c in df.columns)
                yield {"type": "text", "text": f"⚠️ Value `{old_name}` not found in any column. Available columns: {all_cols_str}"}
                return

            affected = 0
            changed_cols = []
            for col in search_cols:
                mask = df[col].astype(str).str.strip().str.lower() == old_name.strip().lower()
                count = int(mask.sum())
                if count > 0:
                    df.loc[mask, col] = new_name
                    affected += count
                    changed_cols.append(col)

            if affected == 0:
                yield {"type": "text", "text": f"_No rows matched value `{old_name}`_"}
                return

            result_msg = _success_response(
                filename, target_sheet,
                f"Changed {affected} occurrence(s) of `{old_name}` → `{new_name}` in column(s): {', '.join(changed_cols)}.",
            )

        else:
            yield {"type": "text", "text": f"⚠️ Operation `{op}` is not supported. Try: insert, update, delete, fill empty, fill random, rename column, or rename value."}
            return

    except Exception as exc:
        logger.error("[ExcelUpdater] Execution error: %s", exc)
        yield {"type": "text", "text": f"Modification failed: {exc}"}
        return

    # ── Step 4: Atomic write to disk ─────────────────────────────────────────
    try:
        _write_back(df, target_sheet, storage_path)
    except Exception as exc:
        logger.error("[ExcelUpdater] Write failed: %s", exc)
        yield {"type": "text", "text": f"Changes were computed but **could not save the file**: {exc}"}
        return

    logger.info(
        "[ExcelUpdater] %s on %s | sheet=%s | affected=%d | ts=%s",
        op.upper(), storage_path, target_sheet, affected,
        datetime.now().isoformat(),
    )

    # ── Step 5: Stream success message ───────────────────────────────────────
    for line in result_msg.splitlines(keepends=True):
        yield {"type": "text", "text": line}
