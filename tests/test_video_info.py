"""
tests/test_video_info.py
────────────────────────
Kiểm thử module video_info (probe_video, _find_binary).
Chạy: python -m pytest tests/ -v
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.video_info import probe_video, get_ffprobe, get_ffmpeg, FFmpegNotFoundError, VideoReadError


class TestFindBinary:
    def test_ffprobe_found(self):
        """ffprobe phải tìm được trong PATH hoặc binaries/."""
        path = get_ffprobe()
        assert "ffprobe" in path.lower()

    def test_ffmpeg_found(self):
        path = get_ffmpeg()
        assert "ffmpeg" in path.lower()


class TestProbeVideo:
    def test_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            probe_video(tmp_path / "no_such_video.mp4")

    def test_raises_video_read_error_on_non_video(self, tmp_path):
        """Truyền file text vào ffprobe phải raise VideoReadError."""
        fake = tmp_path / "fake.mp4"
        fake.write_text("this is not a video", encoding="utf-8")
        with pytest.raises(VideoReadError):
            probe_video(fake)
