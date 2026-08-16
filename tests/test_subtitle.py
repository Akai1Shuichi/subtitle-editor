"""
tests/test_subtitle.py
──────────────────────
Kiểm thử module subtitle_parser và ass_builder.
Chạy: python -m pytest tests/ -v
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pysubs2
from pysubs2 import Alignment
from src.subtitle_parser import load_srt, count_lines, EncodingError, ParseError
from src.ass_builder import build_ass, save_ass

# ──────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────

SAMPLE_SRT = """\
1
00:00:01,000 --> 00:00:03,000
AI đang thay đổi cách chúng ta lập trình

2
00:00:04,000 --> 00:00:06,000
Subtitle có emoji 🎉 và ký tự đặc biệt!

3
00:00:07,000 --> 00:00:09,500
Tiếng Việt: ươu, ổi, ếch, ừ nhỉ?
"""

SAMPLE_SRT_LATIN1 = b"\x80\x81 invalid utf-8 bytes"


@pytest.fixture
def srt_file(tmp_path: Path) -> Path:
    f = tmp_path / "sample.srt"
    f.write_text(SAMPLE_SRT, encoding="utf-8")
    return f


@pytest.fixture
def srt_utf8_bom(tmp_path: Path) -> Path:
    """SRT với UTF-8 BOM – hợp lệ."""
    f = tmp_path / "bom.srt"
    f.write_bytes(b"\xef\xbb\xbf" + SAMPLE_SRT.encode("utf-8"))
    return f


@pytest.fixture
def srt_invalid_encoding(tmp_path: Path) -> Path:
    f = tmp_path / "bad.srt"
    f.write_bytes(SAMPLE_SRT_LATIN1)
    return f


@pytest.fixture
def srt_empty(tmp_path: Path) -> Path:
    f = tmp_path / "empty.srt"
    f.write_text("", encoding="utf-8")
    return f


# ──────────────────────────────────────────────────────────────────────────
# subtitle_parser tests
# ──────────────────────────────────────────────────────────────────────────

class TestLoadSrt:
    def test_load_valid_utf8(self, srt_file):
        subs = load_srt(srt_file)
        assert len(subs.events) == 3

    def test_load_utf8_bom(self, srt_utf8_bom):
        subs = load_srt(srt_utf8_bom)
        assert len(subs.events) == 3

    def test_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_srt(tmp_path / "nonexistent.srt")

    def test_raises_encoding_error(self, srt_invalid_encoding):
        with pytest.raises(EncodingError):
            load_srt(srt_invalid_encoding)

    def test_raises_parse_error_on_empty(self, srt_empty):
        with pytest.raises(ParseError):
            load_srt(srt_empty)

    def test_count_lines(self, srt_file):
        subs = load_srt(srt_file)
        assert count_lines(subs) == 3

    def test_vietnamese_text_preserved(self, srt_file):
        subs = load_srt(srt_file)
        texts = " ".join(e.text for e in subs.events)
        assert "ươu" in texts
        assert "🎉" in texts


# ──────────────────────────────────────────────────────────────────────────
# ass_builder tests
# ──────────────────────────────────────────────────────────────────────────

class TestBuildAss:
    def setup_method(self):
        self.subs = pysubs2.SSAFile.from_string(SAMPLE_SRT, format_="srt")

    def test_normal_mode_events_count(self):
        ass = build_ass(self.subs, "normal")
        assert len(ass.events) == 3

    def test_normal_mode_no_karaoke_tags(self):
        ass = build_ass(self.subs, "normal")
        for e in ass.events:
            assert r"\kf" not in e.text
            assert r"\k" not in e.text

    def test_highlight_mode_has_karaoke_tags(self):
        ass = build_ass(self.subs, "highlight")
        for e in ass.events:
            assert r"\kf" in e.text

    def test_default_style_applied(self):
        ass = build_ass(self.subs, "normal")
        assert "Default" in ass.styles
        style = ass.styles["Default"]
        assert style.fontname == "Montserrat"
        assert style.fontsize == 48

    def test_custom_style_params(self):
        ass = build_ass(
            self.subs, "normal",
            fontname="Arial",
            fontsize=36,
            text_color=(255, 0, 0),
        )
        style = ass.styles["Default"]
        assert style.fontname == "Arial"
        assert style.fontsize == 36
        # primarycolor RGBA → Red channel
        assert style.primarycolor.r == 255
        assert style.primarycolor.g == 0

    def test_save_ass_creates_file(self, tmp_path):
        ass = build_ass(self.subs, "normal")
        dest = tmp_path / "out.ass"
        result = save_ass(ass, dest)
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "[Script Info]" in content
        assert "[Events]" in content

    def test_alignment_set(self):
        ass = build_ass(self.subs, "normal", alignment=Alignment.TOP_CENTER)
        assert ass.styles["Default"].alignment == Alignment.TOP_CENTER
