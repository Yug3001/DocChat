import sys
from sqlalchemy import create_engine, select
import os
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Get all datasets
    from sqlalchemy import text
    result = conn.execute(text("SELECT dataset_id, source_type, display_name, schema_snapshot FROM dataset_registry")).fetchall()
    
    for row in result:
        print("Dataset ID:", row[0])
        print("Source Type:", row[1])
        print("Display Name:", row[2])
        print("Schema Snapshot Type:", type(row[3]))
        print("Schema Snapshot:", row[3])
        print("-" * 50)
