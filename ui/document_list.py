"""Giao diện danh sách tài liệu, kèm dấu hiệu nhận biết kết quả tìm thấy."""
import html
from pathlib import Path
from typing import List, Optional

import streamlit as st

import storage
import thumbs
from search import highlight, is_search_active


# Nền xanh lá #99FF66 trong suốt: hòa vào giao diện Light, Dark hay System
FOUND_RGB = "153, 255, 102"      # = #99FF66
FOUND_ALPHA = 0.30               # độ đậm của nền (0 = trong suốt hoàn toàn, 1 = đặc)
FOUND_BORDER_ALPHA = 0.90

# Bộ chọn CSS: bản Streamlit mới (key) và bản cũ (thẻ đánh dấu + :has)
_FOUND_SELECTORS = [
    '[class*="st-key-docfound"]',
    '[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .doc-found-marker)',
    '[data-testid="stVerticalBlock"]:has(> .element-container .doc-found-marker)',
]


def _css_for(*suffixes: str) -> str:
    """Ghép mọi bộ chọn với mọi hậu tố, ngăn cách bằng dấu phẩy."""
    suffixes = suffixes or ("",)
    return ",\n".join(f"{sel}{suf}" for sel in _FOUND_SELECTORS for suf in suffixes)


FOUND_CSS = (
    "<style>\n"
    + _css_for() + " {\n"
    f"    background-color: rgba({FOUND_RGB}, {FOUND_ALPHA}) !important;\n"
    f"    border: 1px solid rgba({FOUND_RGB}, {FOUND_BORDER_ALPHA});\n"
    "    border-radius: 0.75rem;\n"
    "    padding: 1rem;\n"
    "}\n"
    # Phần từ khóa được tô: nền vàng cam, chữ tối để rõ ở cả giao diện sáng và tối
    + _css_for(" mark") + " {\n"
    "    background-color: #FFD54F;\n"
    "    color: #1A1A1A;\n"
    "}\n"
    "</style>\n"
)

# Không ép tỉ lệ bằng CSS: kích thước 3:4 / 4:3 đã được cố định trong ảnh xem trước
PREVIEW_CSS = """<style>
video { max-width: 520px; border-radius: 0.5rem; }
[data-testid="stImage"] img { border-radius: 0.5rem; }
</style>"""

PREPARED_KEY = "prepared_download"   # id tài liệu đang được chuẩn bị tải


def _doc_container(doc: dict, found: bool):
    """Container của một tài liệu; nếu 'found' thì có nền xanh lá."""
    if not found:
        return st.container()
    try:
        # Streamlit mới: key tạo ra class CSS 'st-key-<key>' để gắn style ổn định
        return st.container(key=f"docfound-{doc['id']}")
    except TypeError:
        # Streamlit cũ không có tham số key: dùng thẻ đánh dấu + CSS :has()
        container = st.container()
        container.markdown('<span class="doc-found-marker"></span>', unsafe_allow_html=True)
        return container


def _tag_html(tag: str, keyword: str, selected_tags: List[str]) -> str:
    if tag in selected_tags:                       # tag được chọn ở bộ lọc: tô cả tag
        inner = f"<mark>{html.escape(tag)}</mark>"
    else:                                          # tag khớp từ khóa: tô phần khớp
        inner = highlight(tag, keyword)
    return f"<code>{inner}</code>"


def _human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def _toggle_button(label_on: str, label_off: str, state_key: str, btn_key: str) -> bool:
    """Nút bật/tắt lưu trong session_state; trả về trạng thái hiện tại."""
    on = st.session_state.get(state_key, False)
    if st.button(label_off if on else label_on, key=btn_key):
        st.session_state[state_key] = not on
        st.rerun()
    return on


def _render_preview(user: str, file_path: Path, doc: dict) -> None:
    """Ảnh: ảnh xem trước 3:4/4:3, bấm để xem ảnh lớn. Video: ảnh bìa giây đầu, bấm để phát."""
    kind = thumbs.kind_of(storage.original_filename(doc))
    if kind is None:
        return
    try:
        thumb = storage.ensure_thumbnail(user, doc)    # tài liệu cũ chưa có thì tạo một lần
        width = thumbs.size_for(doc.get("orientation"))[0]
        doc_id = doc["id"]

        if kind == "image":
            if _toggle_button("🔍 Xem ảnh lớn", "✖️ Thu nhỏ", f"big_{doc_id}", f"bigbtn_{doc_id}"):
                st.image(str(file_path), caption=doc["title"])
            elif thumb:
                st.image(str(thumb), caption=doc["title"], width=width)
            else:
                st.image(str(file_path), caption=doc["title"], width=width)
            return

        # Video
        if st.session_state.get(f"play_{doc_id}"):
            st.video(str(file_path))
            if st.button("⏹️ Đóng video", key=f"stop_{doc_id}"):
                st.session_state[f"play_{doc_id}"] = False
                st.rerun()
        elif thumb:
            st.image(str(thumb), caption=doc["title"], width=width)
            if st.button("▶️ Phát video", key=f"play_btn_{doc_id}"):
                st.session_state[f"play_{doc_id}"] = True
                st.rerun()
        else:
            st.video(str(file_path))                   # không tạo được ảnh bìa: dùng trình phát luôn
    except Exception as e:
        st.caption(f"⚠️ Không thể xem trước file này ({type(e).__name__}: {e})")


