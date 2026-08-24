"""
src/pill_renderer.py
────────────────────
Refactored Pill Subtitle Animation Renderer matching HTML inline layout behavior.

Features:
- Pure Pillow RGBA frame generation (no ASS hacks, no temporary PNG files).
- Layout box alignment (fixed line height based on font metrics ascent+descent).
- Character span prefix-range text measurement for 100% exact X and width coordinates.
- Smooth ease_out_cubic 4D lerp for words on the same line with effective transition duration scaling.
- Gap holding to prevent blinking between word timing intervals.
- Relative luminance auto-contrast calculation for active word text color.
- Debug layout box rendering mode (Red = Word, Green = Pill, Blue = Line).
- FFmpeg stdin rawvideo RGBA pipe for video export.
"""

from __future__ import annotations

import functools
import math
import os
import re
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

from .models import SubtitleClip, SubtitleStyle
from .video_info import VideoInfo, get_ffmpeg, FFmpegNotFoundError, VideoReadError
from .word_timing import LineTiming, TimingFile, WordTiming


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class SubtitleWord:
    text: str
    start_ms: int
    end_ms: int


@dataclass
class WordLayout:
    index: int
    text: str
    x: float
    y: float
    width: float
    height: float
    line_index: int
    baseline_y: float | None = None
    char_start: int = 0
    char_end: int = 0


@dataclass
class SubtitleLayout:
    words: list[WordLayout]
    phrase_x: float
    phrase_y: float
    width: float
    height: float


@dataclass
class Rect:
    x: float
    y: float
    width: float
    height: float


@dataclass
class PillAnimationConfig:
    highlight_color: str = "#FFD84D"
    bg_opacity: float = 0.88  # ~88% opacity for soft semi-transparent background
    active_text_color: str = "auto"
    inactive_text_color: str = "#FFFFFF"
    padding_x: int = 12
    padding_y: int = 4
    radius: int = 10
    radius_mode: str = "rounded"  # "rounded" = rounded rectangle, "pill" = capsule shape
    transition_ms: int = 260
    entrance_ms: int = 140
    line_fade_ms: int = 80
    easing: str = "ease_out_cubic"
    hold_last_word_during_gap: bool = True
    pill_vertical_offset: float = 0.0
    debug_layout: bool = False


# ---------------------------------------------------------------------------
# Easing & Math Helpers
# ---------------------------------------------------------------------------

