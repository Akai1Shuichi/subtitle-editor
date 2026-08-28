"""
tests/test_capcut_parser.py
────────────────────────────
Unit tests cho src/capcut_json_parser.py bằng unittest.
"""

from pathlib import Path
import unittest

from src.capcut_json_parser import (
    load_from_capcut_json,
    CapCutJsonFormatError,
    CapCutJsonSubtitleError,
)

DATA_DIR = Path(__file__).parent.parent / "data"


class TestCapCutParser(unittest.TestCase):
    def test_load_draft_content(self):
        json_path = DATA_DIR / "draft_content.json"
        self.assertTrue(json_path.exists(), "File data/draft_content.json phải tồn tại")

        clips, timing = load_from_capcut_json(json_path)

        self.assertEqual(len(clips), 16)
        self.assertEqual(len(timing.lines), 16)

        # Test clip 0
        c0 = clips[0]
        self.assertEqual(c0.text, "AI đang thay đổi cách chúng ta làm việc mỗi ngày")
        self.assertEqual(c0.start_ms, 267)
        self.assertEqual(c0.end_ms, 2334)

        # Test line timing 0
        t0 = timing.lines[0]
        self.assertEqual(t0.index, 0)
        self.assertEqual(t0.start_ms, 267)
        self.assertEqual(t0.end_ms, 2334)
        self.assertGreater(len(t0.words), 0)

        # Kiểm tra từ đầu tiên của t0
        w0 = t0.words[0]
        self.assertEqual(w0.word, "AI")
        self.assertGreaterEqual(w0.start_ms, c0.start_ms)
        self.assertLessEqual(w0.end_ms, c0.end_ms)

    def test_load_draft_content_animated(self):
        json_path = DATA_DIR / "draft_content_animated.json"
        self.assertTrue(json_path.exists(), "File data/draft_content_animated.json phải tồn tại")

        clips, timing = load_from_capcut_json(json_path)

        self.assertEqual(len(clips), 16)
        self.assertEqual(len(timing.lines), 16)

        c0 = clips[0]
        self.assertEqual(c0.text, "AI đang thay đổi cách chúng ta làm việc mỗi ngày")
        self.assertEqual(c0.start_ms, 267)
        self.assertEqual(c0.end_ms, 2334)

    def test_invalid_file_format(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            f.write('{"foo": "bar"}')
            temp_path = Path(f.name)

        try:
            with self.assertRaises(CapCutJsonFormatError):
                load_from_capcut_json(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            load_from_capcut_json("non_existent_file.json")


if __name__ == "__main__":
    unittest.main()
