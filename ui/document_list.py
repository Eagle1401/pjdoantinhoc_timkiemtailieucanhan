"""Giao diện danh sách tài liệu, kèm dấu hiệu nhận biết kết quả tìm thấy."""
import html
from typing import List, Optional

import streamlit as st

import storage
from search import highlight, is_search_active


# Màu nền tài liệu tìm thấy: cố định, giống nhau ở giao diện Light, Dark và System
FOUND_BG = "#99FF66"
FOUND_BORDER = "#5CCC2E"
FOUND_TEXT = "#1A1A1A"     # chữ tối để đọc rõ trên nền xanh sáng ở mọi giao diện
FOUND_CONTROL_BG = "#FFFFFF"

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


def _rule(selectors: str, **props: str) -> str:
    body = "".join(f"    {k.replace('_', '-')}: {v};\n" for k, v in props.items())
    return f"{selectors} {{\n{body}}}\n"


FOUND_CSS = (
    "<style>\n"
    # Nền cố định, !important để theme sáng/tối không ghi đè; color-scheme: light
    # khiến các điều khiển gốc của trình duyệt trong thẻ này luôn dùng kiểu sáng
    + _rule(
        _css_for(),
        background_color=f"{FOUND_BG} !important",
        border=f"1px solid {FOUND_BORDER}",
        border_radius="0.75rem",
        padding="1rem",
        color_scheme="light",
    )
    # Chữ: tiêu đề, tác giả, tag, ghi chú, nhãn ô nhập
    + _rule(
        _css_for(
            ' [data-testid="stMarkdownContainer"]',
            ' [data-testid="stMarkdownContainer"] *',
            ' [data-testid="stWidgetLabel"] *',
        ),
        color=f"{FOUND_TEXT} !important",
    )
    + _rule(
        _css_for(" code"),
        background_color="rgba(255, 255, 255, 0.6)",
        color=FOUND_TEXT,
    )
    + _rule(_css_for(" mark"), background_color="#FFD54F", color=FOUND_TEXT)
    # Nút bấm và ô ghi chú: kiểu sáng giống nhau ở mọi giao diện
    + _rule(
        _css_for(" button"),
        background_color=f"{FOUND_CONTROL_BG} !important",
        border="1px solid rgba(0, 0, 0, 0.3) !important",
        color=f"{FOUND_TEXT} !important",
    )
    + _rule(
        _css_for(" textarea", ' [data-baseweb="textarea"]', ' [data-baseweb="base-input"]'),
        background_color=f"{FOUND_CONTROL_BG} !important",
        color=f"{FOUND_TEXT} !important",
    )
    + _rule(
        _css_for(' [data-testid="stExpander"] details'),
        border_color="rgba(0, 0, 0, 0.3) !important",
    )
    + _rule(
        _css_for(' [data-testid="stExpander"] summary svg'),
        color=f"{FOUND_TEXT} !important",
        fill=f"{FOUND_TEXT} !important",
    )
    + "</style>\n"
)


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
        st.download_button(
            "⬇️ Tải file",
            data=file_path.read_bytes(),
            file_name=storage.original_filename(doc),
            key=f"dl_{doc['id']}",
        )


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
    st.markdown(FOUND_CSS, unsafe_allow_html=True)
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
