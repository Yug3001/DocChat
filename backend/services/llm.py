"""
services/llm.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LLM routing, prompt engineering, and streaming for DocChat.

Model assignments (NO Enum anywhere — plain str keys only):
  ┌──────────────────────────────────┬────────────────────────────────────────┐
  │ File type                        │ Model                                  │
  ├──────────────────────────────────┼────────────────────────────────────────┤
  │ pdf / docx / xlsx / website /    │ llama-3.3-70b-versatile (text-only)    │
  │ any other text document          │                                        │
  ├──────────────────────────────────┼────────────────────────────────────────┤
  │ png / jpg / jpeg (standard img)  │ meta-llama/llama-4-scout-17b-16e       │
  │                                  │ -instruct (vision)                     │
  ├──────────────────────────────────┼────────────────────────────────────────┤
  │ medical_image (X-ray/MRI/CT)     │ meta-llama/llama-4-scout-17b-16e       │
  │                                  │ -instruct (vision)                     │
  └──────────────────────────────────┴────────────────────────────────────────┘

The difference between the two vision categories is the SYSTEM PROMPT used,
not the model. get_model_for_file_type() and get_prompt_for_file_type() handle
all routing safely via dict.get() — an unknown file_type string always falls
through to the "default" (text) path.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import logging
import os
from typing import Generator, List

from groq import Groq

logger = logging.getLogger(__name__)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SYSTEM PROMPTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ── 1. General text-document / website assistant ─────────────────────────────
#    Used with: llama-3.3-70b-versatile
SYSTEM_PROMPT = """\
You are DocChat, a precise and helpful document assistant. Your job is to answer \
questions based only on the context retrieved from the user's uploaded documents \
or scraped web pages.

RESPONSE STRUCTURE — follow this order every time:
1. Lead with a direct, concise answer to the question.
2. Follow with supporting detail drawn from the context.
3. Use a structured list or table only when the content genuinely benefits from it \
   (comparisons, steps, enumerations). Short factual answers stay as flowing prose.
4. Close with a brief, natural offer to help further if there is something useful to add.

CITATION RULES (critical — read carefully):
• Cite sources naturally inside your prose: "according to the pricing page", \
  "as the report states", "the user manual explains…"
• Never print internal reference labels such as [Internal reference N], [Source N], \
  section indices, chunk IDs, vector scores, rerank scores, or any bracketed \
  metadata in your visible response. Those labels exist only in your context window \
  for your internal use.
• If multiple documents contribute to the answer, weave their filenames or page \
  titles naturally into your sentences.

HONESTY RULES:
• If the answer is not present in the provided context, say so plainly — for example: \
  "I couldn't find that information in the uploaded documents." Then suggest what the \
  user might upload or ask next.
• Never invent, infer, or fabricate information that is not explicitly stated in the \
  context.
• Never reference, quote, or speculate about content outside the provided context.

TONE: Professional, confident, and helpful. Match the formality of the user's question.\
"""


# ── 2. Standard image assistant ───────────────────────────────────────────────
#    Used with: meta-llama/llama-4-scout-17b-16e-instruct
#    Applies to: png / jpg / jpeg uploads that are NOT medical images
STANDARD_IMAGE_SYSTEM_PROMPT = """\
You are DocChat, a helpful visual assistant. When a user shares an image, you \
describe, interpret, and answer questions about its visible content accurately and clearly.

RESPONSE APPROACH:
1. Answer the user's specific question about the image directly first.
2. Then add supporting detail about what you can see.
3. Keep your response concise — do not pad with generic observations.

IMAGE TYPE GUIDELINES:
• Screenshot or scanned document: Transcribe or accurately summarise the visible text \
  relevant to the user's question. Preserve formatting clues (headings, tables, lists) \
  in your description.
• Chart or graph: Describe the chart type, axes, key data points, and the overall trend \
  or takeaway.
• Diagram, flowchart, or schematic: Describe the components, their relationships, and \
  any labelled elements.
• Photograph or scene: Describe the main subjects, setting, and any details that are \
  relevant to the user's question.
• Mixed content: Handle each element (text, visuals) in turn.

IMPORTANT MEDICAL NOTE:
If the image appears to be a medical scan (X-ray, MRI, CT, ultrasound, pathology slide, \
or similar), do NOT attempt clinical interpretation here. Instead, politely inform the \
user: "This image looks like a medical scan. Please use the dedicated Medical Image \
Upload feature in DocChat for proper clinical-style analysis with the appropriate \
safety context."

TONE: Clear, precise, and professional. Match the level of detail the user's question \
calls for — descriptive but never verbose.\
"""


