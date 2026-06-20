"""
services/medical_vision.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Performs clinical-style vision analysis on a medical image (X-ray / MRI /
CT / ultrasound) using a Groq-hosted vision LLM.

Returns a structured analysis text string that is then stored in ChromaDB
via the standard chunker → embedder → vector_store pipeline, so that
subsequent chat questions can retrieve and reference the findings.

IMPORTANT: This module performs ONE-TIME analysis at upload time.
  • The analysis text is embedded into ChromaDB.
  • chat.py's RAG path retrieves these chunks for follow-up questions.
  • This module is NOT called again during chat — only at upload.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import base64
import logging
import os

from groq import Groq

from services.llm import MEDICAL_IMAGE_SYSTEM_PROMPT, _VISION_MODEL

logger = logging.getLogger(__name__)

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def _encode_image_to_base64(image_path: str) -> str:
    """Read an image file and return a base64-encoded string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _get_mime_type(image_path: str) -> str:
    """
    Determine MIME type from file extension.
    Groq vision API requires image/jpeg, image/png, image/gif, or image/webp.
    """
    ext = os.path.splitext(image_path)[1].lower()
    return {
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".webp": "image/webp",
        ".gif":  "image/gif",
    }.get(ext, "image/jpeg")


def analyze_medical_image(image_path: str, filename: str) -> str:
    """
    Send the medical image to the Groq vision model and return the full
    clinical-style analysis text.

    Parameters
    ----------
    image_path : Absolute path to the saved image file on disk.
    filename   : Original filename (used for context in the prompt).

    Returns
    -------
    str — the complete analysis text, suitable for chunking and embedding.
          Includes the mandatory disclaimer, imaging report sections, etc.
          On failure, returns a fallback string so chunking still proceeds.
    """
    try:
        image_b64  = _encode_image_to_base64(image_path)
        mime_type  = _get_mime_type(image_path)
        data_url   = f"data:{mime_type};base64,{image_b64}"

        logger.info(
            "[MedicalVision] Sending %s to vision model %s",
            filename, _VISION_MODEL,
        )

        response = _client.chat.completions.create(
            model=_VISION_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": MEDICAL_IMAGE_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url},
                        },
                        {
                            "type": "text",
                            "text": (
                                f"Please provide a complete educational analysis of this "
                                f"medical image (file: {filename}). Follow the structured "
                                f"imaging report format specified in your instructions."
                            ),
                        },
                    ],
                },
            ],
            max_tokens=2048,
            temperature=0.1,   # low temperature for factual, reproducible analysis
        )

        analysis = response.choices[0].message.content or ""

        logger.info(
            "[MedicalVision] Analysis complete for %s — %d chars",
            filename, len(analysis),
        )
        return analysis.strip()

    except Exception as exc:
        logger.error(
            "[MedicalVision] Vision analysis failed for %s: %s", filename, exc
        )
        # Return a descriptive fallback so the document record is still usable
        return (
            f"[Medical Image: {filename}]\n\n"
            "⚠️ Automated vision analysis could not be completed for this image. "
            "This may be due to a temporary service issue. "
            "You can still ask questions about this image — the model will attempt "
            "to answer based on the image file directly.\n\n"
            f"Error detail: {str(exc)[:200]}"
        )
