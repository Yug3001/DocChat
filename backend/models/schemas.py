from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime


class DocumentOut(BaseModel):
    id:          str
    filename:    str
    file_type:   str
    chunk_count: int
    file_size:   int
    is_excel:    bool
    uploaded_at: datetime
    status:      str

    class Config:
        from_attributes = True


class ExcelMetaOut(BaseModel):
    doc_id:      str
    filename:    str
    sheet_names: List[str]
    columns:     Dict[str, List[str]]
    row_counts:  Dict[str, int]

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    message:      str
    session_id:   str
    document_ids: Optional[List[str]] = None


class UploadResponse(BaseModel):
    document: DocumentOut
    message:  str