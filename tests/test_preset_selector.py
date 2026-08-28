"""
tests/test_preset_selector.py
───────────────────────────────
Test preset preview generation and PresetSelectorWidget integration in Inspector.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from PySide6.QtWidgets import QApplication

from src.presets.preview_generator import generate_highlight_preview, PREVIEW_DIR
from src.ui.preset_selector import PresetSelectorWidget
from src.ui.inspector import Inspector
from src.models import SubtitleStyle


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_preset_preview_files_exist():
    mp4_path = PREVIEW_DIR / "highlight.mp4"
    gif_path = PREVIEW_DIR / "highlight.gif"

    assert mp4_path.exists(), f"MP4 preview file missing: {mp4_path}"
    assert gif_path.exists(), f"GIF preview file missing: {gif_path}"
    assert mp4_path.stat().st_size > 0
    assert gif_path.stat().st_size > 0


def test_preset_selector_widget(qapp):
    widget = PresetSelectorWidget()
    assert widget._current_mode == "normal"

    # Test selecting mode cards
    widget.set_active_preset("normal")
    assert widget._current_mode == "normal"

    widget.set_active_preset("highlight")
    assert widget._current_mode == "highlight"


def test_inspector_preset_integration(qapp):
    inspector = Inspector()
    inspector.set_has_video(True)

    # Check style get and apply
    inspector.apply_style(SubtitleStyle(mode="highlight"))
    assert inspector.get_style().mode == "highlight"

    inspector.apply_style(SubtitleStyle(mode="pill"))
    assert inspector.get_style().mode == "pill"
