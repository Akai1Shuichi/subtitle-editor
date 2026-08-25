"""
src/presets/preview_generator.py
─────────────────────────────────
Generator preview GIF đơn giản: nền đen, text subtitle với word highlight.
Kích thước nhỏ (300x168 = 16:9) để fit card trong inspector.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from src.models import SubtitleClip, SubtitleStyle
from src.pill_renderer import (
    PillSubtitleRenderer,
    SubtitleWord,
    find_active_word,
    get_font,
    parse_color_rgba,
)
from src.video_info import get_ffmpeg


PREVIEW_TEXT = "phụ đề miễn phí"
PREVIEW_DIR = Path(__file__).parent.parent.parent / "data" / "preset_previews"

# Nhỏ gọn, 16:9, vừa card
PREV_W = 300
PREV_H = 168


def _render_highlight_frame(
    words_timing: list[SubtitleWord],
    layout,
    time_ms: int,
    style: SubtitleStyle,
    width: int,
    height: int,
) -> Image.Image:
    """Render một frame subtitle highlight lên nền trong suốt."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    if not layout or not layout.words:
        return img

    font = get_font(style.fontname, style.fontsize)
    draw = ImageDraw.Draw(img)

    active_idx = find_active_word(words_timing, time_ms, hold_during_gap=True)
    inactive_rgba = parse_color_rgba(style.text_color)
    highlight_rgba = parse_color_rgba(style.highlight_color)
    stroke_rgba = parse_color_rgba(style.stroke_color)
    stroke_w = int(style.stroke_width)

    for wl in layout.words:
        baseline = wl.baseline_y if wl.baseline_y is not None else wl.y
        color = highlight_rgba if wl.index == active_idx else inactive_rgba
        draw.text(
            (wl.x, baseline),
            wl.text,
            font=font,
            anchor="ls",
            fill=color,
            stroke_width=stroke_w,
            stroke_fill=stroke_rgba,
        )
    return img


