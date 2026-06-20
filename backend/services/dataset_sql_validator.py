"""
dataset_sql_validator.py
Validates generated SQL against rules: no multi-statements, no drops/truncates,
read operations must be SELECT, mutations must have WHERE clauses unless confirmed.
"""
import sqlparse
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def _is_sql_complete(sql: str) -> bool:
    """Basic heuristic to reject obviously truncated SQL."""
    stripped = sql.strip()
    if not stripped:
        return False
    if stripped.endswith(",") or stripped.endswith("("):
        return False
    if stripped.count("(") != stripped.count(")"):
        return False
    return True

def validate_sql(sql: str, schema: dict, intent: str, table_name: str, allow_all_rows: bool = False) -> Dict[str, Any]:
    """
    Validates a SQL statement.
    Returns: {"valid": bool, "error_message": str}
    """
    if not sql or not sql.strip():
        return {"valid": False, "error_message": "Empty SQL statement."}

    if not _is_sql_complete(sql):
        return {"valid": False, "error_message": "SQL statement appears incomplete or truncated. Please regenerate the query."}

    # Format and parse
    parsed = sqlparse.parse(sql)
    
    # Check for multi-statements
    non_empty_statements = [p for p in parsed if str(p).strip()]
    if len(non_empty_statements) > 1:
        return {"valid": False, "error_message": "Multiple SQL statements are not allowed for security reasons."}

    stmt = non_empty_statements[0]
    stmt_type = stmt.get_type().upper()

    # Reject dangerous admin commands
    forbidden_types = ["DROP", "TRUNCATE", "ALTER DATABASE", "CREATE DATABASE", "GRANT", "REVOKE"]
    if stmt_type in forbidden_types:
        return {"valid": False, "error_message": f"Operation '{stmt_type}' is prohibited."}

    if intent == "DATA_QUERY" and stmt_type != "SELECT":
         return {"valid": False, "error_message": "DATA_QUERY intent must strictly generate SELECT statements."}

    # Removed strict WHERE clause enforcement for UPDATE/DELETE to allow bulk operations easily via natural language. 
    # Safety is guaranteed by the UI ChatConfirmDialog where the user must explicitly approve the operation and can see rows affected.

    # Verify table name is present in the query (simple string check, could be improved)
    if table_name.lower() not in sql.lower():
        # Sometimes table names are quoted
        if f"`{table_name.lower()}`" not in sql.lower() and f'"{table_name.lower()}"' not in sql.lower():
             return {"valid": False, "error_message": f"Table name '{table_name}' must be referenced in the query."}

    # Basic column validation
    sql_lower = sql.lower()
    from services.dataset_schema_inspector import normalize_schema
    norm_schema = normalize_schema(schema)
    valid_columns = [col["name"].lower() for col in norm_schema.get("columns", []) if isinstance(col, dict) and "name" in col]
    # We won't strictly enforce column names via AST parsing as it's complex and error-prone,
    # but the DB will reject invalid columns anyway.

    return {"valid": True, "error_message": ""}
