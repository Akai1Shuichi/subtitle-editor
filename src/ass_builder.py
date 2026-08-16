"""
ass_builder.py
──────────────
Tạo file .ass với style Normal hoặc Word-Highlight (karaoke) từ SSAFile,
rồi lưu vào thư mục temp/ để FFmpeg đọc.

Hai chế độ highlight:
  - simple (sentence-level): cả câu fill màu highlight theo thời lượng câu,
    không cần word timing. Dùng 1 tag \\kf cho toàn câu.
  - per-word: mỗi từ có \\kf riêng dựa trên WordTiming chính xác.
    Yêu cầu truyền word_timings vào build_ass().
"""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Literal, Optional

import pysubs2
from pysubs2 import Alignment

from .word_timing import TimingFile, LineTiming


# ---------------------------------------------------------------------------
# Style definitions
# ---------------------------------------------------------------------------

# Normal: text trắng, outline tối, shadow nhẹ, căn đáy màn hình
NORMAL_STYLE = pysubs2.SSAStyle(
    fontname="Montserrat",
    fontsize=48,
    primarycolor=pysubs2.Color(255, 255, 255, 0),   # trắng, không trong suốt
    secondarycolor=pysubs2.Color(255, 255, 0, 0),   # vàng (dùng cho highlight)
    outlinecolor=pysubs2.Color(0, 0, 0, 0),          # outline đen
    backcolor=pysubs2.Color(0, 0, 0, 80),            # shadow bán trong suốt
    bold=False,
    italic=False,
    underline=False,
    scalex=100,
    scaley=100,
    spacing=0,
    angle=0.0,
    borderstyle=1,       # outline + shadow
    outline=2.5,         # độ dày outline
    shadow=1.5,          # shadow nhẹ
    alignment=Alignment.BOTTOM_CENTER,
    marginl=60,
    marginr=60,
    marginv=30,
    encoding=1,
)

# Word-Highlight: primarycolor = màu "chưa được fill" (trắng),
#                secondarycolor = màu fill karaoke (vàng).
# ASS: \kf "wipes" từ secondarycolor → primarycolor theo thời gian.
HIGHLIGHT_STYLE = copy.deepcopy(NORMAL_STYLE)
HIGHLIGHT_STYLE.primarycolor = pysubs2.Color(255, 255, 255, 0)   # sau khi fill: trắng
HIGHLIGHT_STYLE.secondarycolor = pysubs2.Color(255, 200, 0, 0)   # màu fill: vàng


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

StyleMode = Literal["normal", "highlight"]


def build_ass(
    subs: pysubs2.SSAFile,
    mode: StyleMode = "normal",
    *,
    fontname: str = "Montserrat",
    fontsize: int = 48,
    text_color: tuple[int, int, int] = (255, 255, 255),
    highlight_color: tuple[int, int, int] = (255, 200, 0),
    alignment: int | Alignment = Alignment.BOTTOM_CENTER,
    margin_v: int = 30,
    word_timings: Optional[TimingFile] = None,
) -> pysubs2.SSAFile:
    """
    Xây dựng SSAFile mới (định dạng ASS) từ `subs` gốc.

    Parameters
    ----------
    subs            : SSAFile đã load từ SRT
    mode            : "normal" hoặc "highlight"
    fontname        : tên font
    fontsize        : cỡ chữ (px)
    text_color      : màu RGB chính (màu text sau khi highlight)
    highlight_color : màu RGB fill karaoke (chỉ dùng với mode="highlight")
    alignment       : ASS alignment enum hoặc int (2 = bottom-center)
    margin_v        : lề dọc tính từ cạnh màn hình (px)
    word_timings    : TimingFile với per-word timing.
                      Nếu None và mode="highlight" → dùng simple sentence-level.
                      Nếu có → dùng per-word \\kf chính xác từng từ.
    """
    out = pysubs2.SSAFile()

    # Build style
    style = copy.deepcopy(NORMAL_STYLE if mode == "normal" else HIGHLIGHT_STYLE)
    style.fontname = fontname
    style.fontsize = fontsize
    style.primarycolor = pysubs2.Color(*text_color, 0)
    style.secondarycolor = pysubs2.Color(*highlight_color, 0)
    style.alignment = Alignment(alignment) if isinstance(alignment, int) else alignment
    style.marginv = margin_v

    out.styles["Default"] = style
    out.info["ScaledBorderAndShadow"] = "yes"

    for i, event in enumerate(subs.events):
        if not event.text.strip():
            continue

        new_event = copy.deepcopy(event)
        new_event.style = "Default"

        if mode == "normal":
            new_event.text = _strip_srt_tags(event.text)

        elif mode == "highlight":
            # Lấy LineTiming cho dòng này (nếu có)
            line_timing: Optional[LineTiming] = None
            if word_timings is not None:
                line_timing = word_timings.get_line(i)

            if line_timing is not None and line_timing.has_word_timing:
                # Per-word karaoke: timing chính xác từng từ
                new_event.text = _make_perword_karaoke(event, line_timing)
            else:
                # Simple sentence-level: cả câu fill theo thời lượng câu
                new_event.text = _make_sentence_karaoke(event)

        out.events.append(new_event)

    return out


