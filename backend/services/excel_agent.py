"""
excel_agent.py
──────────────
Handles CALCULATION intent: reads an Excel file and executes safe,
whitelisted Pandas operations.

Security model
──────────────
The LLM never generates executable code.  Instead it returns a structured
JSON spec, and only the operations in ALLOWED_OPS are ever executed.
This eliminates arbitrary code execution risk entirely.

Flow
────
User query
  → LLM extracts JSON operation spec
  → Validate spec (op in whitelist, columns exist)
  → Execute whitelisted Pandas op
  → Format result as Markdown
  → Stream back as SSE text events
"""

import json
import logging
import os
from typing import Dict, Generator, List, Optional

import pandas as pd
from groq import Groq

logger  = logging.getLogger(__name__)
_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
_MODEL  = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── Whitelist ──────────────────────────────────────────────────────────────────
ALLOWED_OPS = frozenset({
    "sum", "mean", "average", "max", "min", "count",
    "median", "std", "group_by", "filter", "describe",
    "head", "unique", "value_counts", "corr",
})

# Maximum rows to return in table output
_TABLE_LIMIT = 50

# ── Extraction prompt ──────────────────────────────────────────────────────────
_EXTRACT_SYSTEM = """\
You are a data operation extractor for Excel spreadsheets.
Given a user query and the available column names, extract the operation spec.

Return ONLY valid JSON (no extra text, no markdown):
{
  "operation": "sum|mean|max|min|count|group_by|filter|describe|head|unique|value_counts|median|std",
  "column": "column_name or null",
  "group_by_column": "column_name or null",
  "filter": {"column":"col","op":"==|>|<|>=|<=|!=|contains","value":"val"} or null,
  "sheet": "sheet_name or null",
  "limit": 10
}

Mapping rules:
  "total X"            → operation=sum,  column=X
  "average / mean X"   → operation=mean, column=X
  "max / highest X"    → operation=max,  column=X
  "min / lowest X"     → operation=min,  column=X
  "count / how many"   → operation=count
  "X by Y / group by Y"→ operation=group_by, column=X, group_by_column=Y
  "show/filter where"  → operation=filter, filter={...}
  "top N rows"         → operation=head, limit=N
  "unique values in X" → operation=unique, column=X\
"""


# ── Column helpers ─────────────────────────────────────────────────────────────

def _find_col(df: pd.DataFrame, hint: Optional[str]) -> Optional[str]:
    """Case-insensitive, partial-match column lookup."""
    if not hint:
        return None
    hint_lower = hint.lower()
    # Exact
    for c in df.columns:
        if str(c) == hint:
            return str(c)
    # Case-insensitive exact
    for c in df.columns:
        if str(c).lower() == hint_lower:
            return str(c)
    # Partial
    for c in df.columns:
        if hint_lower in str(c).lower():
            return str(c)
    return None


def _apply_filter(df: pd.DataFrame, f: dict) -> pd.DataFrame:
    """Apply a single validated filter condition."""
    col = _find_col(df, f.get("column", ""))
    if not col:
        return df

    op  = f.get("op", "==")
    val = f.get("value")

    _SAFE_OPS = {"==", ">", "<", ">=", "<=", "!=", "contains"}
    if op not in _SAFE_OPS:
        return df

    try:
        series = df[col]
        if op == "contains":
            return df[series.astype(str).str.contains(str(val), case=False, na=False)]
        elif op in (">", "<", ">=", "<="):
            numeric = pd.to_numeric(series, errors="coerce")
            fval    = float(val)
            ops_map = {">": numeric.__gt__, "<": numeric.__lt__,
                       ">=": numeric.__ge__, "<=": numeric.__le__}
            return df[ops_map[op](fval)]
        elif op == "==":
            # Try numeric first, then case-insensitive string match
            try:
                fval = float(val)
                numeric = pd.to_numeric(series, errors="coerce")
                return df[numeric == fval]
            except (ValueError, TypeError):
                # Case-insensitive, whitespace-trimmed string comparison
                str_series = series.astype(str).str.strip().str.lower()
                return df[str_series == str(val).strip().lower()]
        elif op == "!=":
            str_series = series.astype(str).str.strip().str.lower()
            return df[str_series != str(val).strip().lower()]
    except Exception as exc:
        logger.warning("[ExcelAgent] Filter error: %s", exc)
    return df


# ── Markdown formatting ────────────────────────────────────────────────────────

def _to_markdown(df: pd.DataFrame, limit: int = _TABLE_LIMIT) -> str:
    df = df.head(limit)
    if df.empty:
        return "_No data to display._"

    cols    = [str(c) for c in df.columns]
    header  = "| " + " | ".join(cols) + " |"
    divider = "|" + "|".join("---" for _ in cols) + "|"

    rows = []
    for _, row in df.iterrows():
        cells = []
        for v in row:
            if isinstance(v, float):
                cells.append(f"{v:,.2f}")
            else:
                cells.append(str(v))
        rows.append("| " + " | ".join(cells) + " |")

    return "\n".join([header, divider] + rows)


# ── Whitelisted executor ───────────────────────────────────────────────────────

