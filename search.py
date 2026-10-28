"""Logic tìm kiếm và lọc, không phụ thuộc Streamlit."""
import unicodedata
from typing import List


def normalize(text: str) -> str:
    """Chữ thường + bỏ dấu tiếng Việt để tìm kiếm linh hoạt."""
    text = text.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower().strip()


def get_all_tags(docs: List[dict]) -> List[str]:
    return sorted({t for d in docs for t in d["tags"]})


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
