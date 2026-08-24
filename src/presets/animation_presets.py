"""
src/presets/animation_presets.py
─────────────────────────────────
Preset animation definitions for subtitle styles (6 Core Styles).
"""

from dataclasses import dataclass
from typing import Literal

SubtitleAnimationType = Literal[
    "normal",
    "highlight",
    "soft_pop",
    "soft-pop",
    "punch",
    "rise",
    "marker",
    "pill",
]


@dataclass(frozen=True)
class SoftPopPreset:
    """Preset 2: Soft Pop phrase entrance animation configuration."""

    start_scale: float = 0.92
    overshoot_scale: float = 1.04
    end_scale: float = 1.00
    overshoot_ms: int = 100
    duration_ms: int = 180
    ass_tag: str = r"{\fscx92\fscy92\fad(180,0)\t(0,100,\fscx104\fscy104)\t(100,180,\fscx100\fscy100)}"


SOFT_POP_PRESET = SoftPopPreset()


@dataclass(frozen=True)
class PunchPreset:
    """Preset 3: Punch word-level scale highlight animation configuration."""

    start_scale: float = 1.00
    peak_scale: float = 1.12
    end_scale: float = 1.00
    peak_ms: int = 80
    duration_ms: int = 160


PUNCH_PRESET = PunchPreset()


@dataclass(frozen=True)
class RisePreset:
    """Preset 4: Rise phrase entrance animation configuration."""

    translate_y_px: int = 16
    duration_ms: int = 200


RISE_PRESET = RisePreset()


@dataclass(frozen=True)
class PillPreset:
    """Preset: Pill word-level moving rounded background animation configuration."""

    highlight_color: str = "#FFD84D"
    active_text_color: str = "auto"
    inactive_text_color: str = "#FFFFFF"
    padding_x: int = 10
    padding_y: int = 4
    radius: int = 10
    transition_ms: int = 260
    easing: str = "ease_out_cubic"


PILL_PRESET = PillPreset()

