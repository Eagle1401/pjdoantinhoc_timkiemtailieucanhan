"""Cấu hình đường dẫn lưu trữ cục bộ (File-based, không dùng Database)."""
from pathlib import Path

DATA_DIR = Path("raw_documents")
META_DIR = Path("metadata")
INIT_MARKER = META_DIR / ".initialized"


def ensure_dirs() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    META_DIR.mkdir(exist_ok=True)
