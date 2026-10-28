"""Logic tìm kiếm, lọc và đánh dấu kết quả, không phụ thuộc Streamlit."""
import html
import unicodedata
from typing import List, Tuple


def _fold_char(c: str) -> str:
    """Bỏ dấu và chuyển thường cho một ký tự (không strip khoảng trắng)."""
    c = c.replace("đ", "d").replace("Đ", "D")
    c = unicodedata.normalize("NFD", c)
    return "".join(x for x in c if not unicodedata.combining(x)).lower()


def normalize(text: str) -> str:
    """Chữ thường + bỏ dấu tiếng Việt để tìm kiếm linh hoạt."""
    return "".join(_fold_char(c) for c in text).strip()


def get_all_tags(docs: List[dict]) -> List[str]:
    return sorted({t for d in docs for t in d["tags"]})


def is_search_active(keyword: str, selected_tags: List[str]) -> bool:
    return bool(keyword.strip() or selected_tags)


def matches(doc: dict, keyword: str, selected_tags: List[str]) -> bool:
    if selected_tags and not set(selected_tags).issubset(doc["tags"]):
        return False
    if not keyword:
        return True
    haystack = normalize(
        " ".join([doc["title"], doc["author"], doc["notes"], " ".join(doc["tags"])])
    )
    return all(word in haystack for word in normalize(keyword).split())


def filter_documents(
    docs: List[dict], keyword: str, selected_tags: List[str]
) -> List[dict]:
    return [d for d in docs if matches(d, keyword, selected_tags)]


def matched_fields(doc: dict, keyword: str, selected_tags: List[str]) -> List[str]:
    """Các trường mà từ khóa/tag đã khớp, để hiển thị 'khớp ở: ...'."""
    labels = []
    words = normalize(keyword).split()
    if words:
        for key, label in (("title", "Tiêu đề"), ("author", "Tác giả"), ("notes", "Ghi chú")):
            text = normalize(doc[key])
            if any(w in text for w in words):
                labels.append(label)
        tags_text = normalize(" ".join(doc["tags"]))
        if any(w in tags_text for w in words):
            labels.append("Tag")
    if selected_tags and "Tag" not in labels:
        labels.append("Tag")
    return labels


def highlight(text: str, keyword: str) -> str:
    """Trả về HTML đã escape, bọc <mark> quanh phần khớp (không phân biệt dấu/hoa thường)."""
    words = normalize(keyword).split()
    if not text or not words:
        return html.escape(text)

    folded, index_map = [], []          # index_map: ký tự đã chuẩn hóa -> vị trí ký tự gốc
    for i, c in enumerate(text):
        for fc in _fold_char(c):
            folded.append(fc)
            index_map.append(i)
    folded = "".join(folded)

    flags = [False] * len(text)
    for w in words:
        start = folded.find(w)
        while start != -1:
            for k in range(start, start + len(w)):
                flags[index_map[k]] = True
            start = folded.find(w, start + 1)

    parts, i = [], 0
    while i < len(text):
        j = i
        while j < len(text) and flags[j] == flags[i]:
            j += 1
        segment = html.escape(text[i:j])
        parts.append(f"<mark>{segment}</mark>" if flags[i] else segment)
        i = j
    return "".join(parts)
