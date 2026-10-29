"""Giao diện đăng nhập, đăng ký, đăng xuất và ghi nhớ đăng nhập bằng cookie."""
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components

import auth
import storage
from config import ensure_dirs

SESSION_KEY = "user"
TOKEN_KEY = "session_token"
COOKIE_ACTION_KEY = "cookie_action"
COOKIE_NAME = "doc_session"


# ---------------------------------------------------------------------------
# Trạng thái đăng nhập
# ---------------------------------------------------------------------------
def _restore_from_cookie() -> Optional[str]:
    """Khôi phục đăng nhập từ cookie (khi tải lại trang, session_state đã mất)."""
    try:
        token = st.context.cookies.get(COOKIE_NAME)   # cần Streamlit >= 1.37
    except Exception:
        return None
    user = auth.get_user_from_token(token)
    if user:
        st.session_state[SESSION_KEY] = user
        st.session_state[TOKEN_KEY] = token
    return user


def current_user() -> Optional[str]:
    return st.session_state.get(SESSION_KEY) or _restore_from_cookie()


def _login(username: str, remember: bool) -> None:
    st.session_state[SESSION_KEY] = username
    if remember:
        token = auth.create_session(username)
        st.session_state[TOKEN_KEY] = token
        # Cookie được ghi ở lần chạy kế tiếp, vì st.rerun() ngay bây giờ sẽ hủy script JS
        st.session_state[COOKIE_ACTION_KEY] = ("set", token)
    st.rerun()


def _logout() -> None:
    auth.delete_session(st.session_state.pop(TOKEN_KEY, None))   # vô hiệu hóa token ở server
    st.session_state.pop(SESSION_KEY, None)
    st.session_state[COOKIE_ACTION_KEY] = ("clear", None)
    st.rerun()


def flush_cookie_actions() -> None:
    """Chạy một đoạn JS nhỏ để ghi hoặc xóa cookie trên trình duyệt (nếu có yêu cầu)."""
    action = st.session_state.pop(COOKIE_ACTION_KEY, None)
    if not action:
        return
    kind, token = action
    value, max_age = (token, auth.SESSION_DAYS * 86400) if kind == "set" else ("", 0)
    # token chỉ gồm ký tự A-Z a-z 0-9 - _ nên chèn thẳng vào chuỗi JS là an toàn
    components.html(
        f"""<script>
        const p = window.parent;
        const secure = p.location.protocol === 'https:' ? '; Secure' : '';
        p.document.cookie = "{COOKIE_NAME}={value}; max-age={max_age}; path=/; SameSite=Lax" + secure;
        </script>""",
        height=0,
    )


# ---------------------------------------------------------------------------
# Giao diện
# ---------------------------------------------------------------------------
def _render_login_tab() -> None:
    with st.form("login_form"):
        username = st.text_input("Tên đăng nhập")
        password = st.text_input("Mật khẩu", type="password")
        remember = st.checkbox(f"Ghi nhớ đăng nhập ({auth.SESSION_DAYS} ngày)", value=True)
        submitted = st.form_submit_button("Đăng nhập", use_container_width=True)
    if submitted:
        user = auth.authenticate(username, password)
        if user:
            _login(user, remember)
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
        _login(result, remember=True)


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
        _logout()
    st.sidebar.markdown("---")