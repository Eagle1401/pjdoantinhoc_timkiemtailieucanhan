"""Giao diện sidebar: tìm kiếm, lọc và form thêm tài liệu."""
import streamlit as st

from pathlib import Path

from typing import List, Tuple

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
        uploaded_files = st.file_uploader(
            "Đính kèm file (tùy chọn, có thể chọn nhiều file)",
            accept_multiple_files=True,
        )
        submitted = st.form_submit_button("Lưu tài liệu vào hệ thống")
    if not submitted:
        return

    # Không có file: tạo một tài liệu chỉ có thông tin (như trước)
    if not uploaded_files:
        if not title.strip():
            st.sidebar.warning("Vui lòng nhập tiêu đề tài liệu!")
            return
        try:
            storage.create_document(user, title, author, tags, None)
        except Exception as e:
            st.sidebar.error(f"Không lưu được tài liệu: {e}")
            return
        st.toast("Đã lưu tài liệu thành công!", icon="✅")
        st.rerun()

    # Có file: mỗi file thành một tài liệu
    ok, failed = 0, []
    progress = st.sidebar.progress(0.0)
    for i, f in enumerate(uploaded_files, start=1):
        if len(uploaded_files) > 1 and title.strip():
            st.sidebar.info("Chọn nhiều file: mỗi tài liệu lấy tên file làm tiêu đề, ô Tiêu đề được bỏ qua.")     # 1 file + có nhập tiêu đề: dùng tiêu đề đó
        else:
            doc_title = Path(f.name).stem      # còn lại: lấy theo tên file
        try:
            storage.create_document(user, doc_title, author, tags, f)
            ok += 1
        except Exception as e:                 # một file lỗi không làm hỏng cả lô
            failed.append(f"{f.name}: {e}")
        progress.progress(i / len(uploaded_files))
    progress.empty()

    if failed:
        for msg in failed:
            st.sidebar.error(msg)
        if ok:
            st.toast(f"Đã lưu {ok}/{len(uploaded_files)} tài liệu.", icon="⚠️")
        return                                 # không rerun để còn đọc được thông báo lỗi
    st.toast(f"Đã lưu {ok} tài liệu thành công!", icon="✅")
    st.rerun()


def render_sidebar(all_tags: List[str], user: str) -> Tuple[str, List[str]]:
    keyword, selected_tags = render_search(all_tags)
    render_add_form(user)
    return keyword, selected_tags
