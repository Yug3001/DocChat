"""
intent_classifier.py
────────────────────
Fast LLM-based intent router.  Runs a single non-streaming Groq call
(~150–250 ms) and returns one of three intents:

    RETRIEVAL    → existing ChromaDB + LLM RAG pipeline (default)
    CALCULATION  → Excel Agent  (Pandas read-only analytics)
    UPDATE       → Excel Updater (Pandas write operations)

Design decisions:
  - Only activates CALCULATION / UPDATE when the session actually has
    an Excel document.  Otherwise always returns RETRIEVAL.
  - Falls back to RETRIEVAL on any parse / network error.
  - Never crashes — all exceptions are caught and logged.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

from groq import Groq

logger = logging.getLogger(__name__)

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
_MODEL  = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── Prompt ─────────────────────────────────────────────────────────────────────
_SYSTEM = """\
You are an intent classifier for a document-chat assistant.
Classify the user query into EXACTLY ONE intent.

RETRIEVAL
  General questions, summaries, explanations, comparisons.
  Examples: "summarize", "what does it say about X", "explain", "list all",
            "who is", "describe", "show me the overview".

CALCULATION
  Arithmetic / aggregation operations on spreadsheet data.
  Keywords: total, sum, average, mean, max, min, count, how many,
            median, std, variance, group by, filter where, show rows where,
            percentage, ratio, correlation, distribution.

UPDATE
  Modifying spreadsheet rows OR filling empty cells (Excel only).
  Keywords: add row, insert row, delete row, remove row, update cell,
            change value, set value, modify cell, rename column,
            rename row, fill, populate, generate, assign, complete,
            empty is/are, column is empty, missing values,
            fill with random, fill randomly, random values.

DOCX_EDIT
  Editing, rewriting, translating, correcting, or improving text content
  inside a Word / PDF / text document (NOT an Excel spreadsheet).
  Keywords: rewrite, rephrase, make it formal, fix grammar, translate,
            change this sentence, update this paragraph, correct this,
            improve this, make it shorter, make it longer, simplify,
            paraphrase, edit this, modify this text, change the wording,
            change the tone, add a sentence, remove this line,
            replace this word, fix the spelling.

Rules:
  1. Return ONLY valid JSON — no markdown, no extra text.
  2. Format: {"intent":"RETRIEVAL","sheet_hint":null,"confidence":0.95}
  3. sheet_hint = sheet name if explicitly mentioned, else null.
  4. confidence = 0.0..1.0 (your certainty).
  5. When unsure, return RETRIEVAL.
  6. Only return CALCULATION or UPDATE when the session has Excel AND arithmetic/row-mutation language is clearly present.
  7. Return DOCX_EDIT when user clearly wants to change the wording, grammar, style, or content of a text document.
  8. "fill X with random values", "the X column is empty, fill it", "populate the X column" → always UPDATE.\
"""


@dataclass
class IntentResult:
    intent:     str            = "RETRIEVAL"   # RETRIEVAL | CALCULATION | UPDATE | DOCX_EDIT
    sheet_hint: Optional[str]  = None
    confidence: float          = 1.0
    error:      Optional[str]  = None


def classify_intent(
    query: str,
    has_excel: bool,
    excel_columns: Optional[List[str]] = None,
) -> IntentResult:
    """
    Classify user query intent.

    Parameters
    ----------
    query         : The raw user message.
    has_excel     : Whether the current session has at least one Excel doc.
    excel_columns : Known column names from the Excel file (improves accuracy).

    Returns
    -------
    IntentResult with .intent, .sheet_hint, .confidence
    """
    # Fast path: if no Excel doc exists, always RETRIEVAL
    if not has_excel:
        return IntentResult(intent="RETRIEVAL", sheet_hint=None, confidence=1.0)

    # Build user message with column hint
    col_hint = ""
    if excel_columns:
        col_hint = f"\nKnown spreadsheet columns: {', '.join(excel_columns[:25])}"

    user_msg = f"Query: {query}{col_hint}"

    try:
        response = _client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user",   "content": user_msg},
            ],
            max_tokens=80,
            temperature=0.0,
            stream=False,
        )

        raw = response.choices[0].message.content.strip()

        # Extract JSON even if LLM wraps it in backticks or prose
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start < 0 or end <= start:
            raise ValueError(f"No JSON in response: {raw!r}")

        data = json.loads(raw[start:end])

        intent = str(data.get("intent", "RETRIEVAL")).upper()
        if intent not in {"RETRIEVAL", "CALCULATION", "UPDATE", "DOCX_EDIT"}:
            intent = "RETRIEVAL"

        result = IntentResult(
            intent     = intent,
            sheet_hint = data.get("sheet_hint") or None,
            confidence = float(data.get("confidence", 0.9)),
        )
        logger.info(
            "[IntentClassifier] query=%r → intent=%s (conf=%.2f)",
            query[:80], result.intent, result.confidence,
        )
        return result

    except Exception as exc:
        logger.warning("[IntentClassifier] Error: %s — falling back to RETRIEVAL", exc)
        return IntentResult(
            intent     = "RETRIEVAL",
            sheet_hint = None,
            confidence = 0.5,
            error      = str(exc),
        )
