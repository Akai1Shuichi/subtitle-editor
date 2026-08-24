"""
exporter.py
────────────
Chạy FFmpeg để burn subtitle ASS vào video.

Tính năng:
  - Parse stdout của FFmpeg để tính phần trăm tiến trình.
  - Hỗ trợ hủy export (cancel) qua threading.Event.
  - Xử lý các lỗi phổ biến: thiếu FFmpeg, video lỗi, hết dung lượng, hủy bởi user.
"""

from __future__ import annotations

import os
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable

from .video_info import get_ffmpeg, VideoInfo, FFmpegNotFoundError, VideoReadError
from .pill_renderer import PillSubtitleRenderer
from .models import SubtitleClip, SubtitleStyle
from .word_timing import TimingFile



# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ExportCancelledError(RuntimeError):
    """Export bị hủy bởi người dùng."""


class DiskSpaceError(OSError):
    """Không đủ dung lượng ổ đĩa."""


class ExportError(RuntimeError):
    """Lỗi export chung."""


# ---------------------------------------------------------------------------
# Progress regex
# ---------------------------------------------------------------------------
# FFmpeg in thông tin tiến trình dạng:
#   frame=  120 fps= 30 q=28.0 size=    1024kB time=00:00:04.00 bitrate=...
_PROGRESS_RE = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")


