"""Giao diện danh sách tài liệu, kèm dấu hiệu nhận biết kết quả tìm thấy."""
import shutil
import tempfile
import uuid
import html
from typing import List, Optional
try:
    import cv2
except ImportError:
    cv2 = None
import streamlit as st

import storage
from search import highlight, is_search_active
from pathlib import Path

# Nền xanh lá #99FF66 trong suốt: hòa vào giao diện Light, Dark hay System
FOUND_RGB = "153, 255, 102"      # = #99FF66
FOUND_ALPHA = 0.30               # độ đậm của nền (0 = trong suốt hoàn toàn, 1 = đặc)
FOUND_BORDER_ALPHA = 0.90

# Bộ chọn CSS: bản Streamlit mới (key) và bản cũ (thẻ đánh dấu + :has)
_FOUND_SELECTORS = [
    '[class*="st-key-docfound"]',
    '[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .doc-found-marker)',
    '[data-testid="stVerticalBlock"]:has(> .element-container .doc-found-marker)',
]


def _css_for(*suffixes: str) -> str:
    """Ghép mọi bộ chọn với mọi hậu tố, ngăn cách bằng dấu phẩy."""
    suffixes = suffixes or ("",)
    return ",\n".join(f"{sel}{suf}" for sel in _FOUND_SELECTORS for suf in suffixes)


FOUND_CSS = (
    "<style>\n"
    + _css_for() + " {\n"
    f"    background-color: rgba({FOUND_RGB}, {FOUND_ALPHA}) !important;\n"
    f"    border: 1px solid rgba({FOUND_RGB}, {FOUND_BORDER_ALPHA});\n"
    "    border-radius: 0.75rem;\n"
    "    padding: 1rem;\n"
    "}\n"
    # Phần từ khóa được tô: nền vàng cam, chữ tối để rõ ở cả giao diện sáng và tối
    + _css_for(" mark") + " {\n"
    "    background-color: #FFD54F;\n"
    "    color: #1A1A1A;\n"
    "}\n"
    "</style>\n"
)
# Khung xem trước ảnh/video theo tỉ lệ 3:4 (rộng:cao)
PREVIEW_WIDTH = 300   # px, chỉnh số này để to/nhỏ hơn

PREVIEW_CSS = f"""<style>
[data-testid="stImage"] img,
video {{
    width: {PREVIEW_WIDTH}px;
    max-width: 100%;
    aspect-ratio: 3 / 4;
    object-fit: contain;      /* giữ nguyên hình, thừa thì để nền đen; đổi thành cover nếu muốn cắt lấp đầy khung */
    background: #000;
    border-radius: 0.5rem;
}}
</style>"""


def _doc_container(doc: dict, found: bool):
    """Container của một tài liệu; nếu 'found' thì có nền xanh lá."""
    if not found:
        return st.container()
    try:
        # Streamlit mới: key tạo ra class CSS 'st-key-<key>' để gắn style ổn định
        return st.container(key=f"docfound-{doc['id']}")
    except TypeError:
        # Streamlit cũ không có tham số key: dùng thẻ đánh dấu + CSS :has()
        container = st.container()
        container.markdown('<span class="doc-found-marker"></span>', unsafe_allow_html=True)
        return container


def _tag_html(tag: str, keyword: str, selected_tags: List[str]) -> str:
    if tag in selected_tags:                       # tag được chọn ở bộ lọc: tô cả tag
        inner = f"<mark>{html.escape(tag)}</mark>"
    else:                                          # tag khớp từ khóa: tô phần khớp
        inner = highlight(tag, keyword)
    return f"<code>{inner}</code>"

# Định dạng được xem trước trực tiếp trong thẻ tài liệu
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".webm", ".ogv", ".mov", ".m4v"}


def _media_kind(file_path, doc: dict) -> Optional[str]:
    """Trả về 'image', 'video' hoặc None, dựa vào đuôi file (lưu trữ hoặc tên gốc)."""
    exts = {
        file_path.suffix.lower(),
        Path(storage.original_filename(doc)).suffix.lower(),
    }
    if exts & IMAGE_EXTS:
        return "image"
    if exts & VIDEO_EXTS:
        return "video"
    return None


THUMB_SECOND = 1.0   # lấy khung hình ở giây thứ mấy làm ảnh xem trước


@st.cache_data(show_spinner=False)
def _open_capture(path_str: str):
    """Mở video; nếu cv2 không đọc được đường dẫn Unicode thì chép tạm sang tên ASCII."""
    cap = cv2.VideoCapture(path_str)
    if cap.isOpened():
        return cap, None
    cap.release()
    tmp = Path(tempfile.gettempdir()) / f"thumb_{uuid.uuid4().hex}{Path(path_str).suffix}"
    shutil.copyfile(path_str, tmp)
    return cv2.VideoCapture(str(tmp)), tmp


@st.cache_data(show_spinner=False)
def _video_thumbnail(path_str: str, mtime: float) -> Optional[bytes]:
    if cv2 is None:
        return None
    cap, tmp = _open_capture(path_str)
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
        ok, buf = cv2.imencode(".jpg", frame)
        return buf.tobytes() if ok else None
    finally:
        cap.release()
        if tmp:
            tmp.unlink(missing_ok=True)


