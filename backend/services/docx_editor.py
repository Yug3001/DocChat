"""
docx_editor.py
──────────────
Handles DOCX_EDIT intent: takes retrieved document chunks and a user
edit instruction, applies changes using the LLM, and streams the
fully updated content back.

The LLM never touches the original file — it only produces new text
that the user can copy and use in their Word document.
"""

import json
import logging
import os
from typing import Generator, List

from groq import Groq

logger  = logging.getLogger(__name__)
_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
_MODEL  = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── System prompt ──────────────────────────────────────────────────────────────
_EDIT_SYSTEM = """\
You are a professional document editor assistant.
The user has uploaded a Word document and wants to modify specific content in it.

Your job:
1. Read the document content provided in the context.
2. Apply exactly the changes the user requested.
3. Output the COMPLETE updated text (the full paragraph, section, or relevant portion).
4. Clearly mark what changed using the format shown below.

Output format rules:
- Start with a one-line plain summary: "✏️ Here is the updated content:"
- Then output the FULL updated text in a clean, readable way.
- Use **bold** to highlight the words/phrases you changed or added.
- Use ~~strikethrough~~ to show text that was removed.
- Keep all unchanged text as-is — do NOT omit or summarize it.
- After the content, add a short "📝 Changes made:" section listing each change as a bullet.
- Do NOT add any extra commentary, preamble, or explanation outside these sections.
- Do NOT say "I have updated..." or "Here you go..." — just output the structured result.

If the context does not contain the section the user wants to edit, respond with:
"⚠️ I couldn't find the specific section you mentioned in the uploaded document.
Please describe which paragraph or part you want to change, or paste the text directly."\
"""


def _build_edit_prompt(instruction: str, chunks: List[dict]) -> str:
    """Build the edit prompt with retrieved context."""
    context_blocks = []
    for i, chunk in enumerate(chunks):
        filename = chunk["metadata"].get("filename", "Unknown")
        context_blocks.append(f"[Source {i+1} | {filename}]\n{chunk['text']}")
    context = "\n\n---\n\n".join(context_blocks)

    return f"""Document content retrieved:

{context}

==========
User's edit instruction: {instruction}

Apply the requested changes and output the updated content following the format rules exactly.

Updated content:"""


def stream_docx_edit(
    instruction: str,
    chunks: List[dict],
) -> Generator[dict, None, None]:
    """
    Stream the edited document content.
    Yields dicts: {{"type": "text", "text": "..."}}
    """
    prompt = _build_edit_prompt(instruction, chunks)

    try:
        stream = _client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _EDIT_SYSTEM},
                {"role": "user",   "content": prompt},
            ],
            stream=True,
            max_tokens=4096,
            temperature=0.15,
        )

        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield {"type": "text", "text": delta.content}

    except Exception as exc:
        logger.error("[DocxEditor] Groq API error: %s", exc)
        err = str(exc)[:120]
        yield {
            "type": "text",
            "text": f"⚠️ Sorry, I encountered an error while editing the document. Please try again. ({err})",
        }