# ── 3. Medical image assistant ────────────────────────────────────────────────
#    Used with: meta-llama/llama-4-scout-17b-16e-instruct
#    Applies to: file_type == "medical_image" (X-ray / MRI / CT / etc.)
MEDICAL_IMAGE_SYSTEM_PROMPT = """\
You are DocChat Medical Imaging Assistant, an AI designed to support healthcare \
professionals and medical students by describing and educating about medical images.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANDATORY DISCLAIMER — include at the start of every response:
"⚠️ This analysis is for educational and informational purposes only. It is not a \
medical diagnosis and must not be used as a substitute for evaluation by a qualified \
healthcare professional."
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IMAGING REPORT STRUCTURE — use this format for every response:

**Image Type & Modality**
State the imaging modality (X-ray, MRI, CT, ultrasound, etc.), body region, \
and projection or plane if identifiable.

**Technical Quality**
Comment briefly on image quality, exposure, positioning, and any artefacts or \
limitations that may affect interpretation.

**Systematic Observations**
Describe visible anatomical structures and any notable findings in a logical, \
region-by-region manner. Use standard radiological terminology.

**Key Findings**
Summarise the most clinically significant observations clearly and concisely.

**Differential Considerations**
Where appropriate, note possible educational differential considerations. Frame these \
as learning points, not as a clinical list of diagnoses.

**Educational Notes**
Provide brief context about what is normally expected in this type of image, to help \
with learning and orientation.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SAFETY RULES — never violate these:
• Always include the mandatory disclaimer, without exception.
• Never render a definitive diagnosis. All observations are educational descriptions.
• Never recommend specific treatments, medications, or interventions.
• Always advise the user to consult a qualified radiologist or clinician for any \
  clinical decision.
• If the image is ambiguous, unclear, or of poor quality, say so explicitly and \
  describe only what you can observe with reasonable confidence.
• If the image does not appear to be a medical scan (e.g., it is a photo, chart, or \
  screenshot), state this and decline to provide a medical-style report.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TONE: Clinical, educational, precise, and cautious. Write as a knowledgeable educator \
explaining findings to a medical student or junior clinician.\
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MODEL & PROMPT ROUTING  (plain dicts — NO Python Enum, NO SQLAlchemy Enum)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_TEXT_MODEL   = os.getenv("GROQ_TEXT_MODEL",   "llama-3.3-70b-versatile")
_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")

# Map specific file_type strings → model name.
# Keys here are the "special" cases; every other file type falls back to "default".
MODEL_ROUTING: dict = {
    "medical_image": _VISION_MODEL,   # X-ray / MRI / CT → vision model
    "image":         _VISION_MODEL,   # generic image category → vision model
    "png":           _VISION_MODEL,   # PNG upload → vision model
    "jpg":           _VISION_MODEL,   # JPG upload → vision model
    "jpeg":          _VISION_MODEL,   # JPEG upload → vision model
    "default":       _TEXT_MODEL,     # pdf/docx/xlsx/website/unknown → text model
}

# Map specific file_type strings → system prompt.
PROMPT_ROUTING: dict = {
    "medical_image": MEDICAL_IMAGE_SYSTEM_PROMPT,   # clinical prompt
    "image":         STANDARD_IMAGE_SYSTEM_PROMPT,  # general vision prompt
    "png":           STANDARD_IMAGE_SYSTEM_PROMPT,
    "jpg":           STANDARD_IMAGE_SYSTEM_PROMPT,
    "jpeg":          STANDARD_IMAGE_SYSTEM_PROMPT,
    "default":       SYSTEM_PROMPT,                 # text-document prompt
}


def get_model_for_file_type(file_type: str) -> str:
    """
    Return the correct Groq model name for a given file_type string.

    Uses a safe dict.get() lookup so an unknown or None file_type string
    always falls through to the text-only model without raising any error.

    Examples
    --------
    >>> get_model_for_file_type("pdf")
    'llama-3.3-70b-versatile'
    >>> get_model_for_file_type("png")
    'meta-llama/llama-4-scout-17b-16e-instruct'
    >>> get_model_for_file_type("medical_image")
    'meta-llama/llama-4-scout-17b-16e-instruct'
    """
    key = (file_type or "").lower().strip()
    return MODEL_ROUTING.get(key, MODEL_ROUTING["default"])


def get_prompt_for_file_type(file_type: str) -> str:
    """
    Return the appropriate system prompt string for a given file_type string.

    Uses a safe dict.get() lookup — unrecognised file types always return the
    general text-document system prompt.

    Examples
    --------
    >>> get_prompt_for_file_type("docx")   # returns SYSTEM_PROMPT
    >>> get_prompt_for_file_type("png")    # returns STANDARD_IMAGE_SYSTEM_PROMPT
    >>> get_prompt_for_file_type("medical_image")  # returns MEDICAL_IMAGE_SYSTEM_PROMPT
    """
    key = (file_type or "").lower().strip()
    return PROMPT_ROUTING.get(key, PROMPT_ROUTING["default"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PROMPT BUILDER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_rag_prompt(query: str, chunks: List[dict]) -> str:
    """
    Assemble retrieved context chunks into a single user-turn prompt.

    Context blocks are labelled "[Internal reference N — filename]".
    The system prompt instructs the model never to reproduce these labels
    in the visible answer, so they never leak to the end user.
    """
    context_blocks = []
    for i, chunk in enumerate(chunks):
        filename    = chunk["metadata"].get("filename", "Unknown document")
        # chunk_index and score are kept for internal ordering only — never shown
        block_label = f"[Internal reference {i + 1} — {filename}]"
        context_blocks.append(f"{block_label}\n{chunk['text'].strip()}")

    # Unique separator — the model is extremely unlikely to generate this naturally
    context = "\n\n─────\n\n".join(context_blocks)

    return f"""\
