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
