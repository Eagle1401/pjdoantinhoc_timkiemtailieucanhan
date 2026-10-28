"""Giao diện danh sách tài liệu, kèm dấu hiệu nhận biết kết quả tìm thấy."""
import html
from typing import List, Optional

import streamlit as st

import storage
from search import highlight, is_search_active, matched_fields


def _tag_html(tag: str, keyword: str, selected_tags: List[str]) -> str:
    if tag in selected_tags:                       # tag được chọn ở bộ lọc: tô cả tag
        inner = f"<mark>{html.escape(tag)}</mark>"
    else:                                          # tag khớp từ khóa: tô phần khớp
        inner = highlight(tag, keyword)
    return f"<code>{inner}</code>"


def _render_info(user: str, doc: dict, keyword: str, selected_tags: List[str]) -> None:
    if is_search_active(keyword, selected_tags):
        fields = matched_fields(doc, keyword, selected_tags)
        if fields:
            st.markdown(f":green[✅ **Đã tìm thấy** — khớp ở: {', '.join(fields)}]")

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
    with st.container():
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
