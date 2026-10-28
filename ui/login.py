"""Giao diện đăng nhập, đăng ký và đăng xuất."""
from typing import Optional
from ui.session import forget_login, remember_login, restore_login
import streamlit as st
import time
import auth
import storage
from config import ensure_dirs

SESSION_KEY = "user"


def current_user() -> Optional[str]:
    user = st.session_state.get(SESSION_KEY)
    if user:
        return user
    user = restore_login()                 # tải lại trang: thử đọc từ cookie
    if user:
        st.session_state[SESSION_KEY] = user
    return user


def _login(username: str) -> None:
    st.session_state[SESSION_KEY] = username
    remember_login(username)
    time.sleep(0.5)                        # cho cookie kịp ghi xuống trình duyệt
    st.rerun()

def _render_login_tab() -> None:
    with st.form("login_form"):
        username = st.text_input("Tên đăng nhập")
        password = st.text_input("Mật khẩu", type="password")
        submitted = st.form_submit_button("Đăng nhập", use_container_width=True)
    if submitted:
        user = auth.authenticate(username, password)
        if user:
            _login(user)
        else:
            st.error("Sai tên đăng nhập hoặc mật khẩu.")


def _render_register_tab() -> None:
    with st.form("register_form"):
        username = st.text_input("Tên đăng nhập mới")
        password = st.text_input("Mật khẩu", type="password")
        confirm = st.text_input("Nhập lại mật khẩu", type="password")
        submitted = st.form_submit_button("Tạo tài khoản", use_container_width=True)
    if submitted:
        is_first_user = not auth.has_users()
        ok, result = auth.register(username, password, confirm)
        if not ok:
            st.error(result)
            return
        ensure_dirs(result)
        if is_first_user:
            # Tài khoản đầu tiên nhận lại dữ liệu cũ chưa thuộc về ai
            storage.migrate_legacy_data(result)
        _login(result)


def render_login_page() -> None:
    _, center, _ = st.columns([1, 2, 1])
    with center:
        st.title("🔐 Quản lý Tài liệu Cá nhân")
        st.caption("Đăng nhập để truy cập kho tài liệu riêng của bạn.")
        tab_login, tab_register = st.tabs(["Đăng nhập", "Đăng ký"])
        with tab_login:
            _render_login_tab()
        with tab_register:
            _render_register_tab()


def render_user_box(user: str) -> None:
    st.sidebar.markdown(f"👤 Xin chào, **{user}**")
    if st.sidebar.button("Đăng xuất", use_container_width=True):
        forget_login()                     # xóa token trên server và cookie
        st.session_state.pop(SESSION_KEY, None)
        st.rerun()
    st.sidebar.markdown("---")
