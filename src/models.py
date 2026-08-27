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

import copy
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
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

    def to_dict(self) -> dict:
        """Chuyển SubtitleClip thành dict để serialize JSON."""
        return {
            "id": self.id,
            "text": self.text,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SubtitleClip:
        """Khôi phục SubtitleClip từ dict JSON."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            text=data.get("text", ""),
            start_ms=int(data.get("start_ms", 0)),
            end_ms=int(data.get("end_ms", 0)),
        )


# ──────────────────────────────────────────────────────────────────────────────
# SubtitleStyle
# ──────────────────────────────────────────────────────────────────────────────

StyleMode = Literal["normal", "highlight", "soft_pop", "soft-pop", "punch", "rise", "pill", "rounded_box", "rounded-box"]

@dataclass
class SubtitleStyle:
    """
    Style toàn cục của project.

    Dùng style_to_subtitle_settings() để chuyển sang SubtitleSettings (ass_builder).
    """

    mode: StyleMode = "normal"
    fontname: str = "Arial"
    fontsize: int = 54
    text_color: tuple[int, int, int] = (255, 255, 255)
    highlight_color: tuple[int, int, int] = (255, 217, 0)
    stroke_color: tuple[int, int, int] = (0, 0, 0)
    stroke_width: float = 1.0
    shadow: float = 2.0
    position_y: int = 90       # % từ trên, tương đương bottom: 10%
    alignment: int = 2         # pysubs2.Alignment value (2 = BOTTOM_CENTER)
    subtitle_width: int = 80   # % chiều rộng video, 30-100

    def to_dict(self) -> dict:
        """Chuyển SubtitleStyle thành dict để serialize JSON."""
        return {
            "mode": self.mode,
            "fontname": self.fontname,
            "fontsize": self.fontsize,
            "text_color": list(self.text_color),
            "highlight_color": list(self.highlight_color),
            "stroke_color": list(self.stroke_color),
            "stroke_width": self.stroke_width,
            "shadow": self.shadow,
            "position_y": self.position_y,
            "alignment": self.alignment,
            "subtitle_width": self.subtitle_width,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SubtitleStyle:
        """Khôi phục SubtitleStyle từ dict JSON."""
        def _to_tuple3(val, default: tuple[int, int, int]) -> tuple[int, int, int]:
            if isinstance(val, (list, tuple)) and len(val) == 3:
                return (int(val[0]), int(val[1]), int(val[2]))
            return default

        return cls(
            mode=data.get("mode", "normal"),
            fontname=data.get("fontname", "Arial"),
            fontsize=int(data.get("fontsize", 54)),
            text_color=_to_tuple3(data.get("text_color"), (255, 255, 255)),
            highlight_color=_to_tuple3(data.get("highlight_color"), (255, 217, 0)),
            stroke_color=_to_tuple3(data.get("stroke_color"), (0, 0, 0)),
            stroke_width=float(data.get("stroke_width", 1.0)),
            shadow=float(data.get("shadow", 2.0)),
            position_y=int(data.get("position_y", 90)),
            alignment=int(data.get("alignment", 2)),
            subtitle_width=int(data.get("subtitle_width", 80)),
        )


# ──────────────────────────────────────────────────────────────────────────────
# UndoManager (State Snapshot)
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ProjectSnapshot:
    clips: list[SubtitleClip]
    style: SubtitleStyle
    selected_clip_id: Optional[str] = None


class UndoManager:
    """Quản lý lịch sử Undo / Redo bằng State Snapshot siêu nhẹ."""

    def __init__(self, max_depth: int = 50):
        self.max_depth = max_depth
        self._undo_stack: list[ProjectSnapshot] = []
        self._redo_stack: list[ProjectSnapshot] = []

    def push_checkpoint(
        self,
        clips: list[SubtitleClip],
        style: SubtitleStyle,
        selected_clip_id: Optional[str] = None,
    ) -> None:
        """Lưu snapshot của trạng thái hiện tại trước khi thay đổi."""
        snapshot = ProjectSnapshot(
            clips=copy.deepcopy(clips),
            style=copy.deepcopy(style),
            selected_clip_id=selected_clip_id,
        )
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > self.max_depth:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def undo(
        self,
        current_clips: list[SubtitleClip],
        current_style: SubtitleStyle,
        current_selected_id: Optional[str] = None,
    ) -> Optional[ProjectSnapshot]:
        """Thực hiện Undo: lưu trạng thái hiện tại vào redo_stack và khôi phục trạng thái từ undo_stack."""
        if not self.can_undo():
            return None

        current_snapshot = ProjectSnapshot(
            clips=copy.deepcopy(current_clips),
            style=copy.deepcopy(current_style),
            selected_clip_id=current_selected_id,
        )
        self._redo_stack.append(current_snapshot)
        return self._undo_stack.pop()

    def redo(
        self,
        current_clips: list[SubtitleClip],
        current_style: SubtitleStyle,
        current_selected_id: Optional[str] = None,
    ) -> Optional[ProjectSnapshot]:
        """Thực hiện Redo: lưu trạng thái hiện tại vào undo_stack và khôi phục trạng thái từ redo_stack."""
        if not self.can_redo():
            return None

        current_snapshot = ProjectSnapshot(
            clips=copy.deepcopy(current_clips),
            style=copy.deepcopy(current_style),
            selected_clip_id=current_selected_id,
        )
        self._undo_stack.append(current_snapshot)
        return self._redo_stack.pop()


# ──────────────────────────────────────────────────────────────────────────────
# ProjectMetadata
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ProjectMetadata:
    """
    Thông tin tổng quan (metadata) của dự án.
    Dùng cho màn hình danh sách dự án (Project List / Dashboard).
    """

    project_id: str
    name: str
    created_at: str    # ISO format string (ví dụ: 2026-08-27T15:00:00)
    updated_at: str    # ISO format string
    video_path: str = ""
    thumbnail_path: str = ""
    duration_ms: int = 0
    clip_count: int = 0

    @property
    def is_example(self) -> bool:
        return self.project_id == "5f60564a-01bf-4280-8924-d96817b8541d"

    def to_dict(self) -> dict:
        """Chuyển ProjectMetadata thành dict sẵn sàng serialize JSON."""
        return {
            "project_id": self.project_id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "video_path": self.video_path,
            "thumbnail_path": self.thumbnail_path,
            "duration_ms": self.duration_ms,
            "clip_count": self.clip_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ProjectMetadata:
        """Tạo ProjectMetadata từ dict JSON."""
        return cls(
            project_id=data.get("project_id", str(uuid.uuid4())),
            name=data.get("name", "Untitled Project"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            video_path=data.get("video_path", ""),
            thumbnail_path=data.get("thumbnail_path", ""),
            duration_ms=int(data.get("duration_ms", 0)),
            clip_count=int(data.get("clip_count", 0)),
        )


# ──────────────────────────────────────────────────────────────────────────────
# EditorProject — single source of truth
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class EditorProject:
    """
    State trung tâm của editor.

    id          : định danh duy nhất của dự án (uuid string)
    name        : tên dự án
    clips       : danh sách SubtitleClip — single source of truth cho
                  timeline, inspector, preview và export.
    style       : style toàn cục của project.
    video_info  : thông tin video (width, height, duration, fps, path).
    word_timings: timing từng từ (tùy chọn, dùng cho highlight mode export).
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Untitled Project"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    thumbnail_path: str = ""

    video_info: Optional[VideoInfo] = None
    clips: list[SubtitleClip] = field(default_factory=list)
    style: SubtitleStyle = field(default_factory=SubtitleStyle)
    word_timings: Optional[TimingFile] = None
    undo_manager: UndoManager = field(default_factory=UndoManager)

    # ── Helpers ───────────────────────────────────────────────────────────

    def to_metadata(self) -> ProjectMetadata:
        """Tạo ProjectMetadata từ EditorProject hiện tại."""
        now_iso = datetime.now().isoformat()
        created = self.created_at or now_iso
        updated = self.updated_at or now_iso
        duration = int(self.video_info.duration * 1000) if self.video_info else 0
        v_path = str(self.video_info.path) if self.video_info and self.video_info.path else ""
        return ProjectMetadata(
            project_id=self.id,
            name=self.name,
            created_at=created,
            updated_at=updated,
            video_path=v_path,
            thumbnail_path=self.thumbnail_path,
            duration_ms=duration,
            clip_count=len(self.clips),
        )

    # ── Serialization / Deserialization ───────────────────────────────────

    def to_dict(self) -> dict:
        """Chuyển EditorProject thành dict sẵn sàng serialize JSON."""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "thumbnail_path": self.thumbnail_path,
            "video_info": self.video_info.to_dict() if self.video_info else None,
            "clips": [clip.to_dict() for clip in self.clips],
            "style": self.style.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> EditorProject:
        """Khôi phục EditorProject từ dict JSON."""
        v_info_data = data.get("video_info")
        video_info = VideoInfo.from_dict(v_info_data) if v_info_data else None
        clips = [SubtitleClip.from_dict(c) for c in data.get("clips", [])]
        style_data = data.get("style")
        style = SubtitleStyle.from_dict(style_data) if style_data else SubtitleStyle()

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "Untitled Project"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            thumbnail_path=data.get("thumbnail_path", ""),
            video_info=video_info,
            clips=clips,
            style=style,
        )

    def to_json(self, indent: int = 2) -> str:
        """Chuyển EditorProject sang chuỗi JSON."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> EditorProject:
        """Khôi phục EditorProject từ chuỗi JSON."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def save_to_file(self, path: str | Path) -> None:
        """Lưu EditorProject vào file dự án (.subproj / JSON)."""
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        self.updated_at = datetime.now().isoformat()
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.to_json())

    @classmethod
    def load_from_file(cls, path: str | Path) -> EditorProject:
        """Khôi phục EditorProject từ file dự án (.subproj / JSON)."""
        file_path = Path(path)
        with open(file_path, "r", encoding="utf-8") as f:
            return cls.from_json(f.read())

    def save_checkpoint(self, selected_clip_id: Optional[str] = None) -> None:
        """Lưu snapshot hiện tại vào undo stack."""
        self.undo_manager.push_checkpoint(self.clips, self.style, selected_clip_id)

    def undo(self, current_selected_id: Optional[str] = None) -> Optional[str]:
        """Thực hiện undo, trả về selected_clip_id đã khôi phục (nếu có)."""
        res = self.undo_manager.undo(self.clips, self.style, current_selected_id)
        if res is not None:
            self.clips = res.clips
            self.style = res.style
            return res.selected_clip_id
        return None

    def redo(self, current_selected_id: Optional[str] = None) -> Optional[str]:
        """Thực hiện redo, trả về selected_clip_id đã khôi phục (nếu có)."""
        res = self.undo_manager.redo(self.clips, self.style, current_selected_id)
        if res is not None:
            self.clips = res.clips
            self.style = res.style
            return res.selected_clip_id
        return None

    @property
    def has_video(self) -> bool:
        return self.video_info is not None

    @property
    def is_example(self) -> bool:
        return self.id == "5f60564a-01bf-4280-8924-d96817b8541d"

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

    def find_available_clip_range(
        self,
        current_time_ms: int,
        video_duration_ms: int = 0,
        desired_duration_ms: int = 2000,
        min_duration_ms: int = 200,
    ) -> Optional[tuple[int, int]]:
        """
        Tìm khoảng thời gian [start_ms, end_ms] trống phù hợp để chèn SubtitleClip mới.

        - Bắt đầu tìm từ current_time_ms.
        - Không đè (overlap) lên bất kỳ clip hiện có nào.
        - Giới hạn bởi 0 và video_duration_ms (nếu > 0).
        - Đảm bảo độ dài clip >= min_duration_ms và <= desired_duration_ms.

        Trả về (start_ms, end_ms) hoặc None nếu không còn khoảng trống nào hợp lệ.
        """
        max_bound = video_duration_ms if video_duration_ms > 0 else 999999999
        sorted_clips = self.sorted_clips()

        # Tạo danh sách các khoảng trống (gaps) [g_start, g_end]
        gaps: list[tuple[int, int]] = []
        curr_pos = 0
        for clip in sorted_clips:
            if clip.start_ms > curr_pos:
                gaps.append((curr_pos, clip.start_ms))
            curr_pos = max(curr_pos, clip.end_ms)

        if curr_pos < max_bound:
            gaps.append((curr_pos, max_bound))

        # 1. Thử tìm gap tại hoặc sau current_time_ms
        for g_start, g_end in gaps:
            if g_end <= current_time_ms:
                continue
            effective_start = max(current_time_ms, g_start)
            if g_end - effective_start >= min_duration_ms:
                new_start = effective_start
                new_end = min(effective_start + desired_duration_ms, g_end)
                return (new_start, new_end)

        # 2. Nếu không tìm thấy gap nào tại/sau current_time_ms, thử tìm gap trước current_time_ms
        for g_start, g_end in gaps:
            if g_end - g_start >= min_duration_ms:
                new_start = g_start
                new_end = min(g_start + desired_duration_ms, g_end)
                return (new_start, new_end)

        return None



# ──────────────────────────────────────────────────────────────────────────────
# Helper: SRT → SubtitleClip[]
# ──────────────────────────────────────────────────────────────────────────────

import re as _re

def _strip_tags(text: str) -> str:
    """Xóa SRT/ASS inline tags khỏi text và chuẩn hoá newline.

    pysubs2 chuyển newline SRT thành '\\N' (ASS soft newline) khi parse.
    Phải đổi '\\N' → '\\n' để hiển thị đúng ở mode normal.
    """
    # Xóa HTML/ASS inline tags như <b>, <i>, {\\an8}, v.v.
    text = _re.sub(r"<[^>]+>", "", text)
    text = _re.sub(r"\{[^}]*\}", "", text)
    # Chuẩn hoá ASS soft newline '\N' và hard newline '\n' → newline thực
    text = text.replace("\\N", "\n").replace("\\n", "\n")
    return text.strip()


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
        subtitle_width=style.subtitle_width,
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
