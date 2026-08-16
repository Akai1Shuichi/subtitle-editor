"""
subtitle_parser.py
──────────────────
Đọc file .srt và chuyển sang pysubs2.SSAFile với style Normal hoặc Word-Highlight.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Callable

import pysubs2


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class SubtitleError(Exception):
    """Base class cho mọi lỗi subtitle."""


class EncodingError(SubtitleError):
    """File không phải UTF-8 hoặc không đọc được."""


class ParseError(SubtitleError):
    """File SRT sai định dạng hoặc rỗng."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_srt(path: str | Path) -> pysubs2.SSAFile:
    """
    Đọc file .srt, kiểm tra encoding UTF-8 và trả về SSAFile.

    Raises
    ------
    FileNotFoundError  – file không tồn tại
    EncodingError      – không phải UTF-8
    ParseError         – sai định dạng hoặc rỗng
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {path}")

    # Kiểm tra encoding
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig")  # utf-8-sig bỏ BOM nếu có
    except UnicodeDecodeError as exc:
        raise EncodingError(
            f"File '{path.name}' không phải UTF-8. "
            "Hãy mở file bằng Notepad và lưu lại với encoding UTF-8."
        ) from exc

    # Parse bằng pysubs2
    try:
        subs = pysubs2.SSAFile.from_string(text, format_="srt")
    except Exception as exc:
        raise ParseError(
            f"Không thể parse file SRT '{path.name}': {exc}"
        ) from exc

    if not subs.events:
        raise ParseError(f"File SRT '{path.name}' không có dòng subtitle nào.")

    return subs


def count_lines(subs: pysubs2.SSAFile) -> int:
    """Trả về số dòng subtitle hợp lệ (không rỗng)."""
    return sum(1 for e in subs.events if e.text.strip())
