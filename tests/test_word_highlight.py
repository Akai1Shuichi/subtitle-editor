"""
tests/test_word_highlight.py
─────────────────────────────
Kiểm thử word_timing và chế độ highlight trong ass_builder.
Chạy: python -m pytest tests/test_word_highlight.py -v
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pysubs2

from src.word_timing import (
    WordTiming, LineTiming, TimingFile,
    save_timing, load_timing, timing_from_subs,
)
from src.ass_builder import build_ass, _make_sentence_karaoke, _make_perword_karaoke


# ──────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────

SAMPLE_SRT = """\
1
00:00:01,000 --> 00:00:03,000
AI đang thay đổi

2
00:00:04,000 --> 00:00:06,000
cách chúng ta lập trình
"""


@pytest.fixture
def subs():
    return pysubs2.SSAFile.from_string(SAMPLE_SRT, format_="srt")


@pytest.fixture
def line_timing_exact():
    """LineTiming với per-word timing cho dòng 'AI đang thay đổi'."""
    return LineTiming(
        index=0,
        start_ms=1000,
        end_ms=3000,
        words=[
            WordTiming("AI",   start_ms=1000, end_ms=1400),
            WordTiming("đang", start_ms=1420, end_ms=1700),
            WordTiming("thay", start_ms=1720, end_ms=2100),
            WordTiming("đổi",  start_ms=2120, end_ms=3000),
        ],
    )


@pytest.fixture
def timing_file(line_timing_exact):
    line2 = LineTiming(
        index=1,
        start_ms=4000,
        end_ms=6000,
        words=[],  # dòng 2 chưa có word timing
    )
    return TimingFile(
        source_srt="test.srt",
        lines=[line_timing_exact, line2],
    )


# ──────────────────────────────────────────────────────────────────────────
# WordTiming
# ──────────────────────────────────────────────────────────────────────────

class TestWordTiming:
    def test_duration_ms(self):
        wt = WordTiming("hello", 1000, 1500)
        assert wt.duration_ms() == 500

    def test_duration_cs(self):
        wt = WordTiming("hello", 1000, 1500)
        assert wt.duration_cs() == 50   # 500ms / 10

    def test_duration_cs_minimum_1(self):
        """duration_cs không bao giờ bằng 0."""
        wt = WordTiming("x", 1000, 1000)
        assert wt.duration_cs() == 1

    def test_raises_on_invalid_timing(self):
        with pytest.raises(ValueError):
            WordTiming("bad", start_ms=2000, end_ms=1000)

    def test_vietnamese_word(self):
        wt = WordTiming("ươu", 500, 800)
        assert wt.word == "ươu"
        assert wt.duration_ms() == 300


# ──────────────────────────────────────────────────────────────────────────
# LineTiming
# ──────────────────────────────────────────────────────────────────────────

class TestLineTiming:
    def test_has_word_timing_true(self, line_timing_exact):
        assert line_timing_exact.has_word_timing is True

    def test_has_word_timing_false(self):
        lt = LineTiming(index=0, start_ms=0, end_ms=1000, words=[])
        assert lt.has_word_timing is False

    def test_duration_ms(self, line_timing_exact):
        assert line_timing_exact.duration_ms() == 2000


# ──────────────────────────────────────────────────────────────────────────
# TimingFile
# ──────────────────────────────────────────────────────────────────────────

class TestTimingFile:
    def test_get_line_found(self, timing_file, line_timing_exact):
        result = timing_file.get_line(0)
        assert result is line_timing_exact

    def test_get_line_not_found(self, timing_file):
        assert timing_file.get_line(99) is None

    def test_has_any_word_timing_true(self, timing_file):
        assert timing_file.has_any_word_timing() is True

    def test_has_any_word_timing_false(self):
        tf = TimingFile(source_srt="x.srt", lines=[
            LineTiming(index=0, start_ms=0, end_ms=1000, words=[]),
        ])
        assert tf.has_any_word_timing() is False


# ──────────────────────────────────────────────────────────────────────────
# Save / Load JSON
# ──────────────────────────────────────────────────────────────────────────

class TestTimingFileSaveLoad:
    def test_roundtrip(self, tmp_path, timing_file):
        dest = tmp_path / "test.words.json"
        save_timing(timing_file, dest)
        loaded = load_timing(dest)

        assert loaded.source_srt == "test.srt"
        assert len(loaded.lines) == 2

        line0 = loaded.get_line(0)
        assert line0 is not None
        assert len(line0.words) == 4
        assert line0.words[0].word == "AI"
        assert line0.words[0].start_ms == 1000

    def test_saves_valid_json(self, tmp_path, timing_file):
        import json
        dest = tmp_path / "test.words.json"
        save_timing(timing_file, dest)
        data = json.loads(dest.read_text(encoding="utf-8"))
        assert data["version"] == 1
        assert data["source_srt"] == "test.srt"

    def test_vietnamese_text_preserved(self, tmp_path):
        tf = TimingFile(source_srt="viet.srt", lines=[
            LineTiming(index=0, start_ms=0, end_ms=2000, words=[
                WordTiming("ươu", 0, 500),
                WordTiming("ổi",  600, 1000),
            ])
        ])
        dest = tmp_path / "viet.words.json"
        save_timing(tf, dest)
        loaded = load_timing(dest)
        assert loaded.lines[0].words[0].word == "ươu"
        assert loaded.lines[0].words[1].word == "ổi"

    def test_load_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_timing(tmp_path / "nonexistent.words.json")

    def test_load_raises_on_invalid_json(self, tmp_path):
        bad = tmp_path / "bad.words.json"
        bad.write_text("not json at all", encoding="utf-8")
        with pytest.raises(ValueError, match="JSON"):
            load_timing(bad)

    def test_load_raises_on_wrong_version(self, tmp_path):
        import json
        dest = tmp_path / "v2.words.json"
        dest.write_text(json.dumps({"version": 2, "source_srt": "", "lines": []}),
                        encoding="utf-8")
        with pytest.raises(ValueError, match="version"):
            load_timing(dest)

    def test_empty_lines_roundtrip(self, tmp_path):
        tf = TimingFile(source_srt="empty.srt", lines=[])
        dest = tmp_path / "empty.words.json"
        save_timing(tf, dest)
        loaded = load_timing(dest)
        assert loaded.lines == []


# ──────────────────────────────────────────────────────────────────────────
# timing_from_subs
# ──────────────────────────────────────────────────────────────────────────

class TestTimingFromSubs:
    def test_creates_skeleton(self, subs):
        tf = timing_from_subs(subs, "test.srt")
        assert tf.source_srt == "test.srt"
        assert len(tf.lines) == 2
        assert all(not ln.has_word_timing for ln in tf.lines)

    def test_timing_matches_events(self, subs):
        tf = timing_from_subs(subs)
        assert tf.lines[0].start_ms == 1000
        assert tf.lines[0].end_ms == 3000
        assert tf.lines[1].start_ms == 4000
        assert tf.lines[1].end_ms == 6000


# ──────────────────────────────────────────────────────────────────────────
# TikTok word-pop renderer
# ──────────────────────────────────────────────────────────────────────────

class TestWordPopHighlight:
    def test_font_size_is_not_downscaled_for_720_by_1280_video(self, subs):
        ass = build_ass(subs, "highlight", fontsize=60, video_width=720, video_height=1280)
        assert ass.styles["Default"].fontsize == 60

    def test_whole_segment_is_rendered_from_its_first_word(self, subs, timing_file):
        ass = build_ass(subs, "highlight", word_timings=timing_file)
        first = min(ass.events, key=lambda event: event.start)
        assert "AI" in first.text
        assert "đang" in first.text
        assert "thay" in first.text
        assert "đổi" in first.text
        assert r"\1c&H00D9FF&" in first.text

    def test_word_timing_drives_the_next_active_word(self, subs, timing_file):
        ass = build_ass(subs, "highlight", word_timings=timing_file)
        active_dang = [event for event in ass.events if event.start >= 1400 and "đang" in event.text]
        assert active_dang
        assert any("AI" in event.text and r"\1c&H00D9FF&" in event.text for event in active_dang)

    def test_renderer_preserves_source_case(self, subs, timing_file):
        ass = build_ass(subs, "highlight", word_timings=timing_file)
        first = min(ass.events, key=lambda event: event.start)
        assert "đang" in first.text
        assert "ĐANG" not in first.text

    def test_no_karaoke_fill_tags(self, subs, timing_file):
        ass = build_ass(subs, "highlight", word_timings=timing_file)
        assert all(r"\kf" not in event.text for event in ass.events)

    def test_highlight_does_not_scale_or_shift_the_group(self, subs, timing_file):
        ass = build_ass(subs, "highlight", word_timings=timing_file)
        text = "\n".join(event.text for event in ass.events)
        assert r"\fscx" not in text
        assert r"\fscy" not in text

    def test_line_break_is_identical_for_every_active_word(self, subs, timing_file):
        ass = build_ass(subs, "highlight", word_timings=timing_file)
        first_word_events = [event for event in ass.events if event.start < 1420]
        second_word_events = [event for event in ass.events if 1420 <= event.start < 1720]
        assert first_word_events and second_word_events
        clean_texts = [event.text.replace(r"{\r}", "").replace(r"{\1c&H00D9FF&}", "") for event in first_word_events + second_word_events]
        assert len(set(clean_texts)) == 1
