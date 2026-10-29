"""Điểm vào của ứng dụng. Chạy: streamlit run app.py"""
import streamlit as st

import storage
from config import ensure_dirs
from search import filter_documents, get_all_tags
from ui.document_list import render_document_list
from ui.login import (
    current_user,
    flush_cookie_actions,
    render_login_page,
    render_user_box,
)
from ui.sidebar import render_sidebar

st.set_page_config(
    page_title="Đồ án Quản lý & Tìm kiếm Tài liệu Cá nhân", layout="wide"
)


def main() -> None:
    debug_panel()   
    flush_cookie_actions()            # ghi/xóa cookie đăng nhập nếu có yêu cầu từ lần chạy trước
    user = current_user()             # lấy từ session hoặc khôi phục từ cookie
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

def debug_panel() -> None:
    """TẠM THỜI: dùng để tìm lý do không nhớ đăng nhập. Xóa sau khi kiểm tra xong."""
    from config import SESSIONS_FILE
    import json

    with st.sidebar.expander("🛠 Debug đăng nhập", expanded=True):
        st.write("Phiên bản Streamlit:", st.__version__)
        try:
            cookies = dict(st.context.cookies)
            st.write("Các cookie server nhận được:", list(cookies.keys()))
            st.write("Có cookie doc_session:", "doc_session" in cookies)
            import auth 
            st.write("Token hợp lệ cho user:", auth.get_user_from_token(cookies.get("doc_session")))
        except Exception as e:
            st.write("Không đọc được cookie:", repr(e))
        try:
            n = len(json.loads(SESSIONS_FILE.read_text())) if SESSIONS_FILE.exists() else 0
        except Exception:
            n = -1
        st.write("Số phiên lưu trong sessions.json:", n)

main()