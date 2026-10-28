"""Điểm vào của ứng dụng. Chạy: streamlit run app.py"""
import streamlit as st

import storage
from config import ensure_dirs
from search import filter_documents, get_all_tags
from ui.document_list import render_document_list
from ui.sidebar import render_sidebar

st.set_page_config(
    page_title="Đồ án Quản lý & Tìm kiếm Tài liệu Cá nhân", layout="wide"
)


def main() -> None:
    ensure_dirs()
    storage.init_sample_data()

    docs, errors = storage.load_all_metadata()
    for err in errors:
        st.warning(err)

    st.title("📂 Hệ thống Quản lý & Tìm kiếm Tài liệu Cá nhân")
    st.markdown("---")

    keyword, selected_tags = render_sidebar(get_all_tags(docs))
    filtered = filter_documents(docs, keyword, selected_tags)
    render_document_list(filtered, total=len(docs))


main()
