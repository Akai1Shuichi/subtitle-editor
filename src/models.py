"""
src/models.py
─────────────
Domain models cho MVP2.

SubtitleClip   – đơn vị làm việc: một dòng subtitle với id, text, timing.
SubtitleStyle  – style toàn cục: font, màu, vị trí.
EditorProject  – single source of truth: video + clips + style.

Sau khi import SRT, editor làm việc hoàn toàn trên SubtitleClip[].
SRT KHÔNG được parse lại sau bước import.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

import pysubs2
from pysubs2 import Alignment

from .subtitle_parser import load_srt
from .ass_builder import SubtitleSettings, SubtitleRenderer
from .word_timing import TimingFile
from .video_info import VideoInfo


# ──────────────────────────────────────────────────────────────────────────────
# SubtitleClip
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class SubtitleClip:
    """
    Đại diện một dòng subtitle trong editor.

    id       : định danh duy nhất (uuid4 string) — dùng để track selection,
               drag, resize trên timeline.
    text     : nội dung văn bản (không có SRT/ASS tags).
    start_ms : thời điểm bắt đầu (milliseconds, >= 0).
    end_ms   : thời điểm kết thúc (milliseconds, > start_ms).
    """

    id: str
    text: str
    start_ms: int
    end_ms: int

    # ── Convenience ───────────────────────────────────────────────────────

    @property
    def duration_ms(self) -> int:
        return max(0, self.end_ms - self.start_ms)

    def is_active_at(self, time_ms: int) -> bool:
        """Trả về True nếu clip đang hiển thị tại thời điểm time_ms."""
        return self.start_ms <= time_ms < self.end_ms

    def __repr__(self) -> str:
        return (
            f"SubtitleClip(id={self.id[:8]}…, "
            f"start={self.start_ms}ms, end={self.end_ms}ms, "
            f"text={self.text[:20]!r})"
        )


# ──────────────────────────────────────────────────────────────────────────────
# SubtitleStyle
# ──────────────────────────────────────────────────────────────────────────────

StyleMode = Literal["normal", "highlight"]

@dataclass
class SubtitleStyle:
    """
    Style toàn cục của project.

    Dùng style_to_subtitle_settings() để chuyển sang SubtitleSettings (ass_builder).
    """

    mode: StyleMode = "normal"
    fontname: str = "Arial Black"
    fontsize: int = 54
    text_color: tuple[int, int, int] = (255, 255, 255)
    highlight_color: tuple[int, int, int] = (255, 217, 0)
    stroke_color: tuple[int, int, int] = (0, 0, 0)
    stroke_width: float = 4.0
    shadow: float = 2.0
    position_y: int = 82       # % từ trên, tương đương bottom: 18%
    alignment: int = 2         # pysubs2.Alignment value (2 = BOTTOM_CENTER)


# ──────────────────────────────────────────────────────────────────────────────
# EditorProject — single source of truth
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class EditorProject:
    """
    State trung tâm của editor.

    clips       : danh sách SubtitleClip — single source of truth cho
                  timeline, inspector, preview và export.
    style       : style toàn cục của project.
    video_info  : thông tin video (width, height, duration, fps, path).
    word_timings: timing từng từ (tùy chọn, dùng cho highlight mode export).
    """

    video_info: Optional[VideoInfo] = None
    clips: list[SubtitleClip] = field(default_factory=list)
    style: SubtitleStyle = field(default_factory=SubtitleStyle)
    word_timings: Optional[TimingFile] = None

    # ── Helpers ───────────────────────────────────────────────────────────

    @property
    def has_video(self) -> bool:
        return self.video_info is not None

    @property
    def has_clips(self) -> bool:
        return len(self.clips) > 0

    def active_clip_at(self, time_ms: int) -> Optional[SubtitleClip]:
        """Tìm clip đang hiển thị tại thời điểm time_ms."""
        for clip in self.clips:
            if clip.is_active_at(time_ms):
                return clip
        return None

    def clip_by_id(self, clip_id: str) -> Optional[SubtitleClip]:
        """Tìm clip theo id."""
        for clip in self.clips:
            if clip.id == clip_id:
                return clip
        return None

    def sorted_clips(self) -> list[SubtitleClip]:
        """Trả về clips sắp xếp theo start_ms."""
        return sorted(self.clips, key=lambda c: c.start_ms)


# ──────────────────────────────────────────────────────────────────────────────
# Helper: SRT → SubtitleClip[]
# ──────────────────────────────────────────────────────────────────────────────

import re as _re

def _strip_tags(text: str) -> str:
    """Xóa SRT/ASS inline tags khỏi text."""
    return _re.sub(r"<[^>]+>", "", text).strip()


def clips_from_srt(path: str | Path) -> list[SubtitleClip]:
    """
    Parse file SRT và trả về danh sách SubtitleClip.

    Chỉ gọi hàm này một lần khi import. Sau đó editor làm việc
    hoàn toàn trên SubtitleClip[] — không parse lại SRT nữa.

    Raises
    ------
    FileNotFoundError  – file không tồn tại
    EncodingError      – không phải UTF-8
    ParseError         – sai định dạng hoặc rỗng
    """
    subs = load_srt(path)
    clips: list[SubtitleClip] = []
    for event in subs.events:
        text = _strip_tags(event.text)
        if not text:
            continue
        clips.append(SubtitleClip(
            id=str(uuid.uuid4()),
            text=text,
            start_ms=event.start,
            end_ms=event.end,
        ))
    return clips


# ──────────────────────────────────────────────────────────────────────────────
# Helper: SubtitleStyle → SubtitleSettings (bridge sang ass_builder)
# ──────────────────────────────────────────────────────────────────────────────

def style_to_subtitle_settings(style: SubtitleStyle) -> SubtitleSettings:
    """
    Chuyển SubtitleStyle (domain model) sang SubtitleSettings (ass_builder).
    """
    return SubtitleSettings(
        fontname=style.fontname,
        fontsize=style.fontsize,
        text_color=style.text_color,
        highlight_color=style.highlight_color,
        stroke_color=style.stroke_color,
        stroke_width=style.stroke_width,
        shadow=style.shadow,
        position_y=style.position_y,
        alignment=Alignment(style.alignment),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Helper: SubtitleClip[] → pysubs2.SSAFile
# ──────────────────────────────────────────────────────────────────────────────

def clips_to_ssa(
    clips: list[SubtitleClip],
    style: SubtitleStyle,
    *,
    video_width: int = 0,
    video_height: int = 0,
    word_timings: Optional[TimingFile] = None,
) -> pysubs2.SSAFile:
    """
    Chuyển SubtitleClip[] + SubtitleStyle thành pysubs2.SSAFile
    sẵn sàng để build ASS và export.

    Preview và Export đều dùng hàm này từ cùng một nguồn dữ liệu.
    """
    # Chuyển clips sang SSAFile tạm để SubtitleRenderer xử lý
    raw = pysubs2.SSAFile()
    for clip in sorted(clips, key=lambda c: c.start_ms):
        raw.events.append(pysubs2.SSAEvent(
            start=clip.start_ms,
            end=clip.end_ms,
            text=clip.text,
        ))

    settings = style_to_subtitle_settings(style)
    renderer = SubtitleRenderer(settings, mode=style.mode)
    return renderer.build(
        raw,
        word_timings=word_timings,
        video_width=video_width,
        video_height=video_height,
    )