def _parse_progress_seconds(line: str) -> float | None:
    """Trích xuất số giây đã xử lý từ dòng output FFmpeg."""
    m = _PROGRESS_RE.search(line)
    if not m:
        return None
    h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
    return h * 3600 + mi * 60 + s


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def export_video(
    video_info: VideoInfo,
    ass_path: str | Path,
    output_path: str | Path,
    *,
    cancel_event: threading.Event | None = None,
    on_progress: Callable[[float], None] | None = None,
) -> Path:
    """
    Burn file ASS vào video và xuất MP4.

    Parameters
    ----------
    video_info   : VideoInfo từ probe_video()
    ass_path     : đường dẫn file .ass tạm
    output_path  : đường dẫn file MP4 đích
    cancel_event : set() event để hủy export
    on_progress  : callback(percent: float) gọi khi tiến trình thay đổi

    Returns
    -------
    Path tới file output đã tạo

    Raises
    ------
    FFmpegNotFoundError   – ffmpeg không có
    ExportCancelledError  – người dùng hủy
    DiskSpaceError        – hết dung lượng
    ExportError           – lỗi khác
    """
    ass_path = Path(ass_path).resolve()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Xóa file output cũ nếu còn (tránh lỗi muxer)
    if output_path.exists():
        output_path.unlink()

    ffmpeg = get_ffmpeg()

    # Escape đường dẫn cho filter subtitle (Windows: backslash → /)
    ass_escaped = str(ass_path).replace("\\", "/").replace(":", "\\:")

    cmd = [
        ffmpeg,
        "-y",                                       # ghi đè không hỏi
        "-i", str(video_info.path),
        "-vf", f"ass='{ass_escaped}'",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(output_path),
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError as exc:
        raise FFmpegNotFoundError("ffmpeg không tìm thấy.") from exc

    duration = video_info.duration or 1.0

    try:
        for line in proc.stderr:
            # Kiểm tra hủy
            if cancel_event and cancel_event.is_set():
                proc.kill()
                proc.wait()
                _cleanup(output_path)
                raise ExportCancelledError("Export đã bị hủy bởi người dùng.")

            # Parse tiến trình
            if on_progress:
                secs = _parse_progress_seconds(line)
                if secs is not None:
                    pct = min(secs / duration * 100, 99.9)
                    on_progress(pct)

            # Kiểm tra lỗi dung lượng
            if "no space left" in line.lower():
                proc.kill()
                proc.wait()
                _cleanup(output_path)
                raise DiskSpaceError(
                    "Không đủ dung lượng ổ đĩa để xuất video. "
                    "Hãy giải phóng dung lượng và thử lại."
                )

        proc.wait()

    except ExportCancelledError:
        raise
    except DiskSpaceError:
        raise
    except Exception as exc:
        proc.kill()
        _cleanup(output_path)
        raise ExportError(f"Lỗi trong quá trình export: {exc}") from exc

    if proc.returncode != 0:
        _cleanup(output_path)
        raise ExportError(
            f"FFmpeg kết thúc với mã lỗi {proc.returncode}. "
            "Hãy kiểm tra lại file video hoặc subtitle."
        )

    if on_progress:
        on_progress(100.0)

    return output_path.resolve()


def export_video_pill(
    video_info: VideoInfo,
    clips: list[SubtitleClip],
    style: SubtitleStyle,
    output_path: str | Path,
    *,
    word_timings: TimingFile | None = None,
    cancel_event: threading.Event | None = None,
    on_progress: Callable[[float], None] | None = None,
) -> Path:
    """
    Export video với Pill Subtitle Animation thông qua raw RGBA stream đến FFmpeg.
    """
    renderer = PillSubtitleRenderer()
    return renderer.export_video_with_pill(
        video_info=video_info,
        clips=clips,
        style=style,
        output_path=output_path,
        word_timings=word_timings,
        cancel_event=cancel_event,
        on_progress=on_progress,
    )



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cleanup(path: Path) -> None:
    """Xóa file output dở dang nếu export thất bại."""
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------

def generate_preview_clip(
    video_info: VideoInfo,
    ass_path: str | Path,
    duration: float = 5.0,
    cancel_event: threading.Event | None = None,
    on_progress: Callable[[float], None] | None = None,
) -> Path:
    """
    Render đoạn video ngắn (mặc định 5 giây đầu) với subtitle đã burn
    vào temp/preview.mp4, rồi trả về đường dẫn để mở bằng media player.

    Parameters
    ----------
    video_info   : VideoInfo từ probe_video()
    ass_path     : đường dẫn file .ass tạm
    duration     : số giây cần preview (mặc định 5s)
    cancel_event : để hủy nếu cần
    on_progress  : callback(percent) báo tiến trình

    Returns
    -------
    Path tới temp/preview.mp4
    """
    preview_path = Path("temp") / "preview.mp4"
    preview_path.parent.mkdir(exist_ok=True)
    _cleanup(preview_path)

    ass_path = Path(ass_path).resolve()
    ffmpeg = get_ffmpeg()
    ass_escaped = str(ass_path).replace("\\", "/").replace(":", "\\:")

    # Lấy thời gian bắt đầu hợp lý (không start từ 0 nếu video dài)
    start_offset = 0.0

    cmd = [
        ffmpeg, "-y",
        "-ss", str(start_offset),
        "-i", str(video_info.path),
        "-t", str(duration),
        "-vf", f"ass='{ass_escaped}'",
        "-c:v", "libx264",
        "-preset", "ultrafast",   # nhanh nhất cho preview
        "-crf", "28",
        "-c:a", "aac",
        "-b:a", "128k",
        str(preview_path),
    ]

    try:
        proc = subprocess.Popen(
            cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True, bufsize=1
        )
    except FileNotFoundError as exc:
        raise FFmpegNotFoundError("ffmpeg không tìm thấy.") from exc

    preview_duration = min(duration, video_info.duration or duration)

    try:
        for line in proc.stderr:
            if cancel_event and cancel_event.is_set():
                proc.kill()
                proc.wait()
                _cleanup(preview_path)
                raise ExportCancelledError("Preview bị hủy.")
            if on_progress:
                secs = _parse_progress_seconds(line)
                if secs is not None:
                    pct = min(secs / preview_duration * 100, 99.9)
                    on_progress(pct)
        proc.wait()
    except ExportCancelledError:
        raise
    except Exception as exc:
        proc.kill()
        _cleanup(preview_path)
        raise ExportError(f"Lỗi tạo preview: {exc}") from exc

    if proc.returncode != 0:
        _cleanup(preview_path)
        raise ExportError("FFmpeg không tạo được preview. Kiểm tra lại video và subtitle.")

    if on_progress:
        on_progress(100.0)

    return preview_path.resolve()


def open_with_system_player(path: str | Path) -> None:
    """Mở file bằng media player mặc định của hệ thống."""
    import platform
    import subprocess
    path = str(path)
    system = platform.system()
    if system == "Windows":
        subprocess.Popen(["start", "", path], shell=True)
    elif system == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])
