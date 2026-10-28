"""Ghi nhớ đăng nhập qua cookie, token lưu trên server."""
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
STORE = Path(__file__).resolve().parent.parent / "sessions.json"   # thêm vào .gitignore


def _controller() -> CookieController:
    return CookieController(key="cookies")


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
    """Gọi ngay sau khi đăng nhập thành công."""
    token = secrets.token_urlsafe(32)
    data = {h: v for h, v in _load().items() if v["exp"] > time.time()}   # dọn token hết hạn
    data[_hash(token)] = {"user": user, "exp": time.time() + TTL_SECONDS}
    _save(data)
    _controller().set(COOKIE_NAME, token, max_age=TTL_SECONDS)


def restore_login() -> Optional[str]:
    """Trả về tên người dùng nếu cookie hợp lệ, ngược lại None."""
    token = _controller().get(COOKIE_NAME)
    if not token:
        return None
    entry = _load().get(_hash(token))
    if entry and entry["exp"] > time.time():
        return entry["user"]
    return None


def forget_login() -> None:
    """Gọi khi bấm Đăng xuất."""
    c = _controller()
    token = c.get(COOKIE_NAME)
    if token:
        data = _load()
        data.pop(_hash(token), None)
        _save(data)
        c.remove(COOKIE_NAME)