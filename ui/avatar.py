"""Avatar tròn (chữ cái đầu) vẽ bằng Pillow, không dùng HTML/CSS."""
import colorsys
import hashlib
import io

import streamlit as st
from PIL import Image, ImageDraw, ImageFont

AVATAR_RADIUS_CM = 0.5                        # bán kính; đường kính = 1 cm
PX_PER_CM = 96 / 2.54                         # ~37,8 px/cm ở độ phân giải chuẩn của trình duyệt
AVATAR_PX = round(AVATAR_RADIUS_CM * 2 * PX_PER_CM)   # ~38 px khi hiển thị
RENDER_PX = 256                               # vẽ lớn rồi thu nhỏ để viền tròn mịn

_FONTS = ["arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"]


def _font(size: int):
    for name in _FONTS:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()           # phương án cuối nếu không có font nào


def _color(user: str) -> tuple:
    """Mỗi người một màu cố định, tính từ tên (không dùng hash() vì nó đổi theo từng lần chạy)."""
    hue = int(hashlib.md5(user.encode("utf-8")).hexdigest(), 16) % 360 / 360
    r, g, b = colorsys.hls_to_rgb(hue, 0.42, 0.60)
    return int(r * 255), int(g * 255), int(b * 255)


@st.cache_data(show_spinner=False)
def avatar_png(user: str) -> bytes:
    """PNG hình tròn nền trong suốt, có chữ cái đầu của tên người dùng."""
    img = Image.new("RGBA", (RENDER_PX, RENDER_PX), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((0, 0, RENDER_PX - 1, RENDER_PX - 1), fill=_color(user) + (255,))

    initial = (user.strip()[:1] or "?").upper()
    draw.text(
        (RENDER_PX / 2, RENDER_PX / 2),
        initial,
        font=_font(int(RENDER_PX * 0.5)),
        fill=(255, 255, 255, 255),
        anchor="mm",                          # căn giữa theo cả chiều ngang và dọc
    )

    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def render_user_avatar(user: str) -> None:
    """Avatar tròn và tên người dùng bên cạnh, đặt trong thanh bên."""
    with st.sidebar:
        try:
            col_img, col_name = st.columns([1, 4], vertical_alignment="center")
        except TypeError:                     # Streamlit cũ không có vertical_alignment
            col_img, col_name = st.columns([1, 4])
        with col_img:
            st.image(avatar_png(user), width=AVATAR_PX)
        with col_name:
            st.markdown(f"**{user}**")