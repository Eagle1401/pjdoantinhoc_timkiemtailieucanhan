"""Tầng lưu trữ theo từng người dùng. Không chứa code giao diện."""
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from config import DATA_ROOT, META_ROOT, data_dir, ensure_dirs, meta_dir


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def parse_tags(text: str) -> List[str]:
    """Tách tags theo dấu phẩy, bỏ trùng nhưng giữ thứ tự nhập."""
    return list(dict.fromkeys(t.strip() for t in text.split(",") if t.strip()))


def save_meta(user: str, doc: dict) -> None:
    """Ghi nguyên tử: ghi file tạm rồi thay thế để tránh hỏng JSON."""
    path = meta_dir(user) / f"{doc['id']}.json"
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=4)
    tmp.replace(path)


def load_all_metadata(user: str) -> Tuple[List[dict], List[str]]:
    """Trả về (danh sách tài liệu của user, danh sách thông báo lỗi)."""
    documents, errors = [], []
    for path in sorted(meta_dir(user).glob("*.json")):
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
    user: str, title: str, author: str, tags_text: str, uploaded_file=None
) -> dict:
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    saved_name = None
    if uploaded_file is not None:
        saved_name = f"{doc_id}_{Path(uploaded_file.name).name}"
        (data_dir(user) / saved_name).write_bytes(uploaded_file.getbuffer())

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
    save_meta(user, doc)
    return doc


def update_notes(user: str, doc: dict, notes: str) -> None:
    doc["notes"] = notes
    save_meta(user, doc)


def delete_doc(user: str, doc: dict) -> None:
    (meta_dir(user) / f"{doc['id']}.json").unlink(missing_ok=True)
    if doc.get("file"):
        (data_dir(user) / doc["file"]).unlink(missing_ok=True)


def get_file_path(user: str, doc: dict) -> Optional[Path]:
    """Trả về đường dẫn file đính kèm nếu tồn tại."""
    if not doc.get("file"):
        return None
    path = data_dir(user) / doc["file"]
    return path if path.exists() else None


def original_filename(doc: dict) -> str:
    """Tên file gốc (bỏ tiền tố doc_xxxx_)."""
    return doc["file"].split("_", 2)[-1] if doc.get("file") else ""


def init_sample_data(user: str) -> None:
    """Tạo dữ liệu mẫu đúng một lần cho mỗi người dùng."""
    marker = meta_dir(user) / ".initialized"
    if marker.exists():
        return
    if not any(meta_dir(user).glob("*.json")):
        save_meta(
            user,
            {
                "id": "doc_sample",
                "title": "Lập trình Python cơ bản và nâng cao",
                "author": "Nguyễn Văn A",
                "source": "Local Upload",
                "tags": ["Python", "Programming"],
                "notes": "Tài liệu tham khảo chính cho đồ án.",
                "file": None,
                "created_at": _now(),
            },
        )
    marker.touch()


def migrate_legacy_data(user: str) -> int:
    """Chuyển dữ liệu cũ (chưa phân người dùng) vào kho của user. Trả về số file đã chuyển."""
    ensure_dirs(user)
    moved = 0
    for path in META_ROOT.glob("*.json"):
        shutil.move(str(path), str(meta_dir(user) / path.name))
        moved += 1
    (META_ROOT / ".initialized").unlink(missing_ok=True)
    for path in DATA_ROOT.iterdir():
        if path.is_file():
            shutil.move(str(path), str(data_dir(user) / path.name))
    return moved
