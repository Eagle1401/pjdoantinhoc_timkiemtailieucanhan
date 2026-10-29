"""Ghi nhớ đăng nhập qua cookie; token lưu trên server."""
import hashlib
import json
import secrets
import time
from pathlib import Path
from typing import Optional

import streamlit as st
from streamlit_cookies_controller import CookieController

COOKIE_NAME = "doc_manager_token"
TTL_SECONDS = 30 * 24 * 3600                       # nhớ đăng nhập 30 ngày
STORE = Path(__file__).resolve().parent.parent / "sessions.json"

_SET = "_cookie_to_set"        # token cần ghi xuống cookie ở lượt chạy kế tiếp
_CLEAR = "_cookie_to_clear"    # cờ xóa cookie ở lượt chạy kế tiếp
_TOKEN = "_cookie_token"       # token của phiên hiện tại (để xóa khi đăng xuất)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _load() -> dict:
    try:
        return json.loads(STORE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save(data: dict) -> None:
    tmp = STORE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    tmp.replace(STORE)


def remember_login(user: str) -> None:
    """Gọi ngay sau khi đăng nhập. Chỉ tạo token và đặt cờ; cookie được ghi ở lượt chạy sau."""
    token = secrets.token_urlsafe(32)
    data = {h: v for h, v in _load().items() if v["exp"] > time.time()}
    data[_hash(token)] = {"user": user, "exp": time.time() + TTL_SECONDS}
    _save(data)
    st.session_state[_SET] = token
    st.session_state[_TOKEN] = token


def forget_login() -> None:
    """Gọi khi bấm Đăng xuất: xóa token ở server, đặt cờ xóa cookie."""
    token = st.session_state.pop(_TOKEN, None)
    if token:
        data = _load()
        data.pop(_hash(token), None)
        _save(data)
    st.session_state[_CLEAR] = True


def resolve_user(session_key: str) -> Optional[str]:
    """Gọi đúng MỘT lần mỗi lượt chạy (trong current_user). Trả về tên người dùng hoặc None."""
    c = CookieController(key="cookies")            # chỉ tạo một lần mỗi lượt

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
    if not token:
        return None
    entry = _load().get(_hash(token))
    if entry and entry["exp"] > time.time():
        st.session_state[session_key] = entry["user"]
        st.session_state[_TOKEN] = token
        return entry["user"]
    return None