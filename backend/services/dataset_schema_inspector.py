"""
dataset_schema_inspector.py
Extracts schema from MySQL and CSV. Detects schema drift.
"""
import pandas as pd
import sqlalchemy as sa
import json
from typing import Dict, Any, Tuple, List

def normalize_schema(schema: Any) -> dict:
    """
    Normalizes a schema snapshot to always be a dict with a 'columns' key.
    Handles list formats, dict formats, and JSON strings.
    """
    if not schema:
        return {"columns": []}
    if isinstance(schema, str):
        try:
            schema = json.loads(schema)
        except Exception:
            return {"columns": []}
    
    if isinstance(schema, list):
        return {"columns": schema}
    
    if isinstance(schema, dict):
        if "columns" not in schema:
            return {"columns": []}
        return schema
        
    return {"columns": []}

def get_table_name_from_snapshot(snapshot: Any, display_name: str) -> str:
    """
    Safely retrieves the table name from a schema snapshot.
    If the snapshot is a JSON string, it parses it first.
    If it cannot be found, falls back to display_name (normalized).
    """
    if not snapshot:
        return _normalize_display_name(display_name)
    if isinstance(snapshot, str):
        try:
            snapshot = json.loads(snapshot)
        except Exception:
            pass
            
    if isinstance(snapshot, dict) and snapshot.get("table_name"):
        return snapshot["table_name"]
        
    return _normalize_display_name(display_name)

def _normalize_display_name(display_name: str) -> str:
    name = display_name.strip()
    if name.lower().endswith(" table"):
        name = name[:-6].strip()
    name_lower = name.lower()
    if name_lower == "document":
        return "documents"
    elif name_lower == "chunk":
        return "chunks"
    return name_lower

def extract_csv_schema(file_path: str) -> Dict[str, Any]:
    """Extracts schema from a CSV file using Pandas."""
    df = pd.read_csv(file_path, nrows=5)
    columns = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        # Map pandas dtype to SQL-like dtype
        if "int" in dtype:
            sql_type = "INTEGER"
        elif "float" in dtype:
            sql_type = "FLOAT"
        elif "bool" in dtype:
            sql_type = "BOOLEAN"
        else:
            sql_type = "VARCHAR"
        
        columns.append({
            "name": col,
            "type": sql_type
        })
    return {"columns": columns}

def extract_mysql_schema(engine: sa.Engine, table_name: str) -> Dict[str, Any]:
    """Extracts schema from a MySQL table using SQLAlchemy."""
    inspector = sa.inspect(engine)
    if not inspector.has_table(table_name):
        raise ValueError(f"Table '{table_name}' does not exist.")
    
    columns = []
    for col in inspector.get_columns(table_name):
        columns.append({
            "name": col["name"],
            "type": str(col["type"])
        })
    return {"columns": columns}

def detect_drift(current_schema: Any, snapshot_schema: Any) -> Tuple[bool, List[str]]:
    """
    Compares current live schema to the stored snapshot schema.
    Returns: (has_drift, list_of_drift_descriptions)
    """
    if not snapshot_schema:
        return False, []
        
    curr_norm = normalize_schema(current_schema)
    snap_norm = normalize_schema(snapshot_schema)
    
    current_cols = {c["name"]: (c.get("type") or c.get("dtype") or "") for c in curr_norm.get("columns", []) if isinstance(c, dict) and "name" in c}
    snapshot_cols = {c["name"]: (c.get("type") or c.get("dtype") or "") for c in snap_norm.get("columns", []) if isinstance(c, dict) and "name" in c}
    
    drift_issues = []
    
    # Check for added or modified columns
    for name, dtype in current_cols.items():
        if name not in snapshot_cols:
            drift_issues.append(f"Added column: {name} ({dtype})")
        elif snapshot_cols[name] != dtype:
            drift_issues.append(f"Changed data type for column {name}: {snapshot_cols[name]} -> {dtype}")
            
    # Check for removed columns
    for name in snapshot_cols:
        if name not in current_cols:
            drift_issues.append(f"Removed column: {name}")
            
    return len(drift_issues) > 0, drift_issues
