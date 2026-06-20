"""
dataset_csv_manager.py
Manages CSV storage, versioning, and working copies.
"""
import os
import shutil
import pandas as pd
from typing import Dict, Any, List

STORAGE_PATH = os.getenv("STORAGE_PATH", "./storage")
os.makedirs(STORAGE_PATH, exist_ok=True)

def get_original_path(dataset_id: str) -> str:
    """Returns the path to the original, immutable V0 CSV."""
    return os.path.join(STORAGE_PATH, f"{dataset_id}_v0.csv")

def get_working_copy_path(dataset_id: str) -> str:
    """Returns the path to the current working copy CSV."""
    return os.path.join(STORAGE_PATH, f"{dataset_id}_working.csv")

def save_initial_csv(dataset_id: str, file_contents: bytes) -> str:
    """Saves the initial CSV as V0 and creates the first working copy."""
    v0_path = get_original_path(dataset_id)
    working_path = get_working_copy_path(dataset_id)
    
    with open(v0_path, "wb") as f:
        f.write(file_contents)
        
    shutil.copy2(v0_path, working_path)
    return working_path

def reset_to_v0(dataset_id: str) -> bool:
    """Overwrites the working copy with the original V0 CSV."""
    v0_path = get_original_path(dataset_id)
    working_path = get_working_copy_path(dataset_id)
    
    if os.path.exists(v0_path):
        shutil.copy2(v0_path, working_path)
        return True
    return False

def get_row_count(dataset_id: str) -> int:
    """Returns the total number of rows in the working copy."""
    try:
        working_path = get_working_copy_path(dataset_id)
        # Fast way to count rows without loading entire file
        with open(working_path, 'r', encoding='utf-8') as f:
            return sum(1 for _ in f) - 1 # Subtract header
    except Exception:
        return 0

def get_sample_rows(dataset_id: str, limit: int = 5) -> List[dict]:
    """Returns a sample of rows from the working copy."""
    try:
        working_path = get_working_copy_path(dataset_id)
        df = pd.read_csv(working_path, nrows=limit)
        return df.to_dict(orient='records')
    except Exception:
        return []

def execute_pandas_sql(dataset_id: str, sql: str) -> Dict[str, Any]:
    """
    Executes a SQL-like query on the CSV using in-memory SQLite.
    Mutations are persisted back to the working CSV copy.
    """
    import sqlite3

    working_path = get_working_copy_path(dataset_id)
    if not os.path.exists(working_path):
        return {"success": False, "results": [], "rows_affected": 0, "error_message": "Dataset file not found."}

    df = pd.read_csv(working_path)
    table_name = "dataset"

    conn = sqlite3.connect(":memory:")
    try:
        df.to_sql(table_name, conn, index=False, if_exists="replace")

        cursor = conn.cursor()
        cursor.execute(sql)

        sql_upper = sql.strip().upper()
        if sql_upper.startswith("SELECT"):
            if cursor.description is None:
                return {"success": True, "results": [], "rows_affected": 0}
            columns = [description[0] for description in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return {"success": True, "results": results, "rows_affected": 0}

        conn.commit()
        rows_affected = cursor.rowcount if cursor.rowcount >= 0 else 0

        modified_df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
        modified_df.to_csv(working_path, index=False)

        return {"success": True, "results": [], "rows_affected": rows_affected}

    except Exception as e:
        return {"success": False, "results": [], "rows_affected": 0, "error_message": str(e)}
    finally:
        conn.close()
