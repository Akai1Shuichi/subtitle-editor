"""
ass_builder.py
──────────────
Tạo file .ass với style Normal hoặc Word-Highlight (karaoke) từ SSAFile,
rồi lưu vào thư mục temp/ để FFmpeg đọc.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Literal

import pysubs2
from pysubs2 import Alignment


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

# Word-Highlight: giống Normal nhưng dùng karaoke tag \kf
HIGHLIGHT_STYLE = copy.deepcopy(NORMAL_STYLE)
HIGHLIGHT_STYLE.primarycolor = pysubs2.Color(255, 255, 255, 0)   # chưa highlight: trắng
HIGHLIGHT_STYLE.secondarycolor = pysubs2.Color(255, 200, 0, 0)   # highlight: vàng


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
) -> pysubs2.SSAFile:
    """
    Xây dựng SSAFile mới (định dạng ASS) từ `subs` gốc.

    Parameters
    ----------
    subs            : SSAFile đã load từ SRT
    mode            : "normal" hoặc "highlight"
    fontname        : tên font
    fontsize        : cỡ chữ (px)
    text_color      : màu RGB chính
    highlight_color : màu RGB khi highlight (chỉ dùng với mode="highlight")
    alignment       : ASS alignment (2 = bottom-center)
    margin_v        : lề dọc tính từ cạnh màn hình (px)
    """
    out = pysubs2.SSAFile()

    # Tạo style từ template
    style = copy.deepcopy(NORMAL_STYLE if mode == "normal" else HIGHLIGHT_STYLE)
    style.fontname = fontname
    style.fontsize = fontsize
    style.primarycolor = pysubs2.Color(*text_color, 0)
    style.secondarycolor = pysubs2.Color(*highlight_color, 0)
    style.alignment = Alignment(alignment) if isinstance(alignment, int) else alignment
    style.marginv = margin_v

    out.styles["Default"] = style
    out.info["ScaledBorderAndShadow"] = "yes"

    for event in subs.events:
        if not event.text.strip():
            continue

        new_event = copy.deepcopy(event)
        new_event.style = "Default"

        if mode == "highlight":
            new_event.text = _make_karaoke_text(event)
        else:
            new_event.text = _strip_srt_tags(event.text)

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
    import re
    return re.sub(r"<[^>]+>", "", text)


def _make_karaoke_text(event: pysubs2.SSAEvent) -> str:
    """
    Tạo text với hiệu ứng karaoke đơn giản:
    toàn bộ câu hiển thị màu trắng, rồi fill sang màu highlight
    theo thời lượng câu (dùng \\kf – fill karaoke).

    Khi có word-level timing thực sự, hàm này sẽ được thay bằng
    logic chia từng từ.
    """
    import re
    text = re.sub(r"<[^>]+>", "", event.text)
    words = text.split()
    if not words:
        return text

    duration_cs = (event.end - event.start) // 10  # centiseconds
    per_word_cs = max(1, duration_cs // len(words))

    parts = []
    remaining = duration_cs
    for i, word in enumerate(words):
        cs = per_word_cs if i < len(words) - 1 else remaining
        remaining -= cs
        parts.append(f"{{\\kf{cs}}}{word}")

    return " ".join(parts)