def _render_video_preview(file_path: Path, doc: dict) -> None:
    doc_id = doc["id"]
    play_key = f"play_{doc_id}"

    if st.session_state.get(play_key):                    # đang phát
        st.video(str(file_path))
        if st.button("⏹️ Đóng video", key=f"stop_{doc_id}"):
            st.session_state[play_key] = False
            st.rerun()
        return

    thumb = _video_thumbnail(str(file_path), file_path.stat().st_mtime)
    if thumb is None:                                     # không cắt được: dùng trình phát luôn
        st.video(str(file_path))
        return
    st.image(thumb, caption=doc["title"])
    if st.button("▶️ Phát video", key=f"play_btn_{doc_id}"):
        st.session_state[play_key] = True
        st.rerun()


def _render_preview(file_path, doc: dict) -> None:
    """Ảnh: st.image. Video: ảnh bìa từ giây đầu, bấm để phát."""
    kind = _media_kind(file_path, doc)
    if kind is None:
        return
    try:
        if kind == "image":
            st.image(str(file_path), caption=doc["title"], width=PREVIEW_WIDTH)
        else:
            _render_video_preview(file_path, doc)
    except Exception:
        st.caption("⚠️ Không thể xem trước file này, hãy tải về để mở.")

PREPARED_KEY = "prepared_download"   # id tài liệu đang được chuẩn bị tải


def _human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def _render_download(file_path: Path, doc: dict) -> None:
    """Chỉ đọc file vào RAM khi người dùng bấm chuẩn bị tải."""
    doc_id = doc["id"]
    if st.session_state.get(PREPARED_KEY) == doc_id:
        st.download_button(
            "✅ Bấm để lưu file",
            data=file_path.read_bytes(),          # chỉ đọc cho đúng tài liệu này
            file_name=storage.original_filename(doc),
            key=f"dl_{doc_id}",
        )
    else:
        size = _human_size(file_path.stat().st_size)   # stat() không đọc nội dung file
        if st.button(f"⬇️ Tải file ({size})", key=f"prep_{doc_id}"):
            st.session_state[PREPARED_KEY] = doc_id
            st.rerun()


def _render_info(user: str, doc: dict, keyword: str, selected_tags: List[str]) -> None:
    st.markdown(f"### 📄 {highlight(doc['title'], keyword)}", unsafe_allow_html=True)
    st.markdown(
        f"**Tác giả:** {highlight(doc['author'], keyword)} | "
        f"**Nguồn:** {html.escape(doc['source'])}",
        unsafe_allow_html=True,
    )
    if doc["tags"]:
        tags_html = " ".join(_tag_html(t, keyword, selected_tags) for t in doc["tags"])
        st.markdown(f"**Tags:** {tags_html}", unsafe_allow_html=True)
    if doc["notes"]:
        notes_html = highlight(doc["notes"], keyword).replace("\n", "<br>")
        st.markdown(f"> 📝 **Ghi chú cá nhân:** {notes_html}", unsafe_allow_html=True)
    file_path = storage.get_file_path(user, doc)
    if file_path:
        _render_preview(file_path, doc)
        _render_download(file_path, doc)     


def _render_actions(user: str, doc: dict) -> None:
    with st.expander("📝 Thêm/Sửa ghi chú"):
        note = st.text_area(
            "Nội dung ghi chú", doc["notes"], key=f"note_{doc['id']}"
        )
        if st.button("Lưu ghi chú", key=f"btn_{doc['id']}"):
            storage.update_notes(user, doc, note)
            st.toast("Đã cập nhật ghi chú!", icon="✅")
            st.rerun()

    if st.button("🗑️ Xóa tài liệu", key=f"del_{doc['id']}"):
        storage.delete_doc(user, doc)
        st.toast("Đã xóa tài liệu.", icon="🗑️")
        st.rerun()


def render_document(
    user: str, doc: dict, keyword: str = "", selected_tags: Optional[List[str]] = None
) -> None:
    with _doc_container(doc, is_search_active(keyword, selected_tags)):
        col_info, col_actions = st.columns([3, 1])
        with col_info:
            _render_info(user, doc, keyword, selected_tags or [])
        with col_actions:
            _render_actions(user, doc)
        st.markdown("---")


def render_document_list(
    user: str,
    filtered: List[dict],
    total: int,
    keyword: str = "",
    selected_tags: Optional[List[str]] = None,
) -> None:
    selected_tags = selected_tags or []
    st.markdown(FOUND_CSS + PREVIEW_CSS, unsafe_allow_html=True)
    st.subheader(f"📋 Kho tài liệu ({len(filtered)}/{total} tài liệu)")

    if is_search_active(keyword, selected_tags):
        criteria = []
        if keyword.strip():
            criteria.append(f"từ khóa “{keyword.strip().replace('`', '')}”")
        if selected_tags:
            criteria.append("tag " + ", ".join(selected_tags))
        if filtered:
            st.success(f"✅ Đã tìm thấy {len(filtered)} tài liệu phù hợp với " + " và ".join(criteria))
        else:
            st.warning("❌ Không tìm thấy tài liệu nào phù hợp với " + " và ".join(criteria))
    elif not filtered:
        st.info("Kho tài liệu đang trống. Hãy thêm tài liệu ở thanh bên.")

    for doc in filtered:
        render_document(user, doc, keyword, selected_tags)
