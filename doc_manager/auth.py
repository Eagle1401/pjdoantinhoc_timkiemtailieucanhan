"""Xác thực người dùng: lưu tài khoản trong users/users.json, mật khẩu được băm."""
import hashlib
import hmac
import json
import os
import re
from typing import Optional, Tuple

from config import USERS_DIR, USERS_FILE

# Tên đăng nhập dùng làm tên thư mục nên chỉ cho phép ký tự an toàn
USERNAME_RE = re.compile(r"^[a-z0-9_]{3,30}$")
MIN_PASSWORD_LEN = 6
ITERATIONS = 200_000


def normalize_username(username: str) -> str:
    return username.strip().lower()


def _hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)


def _load_users() -> dict:
    if not USERS_FILE.exists():
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_users(users: dict) -> None:
    USERS_DIR.mkdir(exist_ok=True)
    tmp = USERS_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=4)
    tmp.replace(USERS_FILE)


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