def _render_download(file_path: Path, doc: dict) -> None:
    """Chỉ đọc file vào RAM khi người dùng bấm chuẩn bị tải."""
    doc_id = doc["id"]
    if st.session_state.get(PREPARED_KEY) == doc_id:
        st.download_button(
            "✅ Bấm để lưu file",
            data=file_path.read_bytes(),               # chỉ đọc cho đúng tài liệu này
            file_name=storage.original_filename(doc),
            key=f"dl_{doc_id}",
        )
    else:
        size = _human_size(file_path.stat().st_size)   # stat() không đọc nội dung file
        if st.button(f"⬇️ Tải file ({size})", key=f"prep_{doc_id}"):
            st.session_state[PREPARED_KEY] = doc_id
            st.rerun()


def _render_info(user: str, doc: dict, keyword: str, selected_tags: List[str]) -> None:
    st.markdown(f"### 📄 {highlight(doc['title'], keyword)}", unsafe_allow_html=True)
    st.markdown(
        f"**Tác giả:** {highlight(doc['author'], keyword)} | "
        f"**Nguồn:** {html.escape(doc['source'])}",
        unsafe_allow_html=True,
    )
    if doc["tags"]:
        tags_html = " ".join(_tag_html(t, keyword, selected_tags) for t in doc["tags"])
        st.markdown(f"**Tags:** {tags_html}", unsafe_allow_html=True)
    if doc["notes"]:
        notes_html = highlight(doc["notes"], keyword).replace("\n", "<br>")
        st.markdown(f"> 📝 **Ghi chú cá nhân:** {notes_html}", unsafe_allow_html=True)

    file_path = storage.get_file_path(user, doc)
    if file_path:
        _render_preview(user, file_path, doc)
        _render_download(file_path, doc)


def _render_actions(user: str, doc: dict) -> None:
    with st.expander("📝 Thêm/Sửa ghi chú"):
        note = st.text_area(
            "Nội dung ghi chú", doc["notes"], key=f"note_{doc['id']}"
        )
        if st.button("Lưu ghi chú", key=f"btn_{doc['id']}"):
            storage.update_notes(user, doc, note)
            st.toast("Đã cập nhật ghi chú!", icon="✅")
            st.rerun()

    if st.button("🗑️ Xóa tài liệu", key=f"del_{doc['id']}"):
        storage.delete_doc(user, doc)
        st.toast("Đã xóa tài liệu.", icon="🗑️")
        st.rerun()


def render_document(
    user: str, doc: dict, keyword: str = "", selected_tags: Optional[List[str]] = None
) -> None:
    with _doc_container(doc, is_search_active(keyword, selected_tags)):
        col_info, col_actions = st.columns([3, 1])
        with col_info:
            _render_info(user, doc, keyword, selected_tags or [])
        with col_actions:
            _render_actions(user, doc)
        st.markdown("---")


def render_document_list(
    user: str,
    filtered: List[dict],
    total: int,
    keyword: str = "",
    selected_tags: Optional[List[str]] = None,
) -> None:
    selected_tags = selected_tags or []
    st.markdown(FOUND_CSS + PREVIEW_CSS, unsafe_allow_html=True)
    st.subheader(f"📋 Kho tài liệu ({len(filtered)}/{total} tài liệu)")

    if is_search_active(keyword, selected_tags):
        criteria = []
        if keyword.strip():
            criteria.append(f"từ khóa “{keyword.strip().replace('`', '')}”")
        if selected_tags:
            criteria.append("tag " + ", ".join(selected_tags))
        if filtered:
            st.success(f"✅ Đã tìm thấy {len(filtered)} tài liệu phù hợp với " + " và ".join(criteria))
        else:
            st.warning("❌ Không tìm thấy tài liệu nào phù hợp với " + " và ".join(criteria))
    elif not filtered:
        st.info("Kho tài liệu đang trống. Hãy thêm tài liệu ở thanh bên.")

    for doc in filtered:
        render_document(user, doc, keyword, selected_tags)