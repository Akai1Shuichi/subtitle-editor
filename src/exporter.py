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
