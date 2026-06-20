"""
dataset_mysql_connector.py
Handles live connections and queries to external MySQL databases.
"""
import os
import logging
from typing import Dict, Any, List
import sqlalchemy as sa
from cryptography.fernet import Fernet
import json

logger = logging.getLogger(__name__)

# Use a static key for encryption for simplicity in this project,
# ideally this would be an env var ENCRYPTION_KEY.
_ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode("utf-8"))
_cipher_suite = Fernet(_ENCRYPTION_KEY.encode("utf-8"))

def encrypt_credentials(creds: dict) -> str:
    """Encrypts connection dictionary into a string."""
    return _cipher_suite.encrypt(json.dumps(creds).encode("utf-8")).decode("utf-8")

def decrypt_credentials(encrypted_str: str) -> dict:
    """Decrypts connection string back to dictionary."""
    if not encrypted_str:
        return {}
    return json.loads(_cipher_suite.decrypt(encrypted_str.encode("utf-8")).decode("utf-8"))

def get_engine(creds: dict) -> sa.Engine:
    """Creates a SQLAlchemy engine from credentials."""
    host = creds.get("host")
    port = creds.get("port", 3306)
    database = creds.get("database")
    username = creds.get("username")
    password = creds.get("password")
    
    url = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
    return sa.create_engine(url)

def test_connection(creds: dict) -> Dict[str, Any]:
    """
    Tests connection and returns a list of accessible tables.
    Returns: {"success": bool, "tables": list, "error_message": str}
    """
    try:
        engine = get_engine(creds)
        inspector = sa.inspect(engine)
        tables = inspector.get_table_names()
        return {"success": True, "tables": tables, "error_message": ""}
    except Exception as e:
        logger.error(f"[MySQLConnector] Connection test failed: {e}")
        return {"success": False, "tables": [], "error_message": str(e)}

def execute_mysql_sql(creds: dict, sql: str) -> Dict[str, Any]:
    """
    Executes a SQL query against the live MySQL DB.
    Returns: {"success": bool, "results": list, "rows_affected": int, "error_message": str}
    """
    try:
        engine = get_engine(creds)
        with engine.connect() as conn:
            # Wrap in text
            stmt = sa.text(sql)
            result = conn.execute(stmt)
            conn.commit()
            
            rows_affected = result.rowcount
            
            # If it's a SELECT query, fetch results
            if result.returns_rows:
                # result.keys() provides column names
                columns = list(result.keys())
                results = [dict(zip(columns, row)) for row in result.fetchall()]
                return {"success": True, "results": results, "rows_affected": 0, "error_message": ""}
            else:
                return {"success": True, "results": [], "rows_affected": rows_affected, "error_message": ""}
                
    except Exception as e:
        logger.error(f"[MySQLConnector] Execution error: {e}")
        return {"success": False, "results": [], "rows_affected": 0, "error_message": str(e)}
