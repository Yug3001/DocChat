"""
dataset.py
Router for dataset linking and natural language CRUD.
"""
import uuid
import json
import logging
import asyncio
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db, SessionLocal
import db.models
from db.dataset_models import DatasetRegistry, MutationLog, QueryCache

from services.dataset_csv_manager import save_initial_csv, get_working_copy_path, reset_to_v0, get_row_count, get_sample_rows
from services.dataset_schema_inspector import (
    extract_csv_schema,
    extract_mysql_schema,
    detect_drift,
    normalize_schema,
    get_table_name_from_snapshot
)
from services.dataset_mysql_connector import test_connection, encrypt_credentials, decrypt_credentials, execute_mysql_sql, get_engine
from services.dataset_intent_classifier import classify_intent
from services.dataset_sql_generator import generate_sql
from services.dataset_sql_validator import validate_sql
from services.dataset_sql_executor import execute_sql, generate_reverse_sql

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Pydantic Models ---

class MySQLConnectionRequest(BaseModel):
    host: str
    port: int = 3306
    database: str
    username: str
    password: str

class MySQLRegisterRequest(MySQLConnectionRequest):
    table_name: str
    display_name: str

class ChatRequest(BaseModel):
    message: str
    session_id: str

class ConfirmRequest(BaseModel):
    forward_sql: str
    reverse_sql: Optional[str] = None
    intent: str
    description: str

class ChatResponse(BaseModel):
    # This won't be used directly since we stream, but good for docs
    pass

# --- Endpoints ---

