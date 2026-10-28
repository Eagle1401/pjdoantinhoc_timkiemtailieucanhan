"""Giao diện danh sách tài liệu."""
from typing import List

import streamlit as st

import storage


def _render_info(doc: dict) -> None:
    st.markdown(f"### 📄 {doc['title']}")
    st.write(f"**Tác giả:** {doc['author']} | **Nguồn:** {doc['source']}")
    if doc["tags"]:
        st.write("**Tags:** " + " ".join(f"`{t}`" for t in doc["tags"]))
    if doc["notes"]:
        st.info(f"**Ghi chú cá nhân:** {doc['notes']}")

    file_path = storage.get_file_path(doc)
    if file_path:
        st.download_button(
            "⬇️ Tải file",
            data=file_path.read_bytes(),
            file_name=storage.original_filename(doc),
            key=f"dl_{doc['id']}",
        )


def _render_actions(doc: dict) -> None:
    with st.expander("📝 Thêm/Sửa ghi chú"):
        note = st.text_area(
            "Nội dung ghi chú", doc["notes"], key=f"note_{doc['id']}"
        )
        if st.button("Lưu ghi chú", key=f"btn_{doc['id']}"):
            storage.update_notes(doc, note)
            st.toast("Đã cập nhật ghi chú!", icon="✅")
            st.rerun()

    if st.button("🗑️ Xóa tài liệu", key=f"del_{doc['id']}"):
        storage.delete_doc(doc)
        st.toast("Đã xóa tài liệu.", icon="🗑️")
        st.rerun()


def render_document(doc: dict) -> None:
    with st.container():
        col_info, col_actions = st.columns([3, 1])
        with col_info:
            _render_info(doc)
        with col_actions:
            _render_actions(doc)
        st.markdown("---")


def render_document_list(filtered: List[dict], total: int) -> None:
    st.subheader(f"📋 Kho tài liệu ({len(filtered)}/{total} tài liệu)")
    if not filtered:
        st.info("Không tìm thấy tài liệu phù hợp.")
    for doc in filtered:
        render_document(doc)
