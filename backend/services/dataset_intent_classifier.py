"""
dataset_intent_classifier.py
Classifies natural language queries for datasets into specific intent strings.
"""
import json
import logging
from typing import Dict, Any
from groq import Groq
import os

logger = logging.getLogger(__name__)

# Using the text model for all logic tasks (SQL generation, intent classification)
_TEXT_MODEL = os.getenv("GROQ_TEXT_MODEL", "llama-3.3-70b-versatile")
_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

VALID_INTENTS = [
    "SCHEMA_QUERY", "DATA_QUERY", "COMPUTE_COLUMN", "ADD_COLUMN", "UPDATE_ROWS",
    "DELETE_ROWS", "INSERT_ROW", "DROP_COLUMN", "RENAME_COLUMN", "DOWNLOAD",
    "RESET", "AMBIGUOUS", "NON_DATASET"
]

def classify_intent(user_message: str, schema: dict, row_count: int, source_type: str) -> Dict[str, Any]:
    """
    Classify the user message into one of the valid intents.
    Returns:
        {"intent": str, "confidence": float, "explanation": str}
    """
    system_prompt = f"""You are a data analyst assistant. Your task is to classify the user's intent based on their message.

Valid Intents:
- SCHEMA_QUERY: Asking about table structure, columns, data types.
- DATA_QUERY: Asking to view, summarize, aggregate, filter, or read data.
- COMPUTE_COLUMN: Asking to add a new column calculated from other columns.
- ADD_COLUMN: Asking to add a new empty or default-value column.
- UPDATE_ROWS: Asking to modify existing records.
- DELETE_ROWS: Asking to remove records.
- INSERT_ROW: Asking to add new records.
- DROP_COLUMN: Asking to remove a column.
- RENAME_COLUMN: Asking to rename a column.
- DOWNLOAD: Asking to download the dataset (Only valid for CSV).
- RESET: Asking to revert the dataset to original state (Only valid for CSV).
- NON_DATASET: Asking a general knowledge question unrelated to the dataset.
- AMBIGUOUS: The request is unclear, missing details, or doesn't fit the above.

Dataset Info:
- Source Type: {source_type} (If MYSQL, DOWNLOAD and RESET are invalid, use AMBIGUOUS if requested)
- Row Count: {row_count}
- Schema: {json.dumps(schema)}

Output strictly valid JSON with these exact keys:
"intent": (string, must be one of the Valid Intents)
"confidence": (float between 0.0 and 1.0)
"explanation": (string, brief explanation of why you chose this intent)
"""

    try:
        response = _client.chat.completions.create(
            model=_TEXT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=200
        )
        content = response.choices[0].message.content
        result = json.loads(content)
        
        intent = result.get("intent", "AMBIGUOUS")
        confidence = float(result.get("confidence", 0.0))
        explanation = result.get("explanation", "Could not determine intent.")
        
        if intent not in VALID_INTENTS:
            intent = "AMBIGUOUS"
            
        if confidence < 0.75 and intent != "NON_DATASET":
            intent = "AMBIGUOUS"
            
        if intent in ["DOWNLOAD", "RESET"] and source_type.upper() == "MYSQL":
            intent = "AMBIGUOUS"
            explanation = f"{intent} is only available for CSV datasets, not MySQL."

        return {
            "intent": intent,
            "confidence": confidence,
            "explanation": explanation
        }

    except Exception as e:
        logger.error(f"[IntentClassifier] Error: {e}")
        return {
            "intent": "AMBIGUOUS",
            "confidence": 0.0,
            "explanation": f"Classification failed: {str(e)}"
        }
