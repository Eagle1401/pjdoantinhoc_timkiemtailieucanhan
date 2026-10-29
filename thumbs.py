"""Tạo ảnh xem trước: đứng -> 3:4, ngang -> 4:3. Không chứa code giao diện."""
import io
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageOps

try:
    import cv2
except ImportError:
    cv2 = None

LONG, SHORT = 320, 240      # cạnh dài / cạnh ngắn (px)
THUMB_SECOND = 1.0          # video: lấy khung hình ở giây này
CROP = True                 # True: cắt giữa cho đầy khung; False: giữ trọn hình, thêm viền đen

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".webm", ".ogv", ".mov", ".m4v"}


def kind_of(filename: str) -> Optional[str]:
    ext = Path(filename).suffix.lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"
    return None


def size_for(orientation: Optional[str]) -> Tuple[int, int]:
    """(rộng, cao) của ảnh xem trước theo hướng."""
    return (LONG, SHORT) if orientation == "landscape" else (SHORT, LONG)


def _to_thumb(img: Image.Image) -> Tuple[bytes, str]:
    img = ImageOps.exif_transpose(img).convert("RGB")   # xoay đúng theo EXIF của ảnh chụp điện thoại
    w, h = img.size
    orientation = "landscape" if w > h else "portrait"  # vuông tính là đứng
    size = size_for(orientation)
    if CROP:
        img = ImageOps.fit(img, size, Image.LANCZOS)
    else:
        img = ImageOps.pad(img, size, Image.LANCZOS, color=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return buf.getvalue(), orientation


def _open_capture(path: Path):
    cap = cv2.VideoCapture(str(path))
    if cap.isOpened():
        return cap, None
    cap.release()                                       # đường dẫn Unicode trên Windows: chép tạm sang tên ASCII
    tmp = Path(tempfile.gettempdir()) / f"thumb_{uuid.uuid4().hex}{path.suffix}"
    shutil.copyfile(path, tmp)
    return cv2.VideoCapture(str(tmp)), tmp


def _video_frame(path: Path) -> Optional[Image.Image]:
    cap, tmp = _open_capture(path)
    try:
        if not cap.isOpened():
            return None
        fps = cap.get(cv2.CAP_PROP_FPS) or 0
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        if fps > 0 and frames > fps * THUMB_SECOND:
            cap.set(cv2.CAP_PROP_POS_MSEC, THUMB_SECOND * 1000)
        ok, frame = cap.read()
        if not ok:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = cap.read()
        if not ok:
            return None
        return Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    finally:
        cap.release()
        if tmp:
            tmp.unlink(missing_ok=True)


def make_thumbnail(path: Path) -> Optional[Tuple[bytes, str]]:
    """Trả về (jpeg_bytes, 'portrait'|'landscape'), hoặc None nếu không tạo được."""
    kind = kind_of(path.name)
    try:
        if kind == "image":
            with Image.open(path) as img:
                return _to_thumb(img)
        if kind == "video" and cv2 is not None:
            frame = _video_frame(path)
            return _to_thumb(frame) if frame is not None else None
    except Exception:
        return None
    return None