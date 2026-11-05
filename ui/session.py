"""Ghi nhớ đăng nhập qua cookie; token do auth.py quản lý (users/sessions.json)."""
from typing import Optional

import streamlit as st
from streamlit_cookies_controller import CookieController

import auth

COOKIE_NAME = "doc_manager_token"
TTL_SECONDS = auth.SESSION_DAYS * 86400

_SET = "_cookie_to_set"        # token cần ghi xuống cookie ở lượt chạy kế tiếp
_CLEAR = "_cookie_to_clear"    # cờ xóa cookie ở lượt chạy kế tiếp
_TOKEN = "_cookie_token"       # token của phiên hiện tại (để xóa khi đăng xuất)


def remember_login(user: str) -> None:
    """Gọi ngay sau khi đăng nhập: tạo token và đặt cờ; cookie ghi ở lượt chạy sau."""
    token = auth.create_session(user)
    st.session_state[_SET] = token
    st.session_state[_TOKEN] = token


def forget_login() -> None:
    """Gọi khi bấm Đăng xuất: xóa token ở server, đặt cờ xóa cookie."""
    auth.delete_session(st.session_state.pop(_TOKEN, None))
    st.session_state[_CLEAR] = True


def resolve_user(session_key: str) -> Optional[str]:
    """Gọi đúng MỘT lần mỗi lượt chạy (trong current_user)."""
    c = CookieController(key="cookies")

    if st.session_state.pop(_CLEAR, False):        # vừa đăng xuất
        try:
            c.remove(COOKIE_NAME)
        except Exception:
            pass
        return None

    to_set = st.session_state.pop(_SET, None)      # vừa đăng nhập
    if to_set:
        c.set(COOKIE_NAME, to_set, max_age=TTL_SECONDS)

    user = st.session_state.get(session_key)
    if user:
        return user

    token = c.get(COOKIE_NAME)                     # tải lại trang: đọc cookie
    user = auth.get_user_from_token(token)
    if user:
        st.session_state[session_key] = user
        st.session_state[_TOKEN] = token
    return user