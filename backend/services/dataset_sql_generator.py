"""
dataset_sql_generator.py
Generates SQL for a given intent. Retries up to 2 times if validation fails.
"""
import os
import logging
from groq import Groq
from typing import Dict, Any, List
from .dataset_sql_validator import validate_sql

logger = logging.getLogger(__name__)

_TEXT_MODEL = os.getenv("GROQ_TEXT_MODEL", "llama-3.3-70b-versatile")
_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_sql(
    schema: dict, 
    row_count: int, 
    sample_rows: List[dict], 
    intent: str, 
    source_type: str, 
    user_message: str,
    table_name: str
) -> Dict[str, Any]:
    """
    Generates SQL based on the prompt. Retries up to 2 times on validation failure.
    Returns: {"sql": str, "error_message": str}
    """
    system_prompt = f"""You are an expert SQL generator for {source_type}.
Your task is to write a single, valid SQL statement based on the user's request.

Dataset Details:
- Table Name: {table_name}
- Total Rows: {row_count}
- Schema: {schema}
- Sample Rows (max 5): {sample_rows}

Rules:
1. Return ONLY the raw SQL string. Do not use markdown blocks (e.g. ```sql).
2. Do not include any explanations or apologies.
3. Ensure the syntax is compatible with {source_type}. For CSV datasets, we will execute this using Pandas/DuckDB, so standard ANSI SQL or SQLite syntax is preferred. For MYSQL, use standard MySQL syntax.
4. The intent identified is: {intent}.
5. If UPDATE or DELETE, you MUST include a WHERE clause unless the user explicitly asks to modify all rows.
6. Never generate DROP TABLE or TRUNCATE statements.
7. For INSERT statements, you MUST provide values for ALL columns listed in the schema. The SQL must be complete — never truncate mid-statement.
8. Use sensible default values for any columns the user did not specify (e.g. 0 for numbers, empty string for text).
"""

    max_retries = 2
    attempts = 0
    last_error = ""

    while attempts <= max_retries:
        try:
            response = _client.chat.completions.create(
                model=_TEXT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            raw_sql = response.choices[0].message.content.strip()
            # Clean up potential markdown formatting
            if raw_sql.startswith("```sql"):
                raw_sql = raw_sql[6:]
            if raw_sql.startswith("```"):
                raw_sql = raw_sql[3:]
            if raw_sql.endswith("```"):
                raw_sql = raw_sql[:-3]
            raw_sql = raw_sql.strip()

            allow_all_rows = "all rows" in user_message.lower() or "every row" in user_message.lower()
            validation = validate_sql(raw_sql, schema, intent, table_name, allow_all_rows)
            
            if validation["valid"]:
                return {"sql": raw_sql, "error_message": ""}
            else:
                last_error = validation["error_message"]
                # Append the error to the prompt for the next retry
                user_message += f"\n\nNote: Your previous SQL failed validation: {last_error}. Please fix it."
                attempts += 1
                logger.warning(f"[SQLGenerator] Validation failed: {last_error}. Retrying ({attempts}/{max_retries})...")
                
        except Exception as e:
            logger.error(f"[SQLGenerator] Generation error: {e}")
            return {"sql": "", "error_message": f"LLM Generation Error: {str(e)}"}
            
    return {"sql": "", "error_message": f"Failed to generate valid SQL after {max_retries} retries. Last error: {last_error}"}
