"""Xác thực người dùng: tài khoản trong users/users.json, phiên đăng nhập trong users/sessions.json."""
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from pathlib import Path
from typing import Optional, Tuple

from config import SESSIONS_FILE, USERS_DIR, USERS_FILE

# Tên đăng nhập dùng làm tên thư mục nên chỉ cho phép ký tự an toàn
USERNAME_RE = re.compile(r"^[a-z0-9_]{3,30}$")
MIN_PASSWORD_LEN = 6
ITERATIONS = 200_000
SESSION_DAYS = 7


# ---------------------------------------------------------------------------
# Đọc/ghi JSON
# ---------------------------------------------------------------------------
def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _write_json(path: Path, data: dict) -> None:
    USERS_DIR.mkdir(exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    tmp.replace(path)


def _load_users() -> dict:
    return _read_json(USERS_FILE)


def _save_users(users: dict) -> None:
    _write_json(USERS_FILE, users)


# ---------------------------------------------------------------------------
# Tài khoản
# ---------------------------------------------------------------------------
def normalize_username(username: str) -> str:
    return username.strip().lower()


def _hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)


def has_users() -> bool:
    return bool(_load_users())


def register(username: str, password: str, confirm: str) -> Tuple[bool, str]:
    username = normalize_username(username)
    if not USERNAME_RE.match(username):
        return False, "Tên đăng nhập gồm 3-30 ký tự: chữ thường, số hoặc dấu gạch dưới."
    if len(password) < MIN_PASSWORD_LEN:
        return False, f"Mật khẩu phải có ít nhất {MIN_PASSWORD_LEN} ký tự."
    if password != confirm:
        return False, "Mật khẩu nhập lại không khớp."

    users = _load_users()
    if username in users:
        return False, "Tên đăng nhập đã tồn tại."

    salt = os.urandom(16)
    users[username] = {
        "salt": salt.hex(),
        "password_hash": _hash_password(password, salt).hex(),
    }
    _save_users(users)
    return True, username


def authenticate(username: str, password: str) -> Optional[str]:
    """Trả về username nếu đúng, ngược lại None."""
    username = normalize_username(username)
    user = _load_users().get(username)

    # Luôn băm một lần dù user không tồn tại để thời gian phản hồi gần như nhau
    salt = bytes.fromhex(user["salt"]) if user else b"\x00" * 16
    candidate = _hash_password(password, salt)
    expected = bytes.fromhex(user["password_hash"]) if user else b"\x00" * 32

    if user and hmac.compare_digest(candidate, expected):
        return username
    return None


# ---------------------------------------------------------------------------
# Phiên đăng nhập ghi nhớ (cookie)
# ---------------------------------------------------------------------------
def _hash_token(token: str) -> str:
    """Chỉ lưu bản băm của token: lộ file sessions.json cũng không dùng được token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _prune_expired(sessions: dict) -> dict:
    now = time.time()
    return {k: v for k, v in sessions.items() if v.get("expires", 0) > now}


def create_session(username: str, days: int = SESSION_DAYS) -> str:
    """Tạo token ngẫu nhiên cho trình duyệt; trả về token gốc (chỉ gửi cho cookie)."""
    sessions = _prune_expired(_read_json(SESSIONS_FILE))
    token = secrets.token_urlsafe(32)
    sessions[_hash_token(token)] = {
        "username": username,
        "expires": time.time() + days * 86400,
    }
    _write_json(SESSIONS_FILE, sessions)
    return token


def get_user_from_token(token: Optional[str]) -> Optional[str]:
    """Trả về username nếu token hợp lệ, chưa hết hạn và tài khoản còn tồn tại."""
    if not token:
        return None
    info = _read_json(SESSIONS_FILE).get(_hash_token(token))
    if not info or info.get("expires", 0) <= time.time():
        return None
    username = info.get("username")
    return username if username in _load_users() else None


def delete_session(token: Optional[str]) -> None:
    if not token:
        return
    sessions = _read_json(SESSIONS_FILE)
    if sessions.pop(_hash_token(token), None) is not None:
        _write_json(SESSIONS_FILE, sessions)