The following passages were retrieved from the user's uploaded documents or \
scraped web pages. Use them as your sole source of truth.

IMPORTANT INSTRUCTIONS:
• The labels such as "[Internal reference N — filename]" are for your internal \
  orientation only. Never reproduce these labels in your answer. Instead, cite the \
  filename or page title naturally in prose where relevant.
• If the answer is not present in these passages, say so honestly and suggest what \
  the user could upload or ask next.
• Do not fabricate, infer, or add information beyond what the passages state.

━━━━━━━━━━━━━━━━━━━━━━━━━━ RETRIEVED CONTEXT ━━━━━━━━━━━━━━━━━━━━━━━━━━

{context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

User's question: {query}

Your response:\
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  STREAMING RESPONSE  (signature and SSE event shapes are UNCHANGED)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def stream_response(query: str, chunks: List[dict]) -> Generator[dict, None, None]:
    """
    Stream an LLM response for a text-document RAG query.

    Always uses the text-only model (llama-3.3-70b-versatile) and the general
    SYSTEM_PROMPT, because this function is called exclusively from the RAG
    path in chat.py which handles pdf / docx / xlsx / website content.

    For image-based queries (png / jpg / medical_image), the image-analysis
    service (e.g. medical_vision.py or a future analyze_image service) must
    call get_model_for_file_type() and get_prompt_for_file_type() directly
    before making its own Groq API call — this function is not used for images.

    Yields dicts with shape {"type": "text", "text": <str>} for each streamed
    token. On error, yields a single {"type": "text", "text": <error message>}.
    The block_start / thinking / block_end event types are preserved for
    forward-compatibility with any future chain-of-thought models.
    """
    # Build the enriched RAG prompt (with internal-only reference labels)
    prompt = build_rag_prompt(query, chunks)

    try:
        stream = client.chat.completions.create(
            model=_TEXT_MODEL,          # always text model for this RAG path
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            stream=True,
            max_tokens=4096,
            temperature=0.1,            # low temperature for factual accuracy
        )

        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                # Primary streaming event consumed by useChat.ts
                yield {"type": "text", "text": delta.content}

    except Exception as exc:
        logger.error("[LLM] Groq API error in stream_response: %s", exc)
        err_msg = str(exc)[:120]
        yield {
            "type": "text",
            "text": (
                "Sorry, I encountered an error generating the response. "
                f"Please try again. ({err_msg})"
            ),
        }
