"""
src/presets/preview_generator.py
─────────────────────────────────
Generator preview GIF đơn giản: nền đen, text subtitle với word highlight.
Kích thước nhỏ (300x168 = 16:9) để fit card trong inspector.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from src.models import SubtitleClip, SubtitleStyle
from src.pill_renderer import (
    PillSubtitleRenderer,
    PillAnimationConfig,
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
        extra_kwargs = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)} if sys.platform == "win32" else {}
        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            **extra_kwargs,
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
        extra_kwargs = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)} if sys.platform == "win32" else {}
        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            **extra_kwargs,
        )
        for b in raw_bytes:
            proc.stdin.write(b)
        proc.stdin.close()
        proc.wait()
        print(f"MP4 saved: {mp4_path}")
    except Exception as err:
        print(f"Warning: MP4 skipped ({err})")

    return mp4_path, gif_path


    return mp4_path, gif_path


def generate_soft_pop_preview(
    output_dir: str | Path = PREVIEW_DIR,
    width: int = PREV_W,
    height: int = PREV_H,
    fps: int = 12,
    duration_ms: int = 2400,
) -> tuple[Path, Path]:
    """
    Generate GIF preview cho mode Soft Pop.
    Phrase pop nhẹ (scale 0.92 -> 1.04 -> 1.0) kèm fade-in, hold, fade-out. Loop.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    gif_path = out_dir / "soft_pop.gif"
    mp4_path = out_dir / "soft_pop.mp4"

    clip = SubtitleClip(
        id="preview_soft_pop",
        text=PREVIEW_TEXT,
        start_ms=0,
        end_ms=duration_ms,
    )

    style = SubtitleStyle(
        mode="soft_pop",
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

    # Render static text onto a transparent layer
    text_base = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw_t = ImageDraw.Draw(text_base)
    for wl in layout.words:
        baseline = wl.baseline_y if wl.baseline_y is not None else wl.y
        draw_t.text(
            (wl.x, baseline),
            wl.text,
            font=font,
            anchor="ls",
            fill=text_rgba,
            stroke_width=stroke_w,
            stroke_fill=stroke_rgba,
        )

    # Background
    bg_base = Image.new("RGBA", (width, height), (10, 11, 16, 255))
    draw_bg = ImageDraw.Draw(bg_base, "RGBA")
    for y in range(height):
        t = y / height
        r = int(14 + 4 * t)
        g = int(16 + 4 * t)
        b = int(24 + 6 * t)
        draw_bg.line([(0, y)], fill=(r, g, b, 255))

    total_frames = int((duration_ms / 1000.0) * fps)
    frames: list[Image.Image] = []
    raw_bytes: list[bytes] = []

    # Center of text phrase for scaling
    cx = width / 2.0
    cy = layout.words[0].baseline_y if (layout.words and layout.words[0].baseline_y) else height * 0.72

    for i in range(total_frames):
        t_norm = i / max(total_frames - 1, 1)

        # Scale & Alpha keyframes:
        # 0.0 -> 0.12: scale 0.90 -> 1.05, alpha 0 -> 255
        # 0.12 -> 0.22: scale 1.05 -> 1.00, alpha 255
        # 0.22 -> 0.72: scale 1.00, alpha 255
        # 0.72 -> 1.00: scale 1.00 -> 0.95, alpha 255 -> 0
        if t_norm < 0.12:
            p = t_norm / 0.12
            scale = 0.90 + 0.15 * p
            alpha = int(255 * p)
        elif t_norm < 0.22:
            p = (t_norm - 0.12) / 0.10
            scale = 1.05 - 0.05 * p
            alpha = 255
        elif t_norm < 0.72:
            scale = 1.0
            alpha = 255
        else:
            p = (t_norm - 0.72) / 0.28
            scale = 1.0 - 0.05 * p
            alpha = int(255 * (1.0 - p))

        alpha = max(0, min(255, alpha))

        frame = bg_base.copy()

        if scale != 1.0 and scale > 0.1:
            sw = int(width * scale)
            sh = int(height * scale)
            scaled_txt = text_base.resize((sw, sh), Image.Resampling.BILINEAR)

            # Center align scaled image
            scaled_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            offset_x = int(cx - (cx * scale))
            offset_y = int(cy - (cy * scale))
            scaled_layer.paste(scaled_txt, (offset_x, offset_y), scaled_txt)
            text_frame = scaled_layer
        else:
            text_frame = text_base.copy()

        # Apply alpha
        r_ch, g_ch, b_ch, a_ch = text_frame.split()
        a_ch = a_ch.point(lambda p: int(p * alpha / 255))
        text_frame = Image.merge("RGBA", (r_ch, g_ch, b_ch, a_ch))
        frame.alpha_composite(text_frame)

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
        extra_kwargs = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)} if sys.platform == "win32" else {}
        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            **extra_kwargs,
        )
        for b in raw_bytes:
            proc.stdin.write(b)
        proc.stdin.close()
        proc.wait()
        print(f"MP4 saved: {mp4_path}")
    except Exception as err:
        print(f"Warning: MP4 skipped ({err})")

    return mp4_path, gif_path