@router.post("/csv/upload")
async def upload_csv(
    file: UploadFile = File(...),
    display_name: str = Form(...),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")
        
    dataset_id = str(uuid.uuid4())
    content = await file.read()
    
    # Save CSV and create working copy
    working_path = save_initial_csv(dataset_id, content)
    
    # Extract schema and row count
    try:
        schema = extract_csv_schema(working_path)
        row_count = get_row_count(dataset_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")
        
    # Register in DB
    dataset = DatasetRegistry(
        dataset_id=dataset_id,
        source_type="CSV",
        schema_snapshot=schema,
        row_count=row_count,
        display_name=display_name
    )
    db.add(dataset)
    db.commit()
    
    return {"dataset_id": dataset_id, "message": "CSV uploaded and registered successfully."}

@router.post("/mysql/test-connection")
async def test_mysql_connection(req: MySQLConnectionRequest):
    creds = req.model_dump()
    result = test_connection(creds)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error_message"])
    return {"tables": result["tables"]}

@router.post("/mysql/register")
async def register_mysql(req: MySQLRegisterRequest, db: Session = Depends(get_db)):
    creds = {
        "host": req.host, "port": req.port, "database": req.database,
        "username": req.username, "password": req.password
    }
    
    # Verify connection again
    test_res = test_connection(creds)
    if not test_res["success"] or req.table_name not in test_res["tables"]:
        raise HTTPException(status_code=400, detail=f"Cannot access table {req.table_name}")
        
    dataset_id = str(uuid.uuid4())
    
    try:
        engine = get_engine(creds)
        schema = extract_mysql_schema(engine, req.table_name)
        
        # Count rows
        with engine.connect() as conn:
            import sqlalchemy as sa
            res = conn.execute(sa.text(f"SELECT COUNT(*) FROM `{req.table_name}`")).scalar()
            row_count = res or 0
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract schema: {str(e)}")
        
    enc_creds = encrypt_credentials(creds)
    
    dataset = DatasetRegistry(
        dataset_id=dataset_id,
        source_type="MYSQL",
        connection_details=enc_creds,
        schema_snapshot=schema,
        row_count=row_count,
        display_name=req.display_name
    )
    # We also store table_name in schema_snapshot for convenience
    schema["table_name"] = req.table_name
    dataset.schema_snapshot = schema
    
    db.add(dataset)
    db.commit()
    
    return {"dataset_id": dataset_id, "message": "MySQL table registered successfully."}

@router.get("/list")
async def list_datasets(db: Session = Depends(get_db)):
    datasets = db.query(DatasetRegistry).order_by(DatasetRegistry.created_at.desc()).all()
    return {"datasets": [
        {
            "dataset_id": ds.dataset_id,
            "display_name": ds.display_name,
            "source_type": ds.source_type,
            "version": ds.version,
            "status": ds.status,
            "row_count": ds.row_count,
            "created_at": ds.created_at.isoformat() if ds.created_at else None
        } for ds in datasets
    ]}

@router.get("/{dataset_id}/schema")
async def get_schema(dataset_id: str, db: Session = Depends(get_db)):
    ds = db.query(DatasetRegistry).filter(DatasetRegistry.dataset_id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    sample_rows = []
    if ds.source_type == "CSV":
        sample_rows = get_sample_rows(dataset_id)
    elif ds.source_type == "MYSQL":
        creds = decrypt_credentials(ds.connection_details)
        table_name = get_table_name_from_snapshot(ds.schema_snapshot, ds.display_name)
        res = execute_mysql_sql(creds, f"SELECT * FROM `{table_name}` LIMIT 5")
        if res["success"]:
            sample_rows = res["results"]
            
    return {
        "dataset": {
            "dataset_id": ds.dataset_id,
            "source_type": ds.source_type,
            "display_name": ds.display_name,
            "version": ds.version,
            "status": ds.status,
            "schema_snapshot": ds.schema_snapshot,
            "row_count": ds.row_count,
        },
        "schema": ds.schema_snapshot,
        "row_count": ds.row_count,
        "sample_rows": sample_rows
    }

@router.get("/{dataset_id}/preview")
async def preview_data(dataset_id: str, limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    ds = db.query(DatasetRegistry).filter(DatasetRegistry.dataset_id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    if ds.source_type == "CSV":
        sql = f"SELECT * FROM dataset LIMIT {limit} OFFSET {offset}"
        res = execute_sql("CSV", dataset_id, sql)
        if not res["success"]:
            raise HTTPException(status_code=500, detail=res["error_message"])
        return {"data": res["results"], "total": ds.row_count}
        
    elif ds.source_type == "MYSQL":
        creds = decrypt_credentials(ds.connection_details)
        table_name = get_table_name_from_snapshot(ds.schema_snapshot, ds.display_name)
        sql = f"SELECT * FROM `{table_name}` LIMIT {limit} OFFSET {offset}"
        res = execute_mysql_sql(creds, sql)
        if not res["success"]:
            raise HTTPException(status_code=500, detail=res["error_message"])
        return {"data": res["results"], "total": ds.row_count}

@router.get("/{dataset_id}/history")
async def get_history(dataset_id: str, db: Session = Depends(get_db)):
    mutations = db.query(MutationLog).filter(MutationLog.dataset_id == dataset_id).order_by(MutationLog.executed_at.desc()).all()
    return {"history": [
        {
            "mutation_id": m.mutation_id,
            "version": m.version,
            "operation_type": m.operation_type,
            "description": m.description,
            "rows_affected": m.rows_affected,
            "success": m.success,
            "error_message": m.error_message,
            "executed_at": m.executed_at.isoformat(),
            "reversible": m.reversible_flag
        } for m in mutations
    ]}

@router.get("/{dataset_id}/download")
async def download_csv(dataset_id: str, db: Session = Depends(get_db)):
    ds = db.query(DatasetRegistry).filter(DatasetRegistry.dataset_id == dataset_id).first()
    if not ds or ds.source_type != "CSV":
        raise HTTPException(status_code=400, detail="Invalid dataset or not a CSV.")
        
    path = get_working_copy_path(dataset_id)
    return FileResponse(path, filename=f"{ds.display_name}_v{ds.version}.csv")

@router.post("/{dataset_id}/reset")
async def reset_csv(dataset_id: str, db: Session = Depends(get_db)):
    ds = db.query(DatasetRegistry).filter(DatasetRegistry.dataset_id == dataset_id).first()
    if not ds or ds.source_type != "CSV":
        raise HTTPException(status_code=400, detail="Invalid dataset or not a CSV.")
        
    success = reset_to_v0(dataset_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to reset to V0.")
        
    ds.version += 1
    ds.row_count = get_row_count(dataset_id)
    
    mut = MutationLog(
        mutation_id=str(uuid.uuid4()),
        dataset_id=dataset_id,
        version=ds.version,
        operation_type="RESET",
        description="Reset dataset back to original V0 state.",
        forward_sql="",
        reverse_sql="",
        rows_affected=ds.row_count,
        success=True,
        reversible_flag=False
    )
    db.add(mut)
    db.commit()
    return {"message": "Dataset reset successfully."}

@router.post("/{dataset_id}/sync")
async def sync_mysql(dataset_id: str, db: Session = Depends(get_db)):
    ds = db.query(DatasetRegistry).filter(DatasetRegistry.dataset_id == dataset_id).first()
    if not ds or ds.source_type != "MYSQL":
        raise HTTPException(status_code=400, detail="Invalid dataset or not MYSQL.")
        
    creds = decrypt_credentials(ds.connection_details)
    table_name = get_table_name_from_snapshot(ds.schema_snapshot, ds.display_name)
    
    try:
        engine = get_engine(creds)
        new_schema = extract_mysql_schema(engine, table_name)
        new_schema["table_name"] = table_name
        
        has_drift, drift_issues = detect_drift(new_schema, ds.schema_snapshot)
        
        with engine.connect() as conn:
            import sqlalchemy as sa
            res = conn.execute(sa.text(f"SELECT COUNT(*) FROM `{table_name}`")).scalar()
            ds.row_count = res or 0
            
        ds.schema_snapshot = new_schema
        db.commit()
        
        return {
            "message": "Schema synchronized.", 
            "has_drift": has_drift, 
            "drift_issues": drift_issues
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{dataset_id}/undo/{mutation_id}")
async def undo_mutation(dataset_id: str, mutation_id: str, db: Session = Depends(get_db)):
    ds = db.query(DatasetRegistry).filter(DatasetRegistry.dataset_id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    mut = db.query(MutationLog).filter(MutationLog.mutation_id == mutation_id, MutationLog.dataset_id == dataset_id).first()
    if not mut or not mut.success or not mut.reversible_flag or not mut.reverse_sql:
        raise HTTPException(status_code=400, detail="Mutation cannot be undone.")
        
    res = execute_sql(ds.source_type, dataset_id, mut.reverse_sql, ds.connection_details)
    if not res["success"]:
        raise HTTPException(status_code=500, detail=res["error_message"])
        
    ds.version += 1
    
    undo_mut = MutationLog(
        mutation_id=str(uuid.uuid4()),
        dataset_id=dataset_id,
        version=ds.version,
        operation_type="UNDO",
        description=f"Undid operation: {mut.description}",
        forward_sql=mut.reverse_sql,
        reverse_sql=mut.forward_sql,  # Re-reversable
        rows_affected=res.get("rows_affected", 0),
        success=True,
        reversible_flag=True
    )
    db.add(undo_mut)
    db.commit()
    
    return {"message": "Undo successful"}

@router.post("/{dataset_id}/confirm")
async def confirm_mutation(dataset_id: str, req: ConfirmRequest, db: Session = Depends(get_db)):
    ds = db.query(DatasetRegistry).filter(DatasetRegistry.dataset_id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")

    table_name = "dataset" if ds.source_type == "CSV" else get_table_name_from_snapshot(ds.schema_snapshot, ds.display_name)
    validation = validate_sql(req.forward_sql, ds.schema_snapshot, req.intent, table_name, allow_all_rows=True)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["error_message"])

    res = execute_sql(ds.source_type, dataset_id, req.forward_sql, ds.connection_details)
    if not res["success"]:
        failed_mut = MutationLog(
            mutation_id=str(uuid.uuid4()),
            dataset_id=dataset_id,
            version=ds.version,
            operation_type=req.intent,
            description=req.description,
            forward_sql=req.forward_sql,
            reverse_sql="",
            success=False,
            error_message=res["error_message"]
        )
        db.add(failed_mut)
        db.commit()
        raise HTTPException(status_code=500, detail=res["error_message"])

    ds.version += 1

    if ds.source_type == "CSV":
        ds.row_count = get_row_count(dataset_id)
    elif ds.source_type == "MYSQL":
        try:
            creds = decrypt_credentials(ds.connection_details)
            table_name = get_table_name_from_snapshot(ds.schema_snapshot, ds.display_name)
            engine = get_engine(creds)
            import sqlalchemy as sa
            with engine.connect() as conn:
                ds.row_count = conn.execute(sa.text(f"SELECT COUNT(*) FROM `{table_name}`")).scalar() or 0
        except Exception as e:
            logger.warning(f"[Confirm] Could not refresh row count: {e}")

    reverse_sql = req.reverse_sql
    if not reverse_sql:
        reverse_sql = generate_reverse_sql(req.forward_sql, req.intent, ds.source_type)

    reversible = bool(reverse_sql.strip())

    mut = MutationLog(
        mutation_id=str(uuid.uuid4()),
        dataset_id=dataset_id,
        version=ds.version,
        operation_type=req.intent,
        description=req.description,
        forward_sql=req.forward_sql,
        reverse_sql=reverse_sql,
        rows_affected=res.get("rows_affected", 0),
        success=True,
        reversible_flag=reversible
    )
    db.add(mut)
    db.commit()

    return {
        "message": "Mutation executed successfully.",
        "rows_affected": res.get("rows_affected", 0),
        "version": ds.version,
        "source_type": ds.source_type,
        "dataset_id": dataset_id,
    }

@router.post("/{dataset_id}/chat")
async def chat(dataset_id: str, req: ChatRequest, db: Session = Depends(get_db)):
    ds = db.query(DatasetRegistry).filter(DatasetRegistry.dataset_id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    from routers.chat import _save_message
    _save_message(db, req.session_id, "user", req.message, session_type="database")
    
    # Capture database attributes locally to avoid detached session issues during streaming
    source_type = ds.source_type
    schema_snapshot = ds.schema_snapshot
    row_count = ds.row_count
    connection_details = ds.connection_details
    display_name = ds.display_name
        
    # SSE Stream generator
    async def sse_stream():
        assistant_text = []
        def yield_text(t: str):
            assistant_text.append(t)
            return f"data: {json.dumps({'type': 'text', 'text': t})}\n\n"
        def yield_block(type_name: str, content: dict = None):
            obj = {"type": type_name}
            if content:
                obj.update(content)
            return f"data: {json.dumps(obj)}\n\n"
            
        try:
            # 1. Classify intent
            yield yield_block("thinking", {"status": "Classifying intent..."})
        
            sample_rows = []
            table_name = "dataset"
            if source_type == "CSV":
                sample_rows = get_sample_rows(dataset_id, 3)
            elif source_type == "MYSQL":
                table_name = get_table_name_from_snapshot(schema_snapshot, display_name)
                creds = decrypt_credentials(connection_details)
                # Drift check
                engine = get_engine(creds)
                try:
                    current_schema = extract_mysql_schema(engine, table_name)
                    drift, issues = detect_drift(current_schema, schema_snapshot)
                    if drift:
                        yield yield_text(f"⚠️ **Schema Drift Detected!**\nThe live database schema has changed since it was registered.\n\nIssues:\n- " + "\n- ".join(issues) + "\n\nPlease click the 'Sync Schema' button before running queries.")
                        yield yield_block("block_end")
                        return
                except Exception as e:
                    pass # Ignore connection issues during chat, will fail later
                
                res = await asyncio.to_thread(execute_mysql_sql, creds, f"SELECT * FROM `{table_name}` LIMIT 3")
                if res["success"]:
                    sample_rows = res["results"]
                
            classification = await asyncio.to_thread(classify_intent, req.message, schema_snapshot, row_count, source_type)
            intent = classification["intent"]
        
            if intent == "NON_DATASET":
                yield yield_text("This question seems unrelated to the dataset. Please switch to the regular Document Chat for general questions.")
                yield yield_block("block_end")
                return
            
            if intent == "AMBIGUOUS":
                yield yield_text(f"I need clarification: {classification['explanation']}")
                yield yield_block("block_end")
                return
            
            if intent in ["DOWNLOAD", "RESET"]:
                yield yield_text(f"You can {intent.lower()} the dataset using the buttons in the dataset panel above.")
                yield yield_block("block_end")
                return
            
            yield yield_block("thinking", {"status": f"Intent identified: {intent}. Generating SQL..."})
        
            # 2. Generate SQL
            gen_res = await asyncio.to_thread(generate_sql, schema_snapshot, row_count, sample_rows, intent, source_type, req.message, table_name)
        
            if not gen_res.get("sql"):
                yield yield_text(f"❌ Failed to generate valid SQL: {gen_res.get('error_message')}")
                yield yield_block("block_end")
                return
            
            sql = gen_res["sql"]
        
            # 3. Handle READ operations directly
            if intent in ["SCHEMA_QUERY", "DATA_QUERY"]:
                yield yield_block("thinking", {"status": "Executing query..."})
                exec_res = await asyncio.to_thread(execute_sql, source_type, dataset_id, sql, connection_details)
            
                if not exec_res["success"]:
                    yield yield_text(f"❌ Execution failed: {exec_res['error_message']}")
                else:
                    results = exec_res["results"]
                
                    # Format results for LLM to summarize
                    yield yield_block("thinking", {"status": "Summarizing results..."})
                
                    summary_prompt = f"User asked: {req.message}\nSQL Executed: {sql}\nResults (truncated if large): {str(results)[:2000]}\nProvide a concise, helpful summary of these results to the user."
                
                    try:
                        from services.llm import client as groq_client, _TEXT_MODEL
                    
                        def fetch_summary():
                            return groq_client.chat.completions.create(
                                model=_TEXT_MODEL,
                                messages=[{"role": "user", "content": summary_prompt}],
                                temperature=0.2,
                                max_tokens=1000,
                                stream=True
                            )
                        
                        resp = await asyncio.to_thread(fetch_summary)
                    
                        yield yield_text(f"**Query Executed:**\n```sql\n{sql}\n```\n\n**Results:**\n")
                    
                        for chunk in resp:
                            if chunk.choices[0].delta.content:
                                yield yield_text(chunk.choices[0].delta.content)
                            await asyncio.sleep(0)
                    except Exception as e:
                        yield yield_text(f"**Query Executed:**\n```sql\n{sql}\n```\n\n**Results (Raw):**\n```text\n{str(results)[:2000]}\n```\n\n*(Failed to generate summary: {str(e)})*")
            else:
                # 4. Handle WRITE operations via Confirm flow
                yield yield_text(f"I have prepared a modification based on your request:\n\n```sql\n{sql}\n```\n\n")
                yield yield_text(f"**Explanation:** {classification['explanation']}\n\n")
            
                # For MySQL, prominently display the warning
                if source_type == "MYSQL":
                    yield yield_text("⚠️ **WARNING: Changes will be permanently written to the external database.**\n\n")
                
                # Send a special structured JSON block that the frontend can parse to show the confirm dialog
                confirm_payload = {
                    "action": "REQUIRE_CONFIRMATION",
                    "sql": sql,
                    "intent": intent,
                    "description": classification['explanation']
                }
                yield f"data: {json.dumps({'type': 'json_payload', 'payload': confirm_payload})}\n\n"
            
            yield yield_block("block_end")
            full_reply = "".join(assistant_text)
            if full_reply:
                with SessionLocal() as local_db:
                    _save_message(local_db, req.session_id, "assistant", full_reply, session_type="database")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            yield yield_text(f"❌ **Stream crashed with Unhandled Exception:**\n```\n{tb}\n```")
            yield yield_block("block_end")
            full_reply = "".join(assistant_text)
            if full_reply:
                with SessionLocal() as local_db:
                    _save_message(local_db, req.session_id, "assistant", full_reply, session_type="database")

    return StreamingResponse(sse_stream(), media_type="text/event-stream")