def _execute(spec: dict, df: pd.DataFrame) -> str:
    """
    Execute the extracted spec on the DataFrame.
    Only whitelisted operations run — no eval(), no exec().
    """
    op = spec.get("operation", "").lower()
    if op not in ALLOWED_OPS:
        return f"Operation `{op}` is not supported."

    # Apply pre-filter if present
    filter_spec = spec.get("filter")
    pre_filtered = False
    if filter_spec:
        df = _apply_filter(df, filter_spec)
        pre_filtered = True
        if df.empty:
            return "_No rows match the filter condition._"

    col = _find_col(df, spec.get("column"))

    # ── Aggregation ops ──────────────────────────────────────────────────────
    def _num_series(c):
        return pd.to_numeric(df[c], errors="coerce")

    def _agg(fn_name: str, label: str) -> str:
        if col:
            val = getattr(_num_series(col), fn_name)()
            return f"**{label} of {col}:** {val:,.4f}".rstrip("0").rstrip(".")
        # All numeric columns
        nums  = df.select_dtypes(include="number")
        lines = [f"**{label} values:**"]
        for c in nums.columns:
            v = getattr(nums[c], fn_name)()
            lines.append(f"- {c}: {v:,.4f}".rstrip("0").rstrip("."))
        return "\n".join(lines)

    if op == "sum":
        return _agg("sum", "Total")
    elif op in ("mean", "average"):
        return _agg("mean", "Average")
    elif op == "max":
        return _agg("max", "Maximum")
    elif op == "min":
        return _agg("min", "Minimum")
    elif op == "median":
        return _agg("median", "Median")
    elif op == "std":
        return _agg("std", "Std Dev")

    elif op == "count":
        n = len(df)
        suffix = " (after filter)" if pre_filtered else ""
        return f"**Record count{suffix}:** {n:,}"

    elif op == "group_by":
        grp_col = _find_col(df, spec.get("group_by_column"))
        if not grp_col:
            return "Please specify a column to group by."
        if col:
            tmp = df.copy()
            tmp[col] = pd.to_numeric(tmp[col], errors="coerce")
            result = tmp.groupby(grp_col)[col].sum().reset_index()
            result.columns = [grp_col, f"Total {col}"]
        else:
            result = df.groupby(grp_col).size().reset_index(name="Count")
        result = result.sort_values(result.columns[-1], ascending=False)
        return _to_markdown(result)

    elif op == "filter":
        limit = min(int(spec.get("limit") or 20), _TABLE_LIMIT)
        return _to_markdown(df.head(limit))

    elif op == "describe":
        nums = df.select_dtypes(include="number")
        if nums.empty:
            return "_No numeric columns found._"
        desc = nums.describe().round(2)
        return _to_markdown(desc.reset_index().rename(columns={"index": "Statistic"}))

    elif op == "head":
        limit = min(int(spec.get("limit") or 10), _TABLE_LIMIT)
        return _to_markdown(df.head(limit))

    elif op == "unique":
        if not col:
            return "Please specify a column."
        vals = df[col].dropna().unique()[:50]
        return f"**Unique values in '{col}'** ({len(vals)}):\n" + "\n".join(f"- {v}" for v in vals)

    elif op == "value_counts":
        if not col:
            return "Please specify a column."
        vc    = df[col].value_counts().head(25)
        lines = [f"**Value counts for '{col}':**"]
        for v, cnt in vc.items():
            lines.append(f"- {v}: {cnt:,}")
        return "\n".join(lines)

    elif op == "corr":
        nums = df.select_dtypes(include="number")
        if nums.shape[1] < 2:
            return "_Need at least 2 numeric columns for correlation._"
        corr = nums.corr().round(3)
        return _to_markdown(corr.reset_index().rename(columns={"index": "Column"}))

    return "_Operation could not be completed._"


# ── Public entry point ─────────────────────────────────────────────────────────

def run_calculation(
    query: str,
    excel_meta: dict,
    storage_path: str,
    sheet_hint: Optional[str] = None,
) -> Generator[dict, None, None]:
    """
    Execute a CALCULATION query on the Excel file.
    Yields SSE-compatible dicts: {"type": "text", "text": "..."}
    """
    sheet_names  = excel_meta.get("sheet_names", [])
    columns_map  = excel_meta.get("columns", {})
    filename     = excel_meta.get("filename", "Excel file")

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

    # Collect all known columns for the extraction prompt
    all_cols: List[str] = []
    for s in sheet_names:
        all_cols.extend(columns_map.get(s, []))
    all_cols = list(dict.fromkeys(all_cols))  # deduplicate

    # ── Step 1: Extract operation spec ──────────────────────────────────────
    spec_prompt = (
        f"Sheets: {', '.join(sheet_names)}\n"
        f"Columns: {', '.join(all_cols[:30])}\n"
        f"Query: {query}"
    )
    try:
        resp = _client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _EXTRACT_SYSTEM},
                {"role": "user",   "content": spec_prompt},
            ],
            max_tokens=300,
            temperature=0.0,
            stream=False,
        )
        raw   = resp.choices[0].message.content.strip()
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        spec  = json.loads(raw[start:end]) if start >= 0 and end > start else {}
    except Exception as exc:
        logger.error("[ExcelAgent] Spec extraction failed: %s", exc)
        yield {"type": "text", "text": f"Could not interpret your query: {exc}"}
        return

    # Override sheet from spec if LLM identified one
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

    # ── Step 3: Execute whitelisted operation ────────────────────────────────
    try:
        result_text = _execute(spec, df)
    except Exception as exc:
        logger.error("[ExcelAgent] Execution error: %s", exc)
        yield {"type": "text", "text": f"Calculation failed: {exc}"}
        return

    # ── Step 4: Stream result line-by-line ──────────────────────────────────
    header = (
        f"📊 **Excel Analysis** — *{filename}* › Sheet: *{target_sheet}*"
        f"  ({len(df):,} rows)\n\n"
    )
    yield {"type": "text", "text": header}

    for line in result_text.splitlines(keepends=True):
        yield {"type": "text", "text": line}

    logger.info(
        "[ExcelAgent] op=%s sheet=%s rows=%d",
        spec.get("operation"), target_sheet, len(df),
    )
