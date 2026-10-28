"""Tầng lưu trữ: đọc/ghi metadata JSON và file đính kèm. Không chứa code giao diện."""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from config import DATA_DIR, INIT_MARKER, META_DIR


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def parse_tags(text: str) -> List[str]:
    """Tách tags theo dấu phẩy, bỏ trùng nhưng giữ thứ tự nhập."""
    return list(dict.fromkeys(t.strip() for t in text.split(",") if t.strip()))


def save_meta(doc: dict) -> None:
    """Ghi nguyên tử: ghi file tạm rồi thay thế để tránh hỏng JSON."""
    path = META_DIR / f"{doc['id']}.json"
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=4)
    tmp.replace(path)


def load_all_metadata() -> Tuple[List[dict], List[str]]:
    """Trả về (danh sách tài liệu, danh sách thông báo lỗi)."""
    documents, errors = [], []
    for path in sorted(META_DIR.glob("*.json")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except (json.JSONDecodeError, OSError):
            errors.append(f"Bỏ qua file metadata lỗi: {path.name}")
            continue
        doc.setdefault("id", path.stem)
        doc.setdefault("title", "(Không có tiêu đề)")
        doc.setdefault("author", "Chưa rõ")
        doc.setdefault("source", "Không rõ")
        doc.setdefault("tags", [])
        doc.setdefault("notes", "")
        doc.setdefault("file", None)
        doc.setdefault("created_at", "")
        documents.append(doc)
    documents.sort(key=lambda d: d["created_at"], reverse=True)
    return documents, errors


def create_document(
    title: str, author: str, tags_text: str, uploaded_file=None
) -> dict:
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    saved_name = None
    if uploaded_file is not None:
        saved_name = f"{doc_id}_{Path(uploaded_file.name).name}"
        (DATA_DIR / saved_name).write_bytes(uploaded_file.getbuffer())

    doc = {
        "id": doc_id,
        "title": title.strip(),
        "author": author.strip() or "Chưa rõ",
        "source": "Local Upload" if saved_name else "Manual Input",
        "tags": parse_tags(tags_text),
        "notes": "",
        "file": saved_name,
        "created_at": _now(),
    }
    save_meta(doc)
    return doc


def update_notes(doc: dict, notes: str) -> None:
    doc["notes"] = notes
    save_meta(doc)


def delete_doc(doc: dict) -> None:
    (META_DIR / f"{doc['id']}.json").unlink(missing_ok=True)
    if doc.get("file"):
        (DATA_DIR / doc["file"]).unlink(missing_ok=True)


def get_file_path(doc: dict) -> Optional[Path]:
    """Trả về đường dẫn file đính kèm nếu tồn tại."""
    if not doc.get("file"):
        return None
    path = DATA_DIR / doc["file"]
    return path if path.exists() else None


def original_filename(doc: dict) -> str:
    """Tên file gốc (bỏ tiền tố doc_xxxx_)."""
    return doc["file"].split("_", 2)[-1] if doc.get("file") else ""


def init_sample_data() -> None:
    """Chỉ tạo dữ liệu mẫu đúng một lần."""
    if INIT_MARKER.exists():
        return
    if not any(META_DIR.glob("*.json")):
        save_meta(
            {
                "id": "doc_sample",
                "title": "Lập trình Python cơ bản và nâng cao",
                "author": "Nguyễn Văn A",
                "source": "Local Upload",
                "tags": ["Python", "Programming"],
                "notes": "Tài liệu tham khảo chính cho đồ án.",
                "file": None,
                "created_at": _now(),
            }
        )
    INIT_MARKER.touch()