def generate_highlight_preview(
    output_dir: str | Path = PREVIEW_DIR,
    width: int = PREV_W,
    height: int = PREV_H,
    fps: int = 12,
    duration_ms: int = 3000,
) -> tuple[Path, Path]:
    """
    Generate GIF preview cho mode highlight.
    Design đơn giản: nền đen, text white, active word vàng.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    gif_path = out_dir / "highlight.gif"
    mp4_path = out_dir / "highlight.mp4"

    clip = SubtitleClip(
        id="preview_highlight",
        text=PREVIEW_TEXT,
        start_ms=0,
        end_ms=duration_ms,
    )

    style = SubtitleStyle(
        mode="highlight",
        fontname="Arial Black",
        fontsize=22,
        text_color=(255, 255, 255),
        highlight_color=(255, 210, 60),   # vàng ấm
        stroke_color=(0, 0, 0),
        stroke_width=2.0,
        position_y=72,     # lower-center
        alignment=5,       # center
        subtitle_width=88,
    )

    # Build word timings (uniform distribution)
    renderer = PillSubtitleRenderer()
    words_timing: list[SubtitleWord] = renderer.extract_words_from_clip(clip)
    layout = renderer.prepare_layout(clip.text, style, width, height)

    # Background đơn giản: gần đen với gradient nhẹ
    bg_base = Image.new("RGBA", (width, height), (10, 11, 16, 255))
    draw_bg = ImageDraw.Draw(bg_base, "RGBA")
    # Subtle gradient từ trên xuống
    for y in range(height):
        t = y / height
        r = int(14 + 4 * t)
        g = int(16 + 4 * t)
        b = int(24 + 6 * t)
        draw_bg.line([(0, y), (width, y)], fill=(r, g, b, 255))

    total_frames = int((duration_ms / 1000.0) * fps)
    frames: list[Image.Image] = []
    raw_bytes: list[bytes] = []

    for i in range(total_frames):
        t_ms = int((i / fps) * 1000)
        frame = bg_base.copy()
        subtitle_layer = _render_highlight_frame(
            words_timing=words_timing,
            layout=layout,
            time_ms=t_ms,
            style=style,
            width=width,
            height=height,
        )
        frame.alpha_composite(subtitle_layer)
        frame_rgb = frame.convert("RGB")
        frames.append(frame_rgb)
        raw_bytes.append(frame.tobytes("raw", "RGBA"))

    # Save GIF
    if frames:
        frame_ms = int(1000 / fps)
        frames[0].save(
            gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=frame_ms,
            loop=0,
            optimize=True,
        )
        print(f"GIF saved: {gif_path}")

    # Save MP4
    try:
        ffmpeg = get_ffmpeg()
        cmd = [
            ffmpeg, "-y",
            "-f", "rawvideo", "-pix_fmt", "rgba",
            "-s", f"{width}x{height}",
            "-r", str(fps),
            "-i", "pipe:0",
            "-c:v", "libx264", "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(mp4_path),
        ]
        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        for b in raw_bytes:
            proc.stdin.write(b)
        proc.stdin.close()
        proc.wait()
        print(f"MP4 saved: {mp4_path}")
    except Exception as err:
        print(f"Warning: MP4 skipped ({err})")

    return mp4_path, gif_path


def generate_rise_preview(
    output_dir: str | Path = PREVIEW_DIR,
    width: int = PREV_W,
    height: int = PREV_H,
    fps: int = 12,
    duration_ms: int = 2600,
) -> tuple[Path, Path]:
    """
    Generate GIF preview cho mode Rise.
    Text trượt từ dưới lên (translateY) kết hợp fade-in,
    hold ở vị trí đúng, rồi fade-out nhẹ. Loop.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    gif_path = out_dir / "rise.gif"
    mp4_path = out_dir / "rise.mp4"

    clip = SubtitleClip(
        id="preview_rise",
        text=PREVIEW_TEXT,
        start_ms=0,
        end_ms=duration_ms,
    )

    style = SubtitleStyle(
        mode="rise",
        fontname="Arial Black",
        fontsize=22,
        text_color=(255, 255, 255),
        highlight_color=(255, 210, 60),
        stroke_color=(0, 0, 0),
        stroke_width=2.0,
        position_y=72,
        alignment=5,
        subtitle_width=88,
    )

    renderer = PillSubtitleRenderer()
    layout = renderer.prepare_layout(clip.text, style, width, height)
    font = get_font(style.fontname, style.fontsize)
    stroke_rgba = parse_color_rgba(style.stroke_color)
    text_rgba = parse_color_rgba(style.text_color)
    stroke_w = int(style.stroke_width)

    # Background
    bg_base = Image.new("RGBA", (width, height), (10, 11, 16, 255))
    draw_bg = ImageDraw.Draw(bg_base, "RGBA")
    for y in range(height):
        t = y / height
        r = int(14 + 4 * t)
        g = int(16 + 4 * t)
        b = int(24 + 6 * t)
        draw_bg.line([(0, y), (width, y)], fill=(r, g, b, 255))

    total_frames = int((duration_ms / 1000.0) * fps)
    frames: list[Image.Image] = []
    raw_bytes: list[bytes] = []

    SLIDE_PX = 18   # pixels trượt lên
    FADE_IN  = 0.30  # 0→30% = rise + fade in
    HOLD     = 0.68  # 30→68% = hold
    FADE_OUT = 1.00  # 68→100% = fade out nhẹ

    def ease_out(t: float) -> float:
        return 1.0 - (1.0 - t) ** 2.5

    for i in range(total_frames):
        t_norm = i / max(total_frames - 1, 1)

        if t_norm < FADE_IN:
            p = ease_out(t_norm / FADE_IN)
            alpha = int(255 * p)
            offset_y = int(SLIDE_PX * (1.0 - p))
        elif t_norm < HOLD:
            alpha = 255
            offset_y = 0
        else:
            p = (t_norm - HOLD) / (FADE_OUT - HOLD)
            alpha = int(255 * (1.0 - p ** 1.5))
            offset_y = 0
        alpha = max(0, min(255, alpha))

        frame = bg_base.copy()

        # Render text với offset Y
        text_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw_t = ImageDraw.Draw(text_layer)
        for wl in layout.words:
            baseline = (wl.baseline_y if wl.baseline_y is not None else wl.y) + offset_y
            draw_t.text(
                (wl.x, baseline),
                wl.text,
                font=font,
                anchor="ls",
                fill=text_rgba,
                stroke_width=stroke_w,
                stroke_fill=stroke_rgba,
            )

        # Apply alpha fade
        r_ch, g_ch, b_ch, a_ch = text_layer.split()
        a_ch = a_ch.point(lambda p: int(p * alpha / 255))
        text_layer = Image.merge("RGBA", (r_ch, g_ch, b_ch, a_ch))
        frame.alpha_composite(text_layer)

        frame_rgb = frame.convert("RGB")
        frames.append(frame_rgb)
        raw_bytes.append(frame.tobytes("raw", "RGBA"))

    if frames:
        frame_ms = int(1000 / fps)
        frames[0].save(
            gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=frame_ms,
            loop=0,
            optimize=True,
        )
        print(f"GIF saved: {gif_path}")

    try:
        ffmpeg = get_ffmpeg()
        cmd = [
            ffmpeg, "-y",
            "-f", "rawvideo", "-pix_fmt", "rgba",
            "-s", f"{width}x{height}",
            "-r", str(fps),
            "-i", "pipe:0",
            "-c:v", "libx264", "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(mp4_path),
        ]
        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        for b in raw_bytes:
            proc.stdin.write(b)
        proc.stdin.close()
        proc.wait()
        print(f"MP4 saved: {mp4_path}")
    except Exception as err:
        print(f"Warning: MP4 skipped ({err})")

    return mp4_path, gif_path


if __name__ == "__main__":
    # print("=== Generating Highlight preview ===")
    # generate_highlight_preview()

    print("\n=== Generating Rise preview ===")
    generate_rise_preview()

    print("\nAll done!")
