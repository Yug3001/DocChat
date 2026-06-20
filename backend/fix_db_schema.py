#!/usr/bin/env python3
"""
Quick script to fix the documents table created_at column default value
Run from backend directory: python fix_db_schema.py
"""
import os
import sys
from sqlalchemy import text
from db.database import engine

def fix_database_schema():
    try:
        with engine.connect() as connection:
            # Get database type
            db_url = os.getenv("DATABASE_URL", "")
            
            if "mysql" in db_url.lower():
                # For MySQL
                sql = """
                ALTER TABLE documents 
                MODIFY COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
                """
                connection.execute(text(sql))
                print("✓ Fixed MySQL documents.created_at default")
                
            elif "postgresql" in db_url.lower():
                # For PostgreSQL
                sql = """
                ALTER TABLE documents 
                ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP,
                ALTER COLUMN created_at SET NOT NULL
                """
                connection.execute(text(sql))
                print("✓ Fixed PostgreSQL documents.created_at default")
                
            elif "sqlite" in db_url.lower():
                print("✓ SQLite doesn't require explicit defaults - should work")
                
            connection.commit()
            print("✓ Database schema fixed successfully!")
            return True
            
    except Exception as e:
        print(f"✗ Error fixing database: {e}")
        return False

if __name__ == "__main__":
    success = fix_database_schema()
    sys.exit(0 if success else 1)