def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b by factor t."""
    return a + (b - a) * t


def ease_out_cubic(t: float) -> float:
    """Cubic ease-out: 1 - (1 - t)^3."""
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def parse_color_rgba(color: str | tuple[int, int, int] | tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    """Normalize hex or tuple color into RGBA tuple (R, G, B, A)."""
    if isinstance(color, tuple):
        if len(color) == 3:
            return (color[0], color[1], color[2], 255)
        elif len(color) == 4:
            return color
    elif isinstance(color, str):
        c = color.lstrip("#")
        if len(c) == 6:
            r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
            return (r, g, b, 255)
        elif len(c) == 8:
            r, g, b, a = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), int(c[6:8], 16)
            return (r, g, b, a)
    return (255, 255, 255, 255)


def calculate_relative_luminance(color: str | tuple[int, int, int] | tuple[int, int, int, int]) -> float:
    """Calculate sRGB relative luminance according to WCAG 2.1 specifications."""
    r, g, b, _ = parse_color_rgba(color)

    def channel_luminance(c_255: int) -> float:
        c = c_255 / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r_lum = channel_luminance(r)
    g_lum = channel_luminance(g)
    b_lum = channel_luminance(b)
    return 0.2126 * r_lum + 0.7152 * g_lum + 0.0722 * b_lum


def get_contrast_color(bg_color: str | tuple[int, int, int] | tuple[int, int, int, int]) -> str:
    """Return dark text '#111111' for bright background, else light text '#FFFFFF'."""
    lum = calculate_relative_luminance(bg_color)
    return "#111111" if lum > 0.4 else "#FFFFFF"


def find_active_word(words: Sequence[SubtitleWord], time_ms: int, hold_during_gap: bool = True) -> int | None:
    """Find the index of the word active at time_ms."""
    if not words:
        return None
    for i, w in enumerate(words):
        if w.start_ms <= time_ms < w.end_ms:
            return i
    # If within phrase boundaries but between words (in a gap)
    if words[0].start_ms <= time_ms <= words[-1].end_ms:
        for i in range(len(words) - 1, -1, -1):
            if words[i].start_ms <= time_ms:
                return i if hold_during_gap else None
    return None


def word_to_pill_rect(word: WordLayout, config: PillAnimationConfig, stroke_width: float = 0.0) -> Rect:
    """Convert a WordLayout box to a Pill background Rect."""
    visual_pad = max(1.0, stroke_width * 0.35) if stroke_width > 0 else 0.0
    return Rect(
        x=word.x - config.padding_x - visual_pad,
        y=word.y - config.padding_y - visual_pad + config.pill_vertical_offset,
        width=word.width + config.padding_x * 2 + visual_pad * 2,
        height=word.height + config.padding_y * 2 + visual_pad * 2,
    )


# ---------------------------------------------------------------------------
# Font & Layout Management
# ---------------------------------------------------------------------------

_FONT_CACHE: dict[tuple[str, int], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}


def get_font(font_name: str, font_size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load or retrieve cached font by name and size."""
    key = (font_name, font_size)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    font = None
    font_paths = [
        font_name,
        f"/usr/share/fonts/truetype/{font_name.lower()}.ttf",
        f"/usr/share/fonts/TTF/{font_name.lower()}.ttf",
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        f"/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for p in font_paths:
        try:
            font = ImageFont.truetype(p, font_size)
            break
        except OSError:
            continue

    if font is None:
        try:
            font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

    _FONT_CACHE[key] = font
    return font


@functools.lru_cache(maxsize=128)
def _cached_layout(
    text: str,
    font_name: str,
    font_size: int,
    video_width: int,
    video_height: int,
    subtitle_width_pct: int,
    position_y: int,
    alignment: int,
) -> SubtitleLayout:
    """Calculate word bounding boxes and layout using HTML-style line box metrics."""
    font = get_font(font_name, font_size)
    dummy_img = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy_img)

    # Clean text and find character spans for words
    words_text = text.split()
    if not words_text:
        return SubtitleLayout(words=[], phrase_x=0, phrase_y=0, width=0, height=0)

    # Word wrapping based on max_w
    max_w = max(100, int(video_width * subtitle_width_pct / 100))

    # Calculate line wrapping preserving exact paragraph breaks
    lines_words: list[list[str]] = []
    curr_line: list[str] = []

    for word in words_text:
        candidate = " ".join(curr_line + [word])
        w_len = draw.textlength(candidate, font=font)
        if curr_line and w_len > max_w:
            lines_words.append(curr_line)
            curr_line = [word]
        else:
            curr_line.append(word)

    if curr_line:
        lines_words.append(curr_line)

    # Calculate font metrics for fixed line height
    try:
        if hasattr(font, "getmetrics"):
            ascent, descent = font.getmetrics()
        else:
            ascent, descent = font_size, int(font_size * 0.25)
    except Exception:
        ascent, descent = font_size, int(font_size * 0.25)

    line_h = ascent + descent
    total_h = len(lines_words) * line_h * 1.15

    # Vertical base position
    if alignment in (1, 2, 3):  # bottom
        base_y = video_height - ((100 - position_y) * video_height / 100) - total_h
    elif alignment in (4, 5, 6):  # center
        base_y = (video_height / 2) - (total_h / 2)
    else:  # top
        base_y = position_y * video_height / 100

    words_layout: list[WordLayout] = []
    global_idx = 0
    max_line_w = 0.0

    for line_idx, line in enumerate(lines_words):
        line_text = " ".join(line)
        line_w = draw.textlength(line_text, font=font)
        if line_w > max_line_w:
            max_line_w = line_w

        # Horizontal alignment
        if alignment in (1, 4, 7):  # left
            line_x = (video_width - max_w) / 2
        elif alignment in (3, 6, 9):  # right
            line_x = ((video_width - max_w) / 2) + max_w - line_w
        else:  # center
            line_x = (video_width - line_w) / 2

        line_y = base_y + line_idx * (line_h * 1.15)

        # Character span prefix-range measurement for 100% exact word X and width
        for w_in_line_idx, word in enumerate(line):
            # Compute char spans inside line_text
            prefix_before = " ".join(line[:w_in_line_idx]) + (" " if w_in_line_idx > 0 else "")
            prefix_after = " ".join(line[: w_in_line_idx + 1])

            start_adv = draw.textlength(prefix_before, font=font) if prefix_before else 0.0
            end_adv = draw.textlength(prefix_after, font=font)

            word_x = line_x + start_adv
            word_w = max(1.0, end_adv - start_adv)

            words_layout.append(
                WordLayout(
                    index=global_idx,
                    text=word,
                    x=word_x,
                    y=line_y,
                    width=word_w,
                    height=line_h,
                    line_index=line_idx,
                    baseline_y=line_y + ascent,
                    char_start=len(prefix_before),
                    char_end=len(prefix_after),
                )
            )
            global_idx += 1

    phrase_x = (video_width - max_line_w) / 2
    phrase_y = base_y
    return SubtitleLayout(
        words=words_layout,
        phrase_x=phrase_x,
        phrase_y=phrase_y,
        width=max_line_w,
        height=total_h,
    )


