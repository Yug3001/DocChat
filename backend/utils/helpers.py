import os
import uuid
from pathlib import Path

ALLOWED_EXTENSIONS = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.ms-excel": "xls",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
}

def generate_id() -> str:
    return str(uuid.uuid4())

def get_file_extension(content_type: str) -> str | None:
    return ALLOWED_EXTENSIONS.get(content_type)

def is_allowed_file(content_type: str) -> bool:
    return content_type in ALLOWED_EXTENSIONS

def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"

def build_storage_path(base_path: str, doc_id: str, extension: str) -> str:
    os.makedirs(base_path, exist_ok=True)
    return os.path.join(base_path, f"{doc_id}.{extension}")

def cleanup_file(file_path: str) -> None:
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass

def count_tokens_approx(text: str) -> int:
    # Rough approximation: 1 token ≈ 4 characters
    return len(text) // 4