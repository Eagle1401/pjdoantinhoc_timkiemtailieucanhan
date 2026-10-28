"""Giao diện sidebar: tìm kiếm, lọc và form thêm tài liệu."""
from typing import List, Tuple

import streamlit as st

import storage


def render_search(all_tags: List[str]) -> Tuple[str, List[str]]:
    st.sidebar.header("🔍 Tìm kiếm & Bộ lọc")
    keyword = st.sidebar.text_input("Từ khóa (tiêu đề, tác giả, tag, ghi chú)")
    selected_tags = st.sidebar.multiselect("Lọc theo tag", all_tags)
    return keyword, selected_tags


def render_add_form(user: str) -> None:
    st.sidebar.markdown("---")
    st.sidebar.subheader("➕ Thêm tài liệu mới")
    with st.sidebar.form("add_doc_form", clear_on_submit=True):
        title = st.text_input("Tiêu đề tài liệu *")
        author = st.text_input("Tác giả")
        tags = st.text_input("Tags (cách nhau bởi dấu phẩy)")
        uploaded = st.file_uploader("Đính kèm file (tùy chọn)")
        submitted = st.form_submit_button("Lưu tài liệu vào hệ thống")

    if not submitted:
        return
    if not title.strip():
        st.sidebar.warning("Vui lòng nhập tiêu đề tài liệu!")
        return
    storage.create_document(user, title, author, tags, uploaded)
    st.toast("Đã lưu tài liệu thành công!", icon="✅")
    st.rerun()


def render_sidebar(all_tags: List[str], user: str) -> Tuple[str, List[str]]:
    keyword, selected_tags = render_search(all_tags)
    render_add_form(user)
    return keyword, selected_tags
