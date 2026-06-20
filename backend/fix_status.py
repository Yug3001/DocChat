"""Fix status column from ENUM to VARCHAR with lowercase values."""
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import text
from db.database import engine

with engine.connect() as conn:
    # Step 1: Change ENUM to VARCHAR to allow custom casing
    try:
        conn.execute(text(
            "ALTER TABLE documents MODIFY COLUMN status VARCHAR(20) NOT NULL DEFAULT 'ready'"
        ))
        conn.commit()
        print("Changed status column type to VARCHAR(20)")
    except Exception as e:
        print(f"Column type change: {e}")
        conn.rollback()

    # Step 2: Normalise existing values to lowercase
    try:
        r1 = conn.execute(text("UPDATE documents SET status = 'ready' WHERE status = 'READY'"))
        r2 = conn.execute(text("UPDATE documents SET status = 'processing' WHERE status = 'PROCESSING'"))
        r3 = conn.execute(text("UPDATE documents SET status = 'error' WHERE status = 'ERROR'"))
        r4 = conn.execute(text("UPDATE documents SET status = 'error' WHERE status = 'FAILED'"))
        r5 = conn.execute(text("UPDATE documents SET status = 'processing' WHERE status = 'PENDING'"))
        conn.commit()
        total = r1.rowcount + r2.rowcount + r3.rowcount + r4.rowcount + r5.rowcount
        print(f"Normalised {total} rows to lowercase status")
    except Exception as e:
        print(f"Row normalisation error: {e}")
        conn.rollback()

    # Verify
    rows = conn.execute(text("SELECT DISTINCT status, COUNT(*) as cnt FROM documents GROUP BY status")).fetchall()
    print("Final status breakdown:", [(r[0], r[1]) for r in rows])
