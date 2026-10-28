"""Cấu hình đường dẫn lưu trữ cục bộ (File-based, không dùng Database)."""
from pathlib import Path

META_ROOT = Path("metadata")        # metadata/<username>/*.json
DATA_ROOT = Path("raw_documents")   # raw_documents/<username>/<file>
USERS_DIR = Path("users")
USERS_FILE = USERS_DIR / "users.json"


def meta_dir(user: str) -> Path:
    return META_ROOT / user


def data_dir(user: str) -> Path:
    return DATA_ROOT / user


def ensure_dirs(user: str = None) -> None:
    for d in (META_ROOT, DATA_ROOT, USERS_DIR):
        d.mkdir(exist_ok=True)
    if user:
        meta_dir(user).mkdir(exist_ok=True)
        data_dir(user).mkdir(exist_ok=True)
