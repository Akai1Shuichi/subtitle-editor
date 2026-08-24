"""
tests/test_pill_renderer.py
───────────────────────────
Unit tests for PillSubtitleRenderer matching docs/pill_subtitle_animation_ai_prompt.md specs.
"""

import unittest
from PIL import Image

from src.models import SubtitleClip, SubtitleStyle
from src.pill_renderer import (
    PillAnimationConfig,
    PillSubtitleRenderer,
    Rect,
    SubtitleWord,
    WordLayout,
    ease_out_cubic,
    find_active_word,
    get_contrast_color,
    calculate_relative_luminance,
    lerp,
    word_to_pill_rect,
)


class TestPillRenderer(unittest.TestCase):
    def setUp(self):
        self.renderer = PillSubtitleRenderer()
        self.words = [
            SubtitleWord("Design", 0, 400),
            SubtitleWord("for", 400, 700),
            SubtitleWord("human", 700, 1100),
            SubtitleWord("attention", 1100, 1600),
        ]

    def test_find_active_word(self):
        self.assertEqual(find_active_word(self.words, 0), 0)
        self.assertEqual(find_active_word(self.words, 200), 0)
        self.assertEqual(find_active_word(self.words, 400), 1)
        self.assertEqual(find_active_word(self.words, 699), 1)
        self.assertEqual(find_active_word(self.words, 700), 2)
        self.assertEqual(find_active_word(self.words, 1200), 3)

    def test_gap_holding(self):
        # Gap between word 1 (ends 700) and word 2 (starts 750)
        gap_words = [
            SubtitleWord("word1", 0, 700),
            SubtitleWord("word2", 750, 1200),
        ]
        # With hold_during_gap=True, at 720ms active_idx holds at 0
        self.assertEqual(find_active_word(gap_words, 720, hold_during_gap=True), 0)
        # With hold_during_gap=False, at 720ms active_idx is None
        self.assertIsNone(find_active_word(gap_words, 720, hold_during_gap=False))

    def test_lerp_and_easing(self):
        self.assertAlmostEqual(lerp(10.0, 20.0, 0.0), 10.0)
        self.assertAlmostEqual(lerp(10.0, 20.0, 0.5), 15.0)
        self.assertAlmostEqual(lerp(10.0, 20.0, 1.0), 20.0)

        self.assertAlmostEqual(ease_out_cubic(0.0), 0.0)
        self.assertAlmostEqual(ease_out_cubic(1.0), 1.0)
        self.assertAlmostEqual(ease_out_cubic(0.5), 0.875)

    def test_auto_contrast(self):
        self.assertEqual(get_contrast_color("#FFD84D"), "#111111")
        self.assertEqual(get_contrast_color("#2563EB"), "#FFFFFF")
        self.assertEqual(get_contrast_color("#7C3AED"), "#FFFFFF")

    def test_A_width_scaling(self):
        """Test A: Pill width changes proportionally to word layout width for 'I WWW iii IMPORTANT'."""
        clip = SubtitleClip(id="test-width", text="I WWW iii IMPORTANT", start_ms=0, end_ms=2000)
        style = SubtitleStyle(fontname="Arial", fontsize=54)
        layout = self.renderer.prepare_layout(clip.text, style, 1920, 1080)

        words_layout = layout.words
        self.assertEqual(len(words_layout), 4)

        # 'I' < 'WWW', 'iii' < 'IMPORTANT'
        self.assertLess(words_layout[0].width, words_layout[1].width)
        self.assertLess(words_layout[2].width, words_layout[3].width)

    def test_B_vertical_alignment_stability(self):
        """Test B: Pill y & height remain stable across descenders for 'AI gyp HELLO'."""
        clip = SubtitleClip(id="test-vert", text="AI gyp HELLO", start_ms=0, end_ms=2000)
        style = SubtitleStyle(fontname="Arial", fontsize=54)
        layout = self.renderer.prepare_layout(clip.text, style, 1920, 1080)

        w_ai, w_gyp, w_hello = layout.words
        # All words on the same line must share identical line_y (y) and line_height (height)
        self.assertEqual(w_ai.y, w_gyp.y)
        self.assertEqual(w_gyp.y, w_hello.y)
        self.assertEqual(w_ai.height, w_gyp.height)
        self.assertEqual(w_gyp.height, w_hello.height)

    def test_C_vietnamese_support(self):
        """Test C: Vietnamese text 'Điều này thực sự quan trọng' layout and active word."""
        clip = SubtitleClip(id="test-vn", text="Điều này thực sự quan trọng", start_ms=0, end_ms=2000)
        style = SubtitleStyle(fontname="Arial", fontsize=54)
        layout = self.renderer.prepare_layout(clip.text, style, 1920, 1080)
        self.assertEqual(len(layout.words), 6)
        self.assertEqual(layout.words[2].text, "thực")
        self.assertEqual(layout.words[3].text, "sự")

    def test_D_word_timing_mapping(self):
        """Test D: Word timing mapping across specific timestamp milestones."""
        timing_words = [
            SubtitleWord("Điều", 0, 300),
            SubtitleWord("này", 300, 550),
            SubtitleWord("thực", 550, 800),
            SubtitleWord("sự", 800, 950),
            SubtitleWord("quan", 950, 1200),
            SubtitleWord("trọng", 1200, 1600),
        ]

        self.assertEqual(find_active_word(timing_words, 100), 0)
        self.assertEqual(find_active_word(timing_words, 400), 1)
        self.assertEqual(find_active_word(timing_words, 700), 2)
        self.assertEqual(find_active_word(timing_words, 900), 3)
        self.assertEqual(find_active_word(timing_words, 1100), 4)
        self.assertEqual(find_active_word(timing_words, 1400), 5)

    def test_debug_layout_rendering(self):
        clip = SubtitleClip(id="test-debug", text="Debug layout test", start_ms=0, end_ms=1000)
        style = SubtitleStyle(fontname="Arial", fontsize=40)
        config = PillAnimationConfig(debug_layout=True)

        frame = self.renderer.render_frame(
            clip=clip,
            time_ms=200,
            style=style,
            config=config,
            video_width=640,
            video_height=360,
        )
        self.assertIsInstance(frame, Image.Image)


if __name__ == "__main__":
    unittest.main()