def save_ass(ass: pysubs2.SSAFile, dest: str | Path) -> Path:
    """Lưu SSAFile ASS ra đĩa và trả về đường dẫn tuyệt đối."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    ass.save(str(dest))
    return dest.resolve()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _strip_srt_tags(text: str) -> str:
    """Bỏ các thẻ HTML đơn giản thường gặp trong SRT (<i>, <b>, <u>, <font ...>)."""
    return re.sub(r"<[^>]+>", "", text)


def _make_sentence_karaoke(event: pysubs2.SSAEvent) -> str:
    """
    Simple sentence-level highlight.

    Cả câu hiển thị với màu secondarycolor (fill color).
    Khi thời gian trong câu trôi qua, màu "wipes" từng từ sang primarycolor.
    Vì chỉ có 1 tag \\kf cho toàn câu → toàn câu chuyển màu cùng lúc khi hết thời gian.

    Hiệu ứng: câu xuất hiện màu highlight, sau khoảng thời gian đó đổi về màu trắng.

    Để dùng hiệu ứng "câu trắng, khi active fill vàng từng từ đều nhau",
    ta chia đều centiseconds cho từng từ (equal-weight per-word).
    """
    text = _strip_srt_tags(event.text)
    words = text.split()
    if not words:
        return text

    duration_cs = max(1, (event.end - event.start) // 10)
    per_word_cs = max(1, duration_cs // len(words))
    remainder = duration_cs - per_word_cs * (len(words) - 1)

    parts = []
    for i, word in enumerate(words):
        cs = remainder if i == len(words) - 1 else per_word_cs
        parts.append(f"{{\\kf{cs}}}{word}")

    return " ".join(parts)


def _make_perword_karaoke(
    event: pysubs2.SSAEvent,
    line_timing: LineTiming,
) -> str:
    """
    Per-word karaoke với timing chính xác từng từ.

    Mỗi từ có \\kf{cs} riêng dựa trên WordTiming.start_ms / end_ms.
    Các khoảng gap giữa các từ được gộp vào từ tiếp theo.

    Nếu số từ trong LineTiming không khớp với số từ trong event.text,
    fallback về sentence-level.
    """
    text = _strip_srt_tags(event.text)
    words_text = text.split()

    if len(words_text) != len(line_timing.words):
        # Số từ không khớp → fallback an toàn
        return _make_sentence_karaoke(event)

    parts = []
    for i, (word, timing) in enumerate(zip(words_text, line_timing.words)):
        cs = timing.duration_cs()
        parts.append(f"{{\\kf{cs}}}{word}")

    return " ".join(parts)