def generate_pill_preview(
    output_dir: str | Path = PREVIEW_DIR,
    width: int = PREV_W,
    height: int = PREV_H,
    fps: int = 15,
    duration_ms: int = 3000,
) -> tuple[Path, Path]:
    """
    Generate GIF preview cho mode Pill.
    Nền capsule màu vàng di chuyển mượt giữa các từ.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    gif_path = out_dir / "pill.gif"
    mp4_path = out_dir / "pill.mp4"

    clip = SubtitleClip(
        id="preview_pill",
        text=PREVIEW_TEXT,
        start_ms=0,
        end_ms=duration_ms,
    )

    style = SubtitleStyle(
        mode="pill",
        fontname="Arial Black",
        fontsize=22,
        text_color=(255, 255, 255),
        highlight_color=(255, 210, 60),
        stroke_color=(0, 0, 0),
        stroke_width=0.0,
        position_y=72,
        alignment=5,
        subtitle_width=88,
    )

    renderer = PillSubtitleRenderer()

    # Background
    bg_base = Image.new("RGBA", (width, height), (10, 11, 16, 255))
    draw_bg = ImageDraw.Draw(bg_base, "RGBA")
    for y in range(height):
        t = y / height
        r = int(14 + 4 * t)
        g = int(16 + 4 * t)
        b = int(24 + 6 * t)
        draw_bg.line([(0, y)], fill=(r, g, b, 255))

    total_frames = int((duration_ms / 1000.0) * fps)
    frames: list[Image.Image] = []
    raw_bytes: list[bytes] = []

    config = PillAnimationConfig(
        highlight_color="#FFD249",
        padding_x=4,
        padding_y=2,
        radius=5,
        bg_opacity=1.0,
    )

    for i in range(total_frames):
        t_ms = int((i / fps) * 1000)
        frame = bg_base.copy()

        pill_layer = renderer.render_frame(
            clip=clip,
            time_ms=t_ms,
            style=style,
            config=config,
            video_width=width,
            video_height=height,
        )
        frame.alpha_composite(pill_layer)

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
        extra_kwargs = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)} if sys.platform == "win32" else {}
        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            **extra_kwargs,
        )
        for b in raw_bytes:
            proc.stdin.write(b)
        proc.stdin.close()
        proc.wait()
        print(f"MP4 saved: {mp4_path}")
    except Exception as err:
        print(f"Warning: MP4 skipped ({err})")

    return mp4_path, gif_path


def generate_punch_preview(
    output_dir: str | Path = PREVIEW_DIR,
    width: int = PREV_W,
    height: int = PREV_H,
    fps: int = 15,
    duration_ms: int = 2800,
) -> tuple[Path, Path]:
    """
    Generate GIF preview cho mode Punch.
    Từ đang phát phóng nhẹ (scale ≈ 1.18) rồi trở về kích thước ban đầu theo nhịp.
    """
    import math

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    gif_path = out_dir / "punch.gif"
    mp4_path = out_dir / "punch.mp4"

    clip = SubtitleClip(
        id="preview_punch",
        text=PREVIEW_TEXT,
        start_ms=0,
        end_ms=duration_ms,
    )

    style = SubtitleStyle(
        mode="punch",
        fontname="Arial Black",
        fontsize=22,
        text_color=(230, 230, 230),
        highlight_color=(255, 215, 60),
        stroke_color=(0, 0, 0),
        stroke_width=2.0,
        position_y=72,
        alignment=5,
        subtitle_width=88,
    )

    renderer = PillSubtitleRenderer()
    words_timing: list[SubtitleWord] = renderer.extract_words_from_clip(clip)
    layout = renderer.prepare_layout(clip.text, style, width, height)

    font = get_font(style.fontname, style.fontsize)
    inactive_rgba = parse_color_rgba(style.text_color)
    highlight_rgba = parse_color_rgba(style.highlight_color)
    stroke_rgba = parse_color_rgba(style.stroke_color)
    stroke_w = int(style.stroke_width)

    # Background
    bg_base = Image.new("RGBA", (width, height), (10, 11, 16, 255))
    draw_bg = ImageDraw.Draw(bg_base, "RGBA")
    for y in range(height):
        t = y / height
        r = int(14 + 4 * t)
        g = int(16 + 4 * t)
        b = int(24 + 6 * t)
        draw_bg.line([(0, y)], fill=(r, g, b, 255))

    total_frames = int((duration_ms / 1000.0) * fps)
    frames: list[Image.Image] = []
    raw_bytes: list[bytes] = []

    for i in range(total_frames):
        t_ms = int((i / fps) * 1000)
        frame = bg_base.copy()
        layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))

        active_idx = find_active_word(words_timing, t_ms, hold_during_gap=True)

        for wl in layout.words:
            baseline = wl.baseline_y if wl.baseline_y is not None else wl.y

            if wl.index == active_idx and active_idx is not None and active_idx < len(words_timing):
                w_timing = words_timing[active_idx]
                w_dur = max(1, w_timing.end_ms - w_timing.start_ms)
                w_t = (t_ms - w_timing.start_ms) / w_dur

                # Punch curve: 0 -> 0.3 (scale 1 -> 1.18), 0.3 -> 0.6 (scale 1.18 -> 1.0)
                if w_t < 0.30:
                    p = w_t / 0.30
                    scale = 1.0 + 0.18 * math.sin(p * math.pi / 2.0)
                elif w_t < 0.60:
                    p = (w_t - 0.30) / 0.30
                    scale = 1.18 - 0.18 * math.sin(p * math.pi / 2.0)
                else:
                    scale = 1.0

                # Render active word on temporary surface to apply scale transform around center
                word_w = int(wl.width + stroke_w * 4 + 16)
                word_h = int(wl.height + stroke_w * 4 + 16)
                word_img = Image.new("RGBA", (word_w, word_h), (0, 0, 0, 0))
                draw_w = ImageDraw.Draw(word_img)

                draw_w.text(
                    (word_w / 2.0, word_h * 0.7),
                    wl.text,
                    font=font,
                    anchor="ms",
                    fill=highlight_rgba,
                    stroke_width=stroke_w,
                    stroke_fill=stroke_rgba,
                )

                if scale != 1.0:
                    sw = max(1, int(word_w * scale))
                    sh = max(1, int(word_h * scale))
                    word_img = word_img.resize((sw, sh), Image.Resampling.BILINEAR)

                # Paste scaled active word centered at original word position
                pos_x = int(wl.x + wl.width / 2.0 - word_img.width / 2.0)
                pos_y = int(baseline - word_h * 0.7 + (word_h - word_img.height) / 2.0)
                layer.paste(word_img, (pos_x, pos_y), word_img)

            else:
                draw_l = ImageDraw.Draw(layer)
                draw_l.text(
                    (wl.x, baseline),
                    wl.text,
                    font=font,
                    anchor="ls",
                    fill=inactive_rgba,
                    stroke_width=stroke_w,
                    stroke_fill=stroke_rgba,
                )

        frame.alpha_composite(layer)
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
        extra_kwargs = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)} if sys.platform == "win32" else {}
        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            **extra_kwargs,
        )
        for b in raw_bytes:
            proc.stdin.write(b)
        proc.stdin.close()
        proc.wait()
        print(f"MP4 saved: {mp4_path}")
    except Exception as err:
        print(f"Warning: MP4 skipped ({err})")

    return mp4_path, gif_path


def generate_rounded_box_preview(
    output_dir: str | Path = PREVIEW_DIR,
    width: int = PREV_W,
    height: int = PREV_H,
    fps: int = 12,
    duration_ms: int = 2400,
) -> tuple[Path, Path]:
    """
    Generate GIF preview cho mode Rounded Box / Caption Card.
    Visual theo docs: Background màu vàng sáng (#FFD900), chữ màu đen (#111111),
    bo góc lớn (rounded box), không stroke, căn giữa, hiển thị dạng SHOW -> HOLD -> HIDE.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    gif_path = out_dir / "rounded_box.gif"
    mp4_path = out_dir / "rounded_box.mp4"

    clip = SubtitleClip(
        id="preview_rounded_box",
        text=PREVIEW_TEXT,
        start_ms=0,
        end_ms=duration_ms,
    )

    style = SubtitleStyle(
        mode="rounded_box",
        fontname="Arial Black",
        fontsize=22,
        text_color=(17, 17, 17),
        highlight_color=(17, 17, 17),
        stroke_color=(0, 0, 0),
        stroke_width=0.0,
        position_y=72,
        alignment=5,
        subtitle_width=88,
    )

    renderer = PillSubtitleRenderer()
    layout = renderer.prepare_layout(clip.text, style, width, height)
    font = get_font(style.fontname, style.fontsize)
    text_rgba = (17, 17, 17, 255)

    # Background canvas
    bg_base = Image.new("RGBA", (width, height), (10, 11, 16, 255))
    draw_bg = ImageDraw.Draw(bg_base, "RGBA")
    for y in range(height):
        t = y / height
        r = int(14 + 4 * t)
        g = int(16 + 4 * t)
        b = int(24 + 6 * t)
        draw_bg.line([(0, y)], fill=(r, g, b, 255))

    # Compute bounding box for caption card
    if layout.words:
        min_x = min(wl.x for wl in layout.words) - 14
        max_x = max(wl.x + wl.width for wl in layout.words) + 14
        min_y = min(wl.y for wl in layout.words) - 6
        max_y = max(wl.y + wl.height for wl in layout.words) + 6
    else:
        min_x, min_y, max_x, max_y = 20, height * 0.6, width - 20, height * 0.8

    box_rect = [min_x, min_y, max_x, max_y]

    # Static caption card layer: Bright Yellow background + dark text
    card_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw_c = ImageDraw.Draw(card_layer, "RGBA")

    # Yellow background box #FFD900
    draw_c.rounded_rectangle(
        box_rect,
        radius=12,
        fill=(255, 217, 0, 255),
    )

    # Dark text inside yellow box
    for wl in layout.words:
        baseline = wl.baseline_y if wl.baseline_y is not None else wl.y
        draw_c.text(
            (wl.x, baseline),
            wl.text,
            font=font,
            anchor="ls",
            fill=text_rgba,
        )

    # Loop frames: SHOW -> HOLD -> HIDE
    total_frames = int((duration_ms / 1000.0) * fps)
    frames: list[Image.Image] = []
    raw_bytes: list[bytes] = []

    for i in range(total_frames):
        t_norm = i / max(total_frames - 1, 1)

        if t_norm < 0.15:
            alpha = int(255 * (t_norm / 0.15))
        elif t_norm < 0.78:
            alpha = 255
        else:
            alpha = int(255 * (1.0 - (t_norm - 0.78) / 0.22))

        alpha = max(0, min(255, alpha))

        frame = bg_base.copy()

        faded_card = card_layer.copy()
        r_ch, g_ch, b_ch, a_ch = faded_card.split()
        a_ch = a_ch.point(lambda p: int(p * alpha / 255))
        faded_card = Image.merge("RGBA", (r_ch, g_ch, b_ch, a_ch))
        frame.alpha_composite(faded_card)

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
        extra_kwargs = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)} if sys.platform == "win32" else {}
        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            **extra_kwargs,
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
    print("=== Generating Preset Previews ===")
    # generate_highlight_preview()
    # generate_rise_preview()
    # generate_soft_pop_preview()
    # generate_pill_preview()
    # generate_punch_preview()
    generate_rounded_box_preview()