# ---------------------------------------------------------------------------
# Pill Geometry & Renderer
# ---------------------------------------------------------------------------

class PillSubtitleRenderer:
    """Stateless Pill Subtitle Renderer operating by target frame time_ms."""

    def prepare_layout(
        self,
        text: str,
        style: SubtitleStyle,
        video_width: int = 1920,
        video_height: int = 1080,
    ) -> SubtitleLayout:
        return _cached_layout(
            text=text,
            font_name=style.fontname,
            font_size=style.fontsize,
            video_width=video_width,
            video_height=video_height,
            subtitle_width_pct=style.subtitle_width,
            position_y=style.position_y,
            alignment=int(style.alignment),
        )

    def extract_words_from_clip(
        self, clip: SubtitleClip, line_timing: Optional[LineTiming] = None
    ) -> list[SubtitleWord]:
        words_text = clip.text.split()
        if not words_text:
            return []

        if line_timing and len(line_timing.words) == len(words_text) and line_timing.has_word_timing:
            return [
                SubtitleWord(text=w_text, start_ms=tw.start_ms, end_ms=tw.end_ms)
                for w_text, tw in zip(words_text, line_timing.words)
            ]

        # Uniform distribution if word timing is missing
        duration = max(1, clip.end_ms - clip.start_ms)
        n = len(words_text)
        return [
            SubtitleWord(
                text=w,
                start_ms=clip.start_ms + round(i * duration / n),
                end_ms=clip.start_ms + round((i + 1) * duration / n),
            )
            for i, w in enumerate(words_text)
        ]

    def get_pill_rect(
        self,
        words_layout: list[WordLayout],
        words_timing: list[SubtitleWord],
        time_ms: int,
        config: PillAnimationConfig,
        stroke_width: float = 0.0,
    ) -> tuple[Rect | None, float]:
        """
        Calculate animated pill Rect and opacity at time_ms.
        Returns (Rect, opacity: float in 0..1).
        """
        active_idx = find_active_word(words_timing, time_ms, config.hold_last_word_during_gap)
        if active_idx is None or active_idx >= len(words_layout):
            return None, 0.0

        curr_wl = words_layout[active_idx]
        curr_word_rect = word_to_pill_rect(curr_wl, config, stroke_width)

        # First word entrance
        if active_idx == 0:
            elapsed = time_ms - words_timing[0].start_ms
            if elapsed < config.entrance_ms and config.entrance_ms > 0:
                progress = max(0.0, min(1.0, elapsed / config.entrance_ms))
                opacity = ease_out_cubic(progress)
            else:
                opacity = 1.0
            return curr_word_rect, opacity

        # Previous word logic
        prev_idx = active_idx - 1
        prev_wl = words_layout[prev_idx]

        # If on the same line: smooth 4D lerp with effective_transition_ms
        if curr_wl.line_index == prev_wl.line_index:
            prev_word_rect = word_to_pill_rect(prev_wl, config, stroke_width)

            word_dur = words_timing[active_idx].end_ms - words_timing[active_idx].start_ms
            effective_trans = min(config.transition_ms, max(60.0, word_dur * 0.55))

            elapsed = time_ms - words_timing[active_idx].start_ms
            if elapsed < effective_trans and effective_trans > 0:
                t = max(0.0, min(1.0, elapsed / effective_trans))
                eased_t = ease_out_cubic(t)
                lerped_rect = Rect(
                    x=lerp(prev_word_rect.x, curr_word_rect.x, eased_t),
                    y=lerp(prev_word_rect.y, curr_word_rect.y, eased_t),
                    width=lerp(prev_word_rect.width, curr_word_rect.width, eased_t),
                    height=lerp(prev_word_rect.height, curr_word_rect.height, eased_t),
                )
                return lerped_rect, 1.0
            else:
                return curr_word_rect, 1.0
        else:
            # Different line: snap position, optional line fade
            elapsed = time_ms - words_timing[active_idx].start_ms
            if elapsed < config.line_fade_ms and config.line_fade_ms > 0:
                progress = max(0.0, min(1.0, elapsed / config.line_fade_ms))
                opacity = ease_out_cubic(progress)
            else:
                opacity = 1.0
            return curr_word_rect, opacity

    def render_frame(
        self,
        clip: SubtitleClip,
        time_ms: int,
        style: SubtitleStyle,
        config: Optional[PillAnimationConfig] = None,
        line_timing: Optional[LineTiming] = None,
        video_width: int = 1920,
        video_height: int = 1080,
    ) -> Image.Image:
        """
        Render a transparent RGBA image containing the pill background and subtitle text.
        """
        if config is None:
            hl = style.highlight_color
            hl_hex = f"#{hl[0]:02x}{hl[1]:02x}{hl[2]:02x}" if isinstance(hl, tuple) else str(hl)
            config = PillAnimationConfig(highlight_color=hl_hex)

        img = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))
        if not clip or not clip.is_active_at(time_ms):
            return img

        words_timing = self.extract_words_from_clip(clip, line_timing)
        if not words_timing:
            return img

        layout = self.prepare_layout(clip.text, style, video_width, video_height)
        if not layout.words:
            return img

        stroke_w = float(style.stroke_width)
        pill_rect, opacity = self.get_pill_rect(layout.words, words_timing, time_ms, config, stroke_w)

        font = get_font(style.fontname, style.fontsize)

        # 1. Render Pill Background
        if pill_rect and opacity > 0.0:
            pill_img = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))
            p_draw = ImageDraw.Draw(pill_img)

            bg_rgba = parse_color_rgba(config.highlight_color)
            fill_color = (bg_rgba[0], bg_rgba[1], bg_rgba[2], int(bg_rgba[3] * config.bg_opacity * opacity))

            radius = pill_rect.height / 2 if config.radius_mode == "pill" else config.radius

            p_draw.rounded_rectangle(
                [
                    pill_rect.x,
                    pill_rect.y,
                    pill_rect.x + pill_rect.width,
                    pill_rect.y + pill_rect.height,
                ],
                radius=max(1, int(radius)),
                fill=fill_color,
            )
            img = Image.alpha_composite(img, pill_img)

        draw = ImageDraw.Draw(img)

        # Determine active text color
        if config.active_text_color == "auto":
            active_text_color = get_contrast_color(config.highlight_color)
        else:
            active_text_color = config.active_text_color

        active_idx = find_active_word(words_timing, time_ms, config.hold_last_word_during_gap)

        # 2. Render Inactive Text (skip active word to prevent color bleeding later)
        # Use anchor="ls" at baseline_y for consistent vertical position across all glyphs
        inactive_rgba = parse_color_rgba(style.text_color)
        stroke_rgba = parse_color_rgba(style.stroke_color)

        for wl in layout.words:
            # Skip active word – drawn cleanly in step 3 to prevent stroke bleed-through
            if wl.index == active_idx and pill_rect and opacity > 0.0:
                continue

            baseline = wl.baseline_y if wl.baseline_y is not None else wl.y

            if style.shadow > 0:
                draw.text(
                    (wl.x + style.shadow, baseline + style.shadow),
                    wl.text,
                    font=font,
                    anchor="ls",
                    fill=stroke_rgba,
                )

            if stroke_w > 0:
                draw.text(
                    (wl.x, baseline),
                    wl.text,
                    font=font,
                    anchor="ls",
                    fill=inactive_rgba,
                    stroke_width=int(stroke_w),
                    stroke_fill=stroke_rgba,
                )
            else:
                draw.text((wl.x, baseline), wl.text, font=font, anchor="ls", fill=inactive_rgba)

        # 3. Render Active Word cleanly on top of Pill (no prior stroke underneath to bleed through)
        if active_idx is not None and active_idx < len(layout.words) and pill_rect and opacity > 0.0:
            wl = layout.words[active_idx]
            baseline = wl.baseline_y if wl.baseline_y is not None else wl.y
            act_rgba = parse_color_rgba(active_text_color)
            fill_act = (act_rgba[0], act_rgba[1], act_rgba[2], int(act_rgba[3] * opacity))
            # Draw without stroke so active text colour is pure (pill background is the visual boundary)
            draw.text((wl.x, baseline), wl.text, font=font, anchor="ls", fill=fill_act)

        # 4. Render Debug Layout Boxes if enabled
        if config.debug_layout:
            debug_img = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))
            d_draw = ImageDraw.Draw(debug_img)

            # Draw Line boxes (Blue)
            lines_map: dict[int, list[WordLayout]] = {}
            for wl in layout.words:
                lines_map.setdefault(wl.line_index, []).append(wl)
            for l_words in lines_map.values():
                l_x = l_words[0].x
                l_y = l_words[0].y
                l_w = (l_words[-1].x + l_words[-1].width) - l_x
                l_h = l_words[0].height
                d_draw.rectangle([l_x, l_y, l_x + l_w, l_y + l_h], outline=(0, 0, 255, 255), width=2)

            # Draw Word layout boxes (Red)
            for wl in layout.words:
                d_draw.rectangle([wl.x, wl.y, wl.x + wl.width, wl.y + wl.height], outline=(255, 0, 0, 255), width=1)

            # Draw Pill rect (Green)
            if pill_rect:
                d_draw.rectangle(
                    [pill_rect.x, pill_rect.y, pill_rect.x + pill_rect.width, pill_rect.y + pill_rect.height],
                    outline=(0, 255, 0, 255),
                    width=2,
                )

            img = Image.alpha_composite(img, debug_img)

        return img

    def export_video_with_pill(
        self,
        video_info: VideoInfo,
        clips: list[SubtitleClip],
        style: SubtitleStyle,
        output_path: str | Path,
        word_timings: Optional[TimingFile] = None,
        cancel_event: Optional[threading.Event] = None,
        on_progress: Optional[Callable[[float], None]] = None,
        config: Optional[PillAnimationConfig] = None,
    ) -> Path:
        """
        Export video with animated pill subtitles using FFmpeg stdin rawvideo RGBA pipe.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            output_path.unlink()

        ffmpeg = get_ffmpeg()
        vw, vh = video_info.width, video_info.height
        fps = video_info.fps or 30.0
        duration = video_info.duration or 1.0
        total_frames = int(duration * fps)

        cmd = [
            ffmpeg,
            "-y",
            "-i", str(video_info.path),
            "-f", "rawvideo",
            "-pix_fmt", "rgba",
            "-s", f"{vw}x{vh}",
            "-r", str(fps),
            "-i", "pipe:0",
            "-filter_complex", "[0:v][1:v]overlay=0:0[v]",
            "-map", "[v]",
            "-map", "0:a?",
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
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
            )
        except FileNotFoundError as exc:
            raise FFmpegNotFoundError("ffmpeg binary not found.") from exc

        sorted_clips = sorted(clips, key=lambda c: c.start_ms)

        try:
            for frame_idx in range(total_frames):
                if cancel_event and cancel_event.is_set():
                    proc.kill()
                    proc.wait()
                    if output_path.exists():
                        output_path.unlink()
                    raise RuntimeError("Export cancelled by user.")

                time_ms = int(frame_idx / fps * 1000)

                active_clip = None
                clip_idx = None
                for idx, c in enumerate(sorted_clips):
                    if c.is_active_at(time_ms):
                        active_clip = c
                        clip_idx = idx
                        break

                line_t = word_timings.get_line(clip_idx) if (word_timings and clip_idx is not None) else None

                frame_img = self.render_frame(
                    clip=active_clip,
                    time_ms=time_ms,
                    style=style,
                    config=config,
                    line_timing=line_t,
                    video_width=vw,
                    video_height=vh,
                )

                proc.stdin.write(frame_img.tobytes())

                if on_progress and frame_idx % 10 == 0:
                    pct = min((frame_idx / total_frames) * 100.0, 99.9)
                    on_progress(pct)

            proc.stdin.close()
            proc.wait()
        except Exception as exc:
            proc.kill()
            if output_path.exists():
                output_path.unlink()
            raise RuntimeError(f"Pill export failed: {exc}") from exc

        if proc.returncode != 0:
            if output_path.exists():
                output_path.unlink()
            raise RuntimeError(f"FFmpeg process returned non-zero exit code {proc.returncode}")

        if on_progress:
            on_progress(100.0)

        return output_path.resolve()
