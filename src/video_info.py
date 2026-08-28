"""
video_info.py
─────────────
Lấy thông tin video (resolution, duration, fps) bằng ffprobe.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class FFmpegNotFoundError(RuntimeError):
    """ffmpeg / ffprobe không tìm thấy trong PATH hoặc binaries/."""


class VideoReadError(RuntimeError):
    """Video không đọc được hoặc không hợp lệ."""


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@dataclass
class VideoInfo:
    width: int
    height: int
    duration: float      # giây
    fps: float
    path: Path

    @property
    def resolution(self) -> str:
        return f"{self.width}x{self.height}"

    @property
    def duration_str(self) -> str:
        """Định dạng mm:ss."""
        m, s = divmod(int(self.duration), 60)
        return f"{m:02d}:{s:02d}"

    def to_dict(self) -> dict:
        """Chuyển VideoInfo thành dict để serialize JSON."""
        return {
            "width": self.width,
            "height": self.height,
            "duration": self.duration,
            "fps": self.fps,
            "path": str(self.path),
        }

    @classmethod
    def from_dict(cls, data: dict) -> VideoInfo:
        """Khôi phục VideoInfo từ dict JSON với tự động tìm file video nếu đường dẫn tương đối."""
        import sys
        raw_path = str(data.get("path", ""))
        vpath = Path(raw_path) if raw_path else Path("")
        if raw_path and not vpath.is_file():
            base_dir = Path(sys._MEIPASS) if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS") else Path(__file__).parent.parent
            rel_root = base_dir / raw_path
            rel_samples = base_dir / "data" / "samples" / Path(raw_path).name
            if rel_root.is_file():
                vpath = rel_root
            elif rel_samples.is_file():
                vpath = rel_samples

        return cls(
            width=int(data.get("width", 0)),
            height=int(data.get("height", 0)),
            duration=float(data.get("duration", 0.0)),
            fps=float(data.get("fps", 0.0)),
            path=vpath,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_binary(name: str) -> str:
    """
    Tìm binary theo thứ tự:
    1. binaries/<name> trong _MEIPASS (nếu đóng gói trong EXE)
    2. binaries/<name> cùng cấp file executable (.exe)
    3. Cùng thư mục với file executable (.exe)
    4. binaries/<name> trong thư mục mã nguồn
    5. PATH hệ thống
    """
    import os
    import sys
    candidates: list[Path] = []

    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            candidates.append(Path(sys._MEIPASS) / "binaries")
        exe_dir = Path(sys.executable).parent
        candidates.append(exe_dir / "binaries")
        candidates.append(exe_dir)
    
    candidates.append(Path(__file__).parent.parent / "binaries")

    exts = (".exe", "") if sys.platform == "win32" else ("",)

    for binaries_dir in candidates:
        for ext in exts:
            candidate = binaries_dir / (name + ext)
            if candidate.is_file():
                if sys.platform == "win32" or os.access(candidate, os.X_OK):
                    return str(candidate)

    found = shutil.which(name)
    if found:
        return found

    raise FFmpegNotFoundError(
        f"Không tìm thấy '{name}'. Hãy cài FFmpeg vào PATH hệ thống hoặc đặt file '{name}' vào thư mục binaries/."
    )


def get_ffprobe() -> str:
    return _find_binary("ffprobe")


def get_ffmpeg() -> str:
    return _find_binary("ffmpeg")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def probe_video(path: str | Path) -> VideoInfo:
    """
    Chạy ffprobe để lấy thông tin video.

    Raises
    ------
    FFmpegNotFoundError – ffprobe không có
    VideoReadError      – video không đọc được / không có video stream
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy video: {path}")

    ffprobe = get_ffprobe()

    cmd = [
        ffprobe,
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        str(path),
    ]

    extra_kwargs = {}
    if sys.platform == "win32":
        extra_kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            **extra_kwargs,
        )
    except FileNotFoundError as exc:
        raise FFmpegNotFoundError("ffprobe không tìm thấy.") from exc
    except subprocess.TimeoutExpired as exc:
        raise VideoReadError("ffprobe timeout – video quá lớn hoặc bị lỗi.") from exc

    if result.returncode != 0:
        raise VideoReadError(
            f"Không đọc được video '{path.name}'.\n"
            f"ffprobe stderr: {result.stderr.strip()}"
        )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise VideoReadError("ffprobe trả về dữ liệu không hợp lệ.") from exc

    # Lấy video stream đầu tiên
    video_stream = next(
        (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
        None,
    )
    if video_stream is None:
        raise VideoReadError(f"'{path.name}' không có video stream nào.")

    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))

    # FPS: r_frame_rate = "30000/1001" → 29.97 fps
    fps_raw = video_stream.get("r_frame_rate", "25/1")
    try:
        num, den = fps_raw.split("/")
        fps = float(num) / float(den)
    except (ValueError, ZeroDivisionError):
        fps = 25.0

    # Duration: ưu tiên format.duration (chính xác hơn)
    duration_raw = (
        data.get("format", {}).get("duration")
        or video_stream.get("duration")
        or "0"
    )
    try:
        duration = float(duration_raw)
    except ValueError:
        duration = 0.0

    return VideoInfo(
        width=width,
        height=height,
        duration=duration,
        fps=fps,
        path=path.resolve(),
    )
