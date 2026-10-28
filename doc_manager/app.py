"""Điểm vào của ứng dụng. Chạy: streamlit run app.py"""
import streamlit as st

import storage
from config import ensure_dirs
from search import filter_documents, get_all_tags
from ui.document_list import render_document_list
from ui.login import current_user, render_login_page, render_user_box
from ui.sidebar import render_sidebar

st.set_page_config(
    page_title="Đồ án Quản lý & Tìm kiếm Tài liệu Cá nhân", layout="wide"
)


def main() -> None:
    user = current_user()
    if not user:                      # chưa đăng nhập -> chỉ hiện trang đăng nhập
        render_login_page()
        return

    ensure_dirs(user)
    storage.init_sample_data(user)

    docs, errors = storage.load_all_metadata(user)
    for err in errors:
        st.warning(err)

    st.title("📂 Hệ thống Quản lý & Tìm kiếm Tài liệu Cá nhân")
    st.markdown("*(Mô hình File-based Storage - Không sử dụng Database)*")
    st.markdown("---")

    render_user_box(user)
    keyword, selected_tags = render_sidebar(get_all_tags(docs), user)
    filtered = filter_documents(docs, keyword, selected_tags)
    render_document_list(
        user, filtered, total=len(docs), keyword=keyword, selected_tags=selected_tags
    )


main()
