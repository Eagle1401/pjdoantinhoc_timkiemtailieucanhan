"""Avatar tròn: ảnh người dùng tải lên, hoặc chữ cái đầu nếu chưa có. Thuần Python (Pillow)."""
import colorsys
import hashlib
import io
from pathlib import Path
from typing import Optional

import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps

from config import data_dir

AVATAR_RADIUS_CM = 0.5                        # bán kính; đường kính = 1 cm
PX_PER_CM = 96 / 2.54                         # ~37,8 px/cm ở độ phân giải chuẩn của trình duyệt
AVATAR_PX = round(AVATAR_RADIUS_CM * 2 * PX_PER_CM)   # ~38 px khi hiển thị
RENDER_PX = 256                               # kích thước ảnh lưu/vẽ, thu nhỏ khi hiển thị
MAX_UPLOAD_MB = 5

_FONTS = ["arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"]


# ---------------------------------------------------------------------------
# Lưu trữ ảnh đại diện
# ---------------------------------------------------------------------------
def avatar_path(user: str) -> Path:
    """Ảnh đại diện nằm trong thư mục dữ liệu của người dùng, không lẫn vào danh sách tài liệu."""
    return data_dir(user) / "_avatar.png"


def _circle_crop(img: Image.Image) -> Image.Image:
    """Cắt vuông ở giữa, thu về RENDER_PX rồi cắt tròn (nền ngoài hình tròn trong suốt)."""
    img = ImageOps.exif_transpose(img).convert("RGBA")
    img = ImageOps.fit(img, (RENDER_PX, RENDER_PX), Image.LANCZOS)
    big = RENDER_PX * 4                       # vẽ mặt nạ lớn rồi thu nhỏ để viền mịn
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, big - 1, big - 1), fill=255)
    img.putalpha(mask.resize((RENDER_PX, RENDER_PX), Image.LANCZOS))
    return img


def save_avatar(user: str, uploaded_file) -> None:
    with Image.open(uploaded_file) as img:
        out = _circle_crop(img)
    out.save(avatar_path(user), "PNG")


def delete_avatar(user: str) -> None:
    avatar_path(user).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Avatar mặc định (chữ cái đầu)
# ---------------------------------------------------------------------------
def _font(size: int):
    for name in _FONTS:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _color(user: str) -> tuple:
    hue = int(hashlib.md5(user.encode("utf-8")).hexdigest(), 16) % 360 / 360
    r, g, b = colorsys.hls_to_rgb(hue, 0.42, 0.60)
    return int(r * 255), int(g * 255), int(b * 255)


@st.cache_data(show_spinner=False)
def _initial_png(user: str) -> bytes:
    img = Image.new("RGBA", (RENDER_PX, RENDER_PX), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((0, 0, RENDER_PX - 1, RENDER_PX - 1), fill=_color(user) + (255,))
    draw.text(
        (RENDER_PX / 2, RENDER_PX / 2),
        (user.strip()[:1] or "?").upper(),
        font=_font(int(RENDER_PX * 0.5)),
        fill=(255, 255, 255, 255),
        anchor="mm",
    )
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def avatar_image(user: str) -> bytes:
    """Ảnh người dùng tải lên nếu có, ngược lại là avatar chữ cái đầu."""
    path = avatar_path(user)
    if path.exists():
        return path.read_bytes()              # chỉ ~256x256 nên nhẹ, không cần cache
    return _initial_png(user)


# ---------------------------------------------------------------------------
# Giao diện
# ---------------------------------------------------------------------------
def _render_change_form(user: str) -> None:
    with st.sidebar.expander("🖼️ Đổi ảnh đại diện"):
        with st.form("avatar_form", clear_on_submit=True):
            file = st.file_uploader("Chọn ảnh", type=["png", "jpg", "jpeg", "webp"])
            submitted = st.form_submit_button("Lưu ảnh đại diện", use_container_width=True)
        if submitted:
            if file is None:
                st.warning("Bạn chưa chọn ảnh.")
            elif file.size > MAX_UPLOAD_MB * 1024 * 1024:
                st.error(f"Ảnh vượt quá {MAX_UPLOAD_MB} MB.")
            else:
                try:
                    save_avatar(user, file)
                except Exception as e:
                    st.error(f"Không đọc được ảnh: {type(e).__name__}")
                else:
                    st.toast("Đã cập nhật ảnh đại diện!", icon="✅")
                    st.rerun()
        if avatar_path(user).exists() and st.button("Xóa ảnh, dùng chữ cái đầu", key="avatar_del"):
            delete_avatar(user)
            st.toast("Đã xóa ảnh đại diện.", icon="🗑️")
            st.rerun()


def render_user_avatar(user: str) -> None:
    """Avatar tròn kèm tên người dùng bên cạnh, và mục đổi ảnh đại diện."""
    with st.sidebar:
        try:
            col_img, col_name = st.columns([1, 4], vertical_alignment="center")
        except TypeError:                     # Streamlit cũ không có vertical_alignment
            col_img, col_name = st.columns([1, 4])
        with col_img:
            st.image(avatar_image(user), width=AVATAR_PX)
        with col_name:
            st.markdown(f"**{user}**")
    _render_change_form(user)