"""
dataset_sql_executor.py
Executes the validated SQL and generates the undo query for mutations.
"""
import os
import logging
from typing import Dict, Any
from groq import Groq
from .dataset_csv_manager import execute_pandas_sql
from .dataset_mysql_connector import execute_mysql_sql, decrypt_credentials

logger = logging.getLogger(__name__)

_TEXT_MODEL = os.getenv("GROQ_TEXT_MODEL", "llama-3.3-70b-versatile")
_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_reverse_sql(forward_sql: str, intent: str, source_type: str) -> str:
    """
    Generates a reverse SQL statement to undo the forward_sql if possible.
    """
    if intent in ["DATA_QUERY", "SCHEMA_QUERY", "DOWNLOAD", "RESET", "NON_DATASET", "AMBIGUOUS"]:
        return ""
        
    system_prompt = f"""You are an expert SQL analyst. 
Given a forward SQL query that modifies a {source_type} database, generate the exact reverse SQL query that would undo the operation if executed immediately after.
If the operation cannot be easily reversed without knowing the prior state (e.g. UPDATE without knowing previous values, or DELETE without having the deleted data), generate a best-effort reverse query but it's okay if it's imperfect. The system warns users about this limitation.

Rules:
1. Return ONLY the raw SQL string. Do not use markdown blocks (e.g. ```sql).
2. Do not include any explanations.
3. If it is fundamentally impossible to reverse (like DROP COLUMN), return an empty string.
"""
    try:
        response = _client.chat.completions.create(
            model=_TEXT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Forward SQL: {forward_sql}"}
            ],
            temperature=0.1,
            max_tokens=500
        )
        
        reverse_sql = response.choices[0].message.content.strip()
        if reverse_sql.startswith("```sql"):
            reverse_sql = reverse_sql[6:]
        if reverse_sql.startswith("```"):
            reverse_sql = reverse_sql[3:]
        if reverse_sql.endswith("```"):
            reverse_sql = reverse_sql[:-3]
            
        return reverse_sql.strip()
    except Exception as e:
        logger.error(f"[SQLExecutor] Failed to generate reverse SQL: {e}")
        return ""

def execute_sql(
    source_type: str, 
    dataset_id: str, 
    sql: str, 
    connection_details: dict = None
) -> Dict[str, Any]:
    """
    Executes SQL on the target source.
    Returns: {"success": bool, "results": list, "rows_affected": int, "error_message": str}
    """
    if source_type.upper() == "CSV":
        return execute_pandas_sql(dataset_id, sql)
    elif source_type.upper() == "MYSQL":
        if not connection_details:
            return {"success": False, "results": [], "rows_affected": 0, "error_message": "Missing MySQL credentials."}
        # Connection details might be encrypted, but they are stored as JSON strings in the DB
        # if using Fernet. 
        if isinstance(connection_details, str):
            creds = decrypt_credentials(connection_details)
        else:
            creds = connection_details
            
        # Ensure we decrypt if they have a specific format, but we'll assume they are 
        # passed decrypted or handled by the caller. Actually, let's just pass raw creds.
        return execute_mysql_sql(creds, sql)
    else:
        return {"success": False, "results": [], "rows_affected": 0, "error_message": f"Unsupported source type: {source_type}"}
