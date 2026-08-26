"""
src/ui/timeline_widget.py
───────────────────────────
Interactive Subtitle Timeline Widget cho Subtitle Editor.

Tính năng:
- Thước thời gian (Ruler) hiển thị mốc giây/phút linh hoạt theo mức zoom.
- Vạch thời gian (Playhead) màu đỏ nổi bật, hiển thị vị trí video hiện tại.
- Render danh sách SubtitleClip dưới dạng các khối clip trên track subtitle.
- Tương tác chuột trực tiếp:
  * Click trên Ruler / Canvas để seek video (seek_requested).
  * Click clip để chọn (clip_selected / clip_deselected).
  * Kéo giữa clip để di chuyển (cập nhật đồng thời start_ms và end_ms).
  * Kéo mép trái để resize start_ms (với con trỏ QCursor(SizeHorCursor)).
  * Kéo mép phải để resize end_ms (với con trỏ QCursor(SizeHorCursor)).
  * Ràng buộc: start_ms >= 0, end_ms > start_ms (min 100ms), không vượt video_duration.
- Nút Zoom in / Zoom out và điều khiển playback.

Signals
-------
clip_selected(clip_id: str)
clip_deselected()
clip_timing_changed(clip_id: str, start_ms: int, end_ms: int)
add_subtitle_requested()
play_pause_requested()
seek_requested(ms: int)
"""

from __future__ import annotations

import math
from PySide6.QtCore import QPoint, QRect, QRectF, Qt, Signal, Slot
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QFont,
    QFontMetrics,
    QIcon,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..models import SubtitleClip


# ──────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────
RULER_HEIGHT = 28
CLIP_TRACK_TOP = 34
CLIP_HEIGHT = 42
TRACK_TOTAL_HEIGHT = 90
HANDLE_WIDTH = 8
MIN_CLIP_DURATION = 100  # ms


# ──────────────────────────────────────────────────────────────────────────
# Timeline Canvas Sub-widget
# ──────────────────────────────────────────────────────────────────────────

class _TimelineCanvas(QWidget):
    """
    Vùng vẽ chính của Timeline:
    - Thước thời gian
    - Track clips & handles drag/resize
    - Playhead line
    """

    clip_selected = Signal(str)
    clip_deselected = Signal()
    clip_timing_changed = Signal(str, int, int)  # clip_id, start_ms, end_ms
    seek_requested = Signal(int)  # ms

    # Drag modes
    MODE_NONE = 0
    MODE_SEEK = 1
    MODE_MOVE = 2
    MODE_RESIZE_LEFT = 3
    MODE_RESIZE_RIGHT = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFixedHeight(TRACK_TOTAL_HEIGHT)

        self._clips: list[SubtitleClip] = []
        self._selected_clip_id: str | None = None
        self._current_time_ms: int = 0
        self._duration_ms: int = 60000  # Default 1 min
        self._px_per_sec: float = 50.0  # Zoom ratio (50px = 1 sec)

        # Drag state
        self._drag_mode = self.MODE_NONE
        self._drag_clip_id: str | None = None
        self._drag_start_x: int = 0
        self._drag_orig_start_ms: int = 0
        self._drag_orig_end_ms: int = 0

        self.update_canvas_size()

    # ──────────────────────────────────────────────────────────────────────
    # Converters
    # ──────────────────────────────────────────────────────────────────────

    def ms_to_px(self, ms: int) -> float:
        return (ms / 1000.0) * self._px_per_sec

    def px_to_ms(self, px: float) -> int:
        return max(0, round((px / self._px_per_sec) * 1000.0))

    def update_canvas_size(self) -> None:
        duration_sec = max(10, self._duration_ms / 1000.0)
        content_width = int(duration_sec * self._px_per_sec) + 200
        self.setFixedWidth(max(content_width, 800))
        self.update()

    # ──────────────────────────────────────────────────────────────────────
    # Data Setters
    # ──────────────────────────────────────────────────────────────────────

    def set_data(
        self,
        clips: list[SubtitleClip],
        selected_clip_id: str | None,
        current_time_ms: int,
        duration_ms: int,
        px_per_sec: float,
    ) -> None:
        self._clips = clips
        self._selected_clip_id = selected_clip_id
        self._current_time_ms = current_time_ms
        if duration_ms > 0:
            self._duration_ms = duration_ms
        self._px_per_sec = px_per_sec
        self.update_canvas_size()

    # ──────────────────────────────────────────────────────────────────────
    # Geometry Helpers
    # ──────────────────────────────────────────────────────────────────────

    def get_clip_rect(self, clip: SubtitleClip) -> QRectF:
        x = self.ms_to_px(clip.start_ms)
        w = max(20.0, self.ms_to_px(clip.duration_ms))
        return QRectF(x, CLIP_TRACK_TOP, w, CLIP_HEIGHT)

    def find_clip_at(self, pos: QPoint) -> tuple[SubtitleClip | None, int]:
        """
        Trả về (clip, handle_type) tại vị trí pos.
        handle_type: MODE_MOVE, MODE_RESIZE_LEFT, MODE_RESIZE_RIGHT hoặc MODE_NONE
        """
        for clip in reversed(self._clips):
            rect = self.get_clip_rect(clip)
            if rect.contains(pos):
                left_handle = QRectF(rect.left(), rect.top(), HANDLE_WIDTH, rect.height())
                right_handle = QRectF(rect.right() - HANDLE_WIDTH, rect.top(), HANDLE_WIDTH, rect.height())
                
                if left_handle.contains(pos):
                    return clip, self.MODE_RESIZE_LEFT
                elif right_handle.contains(pos):
                    return clip, self.MODE_RESIZE_RIGHT
                else:
                    return clip, self.MODE_MOVE
        return None, self.MODE_NONE

    # ──────────────────────────────────────────────────────────────────────
    # Mouse Events
    # ──────────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.LeftButton:
            return

        self.setFocus()
        pos = event.pos()

        # Click trên Ruler (top area)
        if pos.y() <= RULER_HEIGHT:
            self._drag_mode = self.MODE_SEEK
            target_ms = self.px_to_ms(pos.x())
            self.seek_requested.emit(target_ms)
            return

        # Click trên Clip track
        clip, handle_type = self.find_clip_at(pos)
        if clip:
            self._drag_mode = handle_type
            self._drag_clip_id = clip.id
            self._drag_start_x = pos.x()
            self._drag_orig_start_ms = clip.start_ms
            self._drag_orig_end_ms = clip.end_ms

            if clip.id != self._selected_clip_id:
                self._selected_clip_id = clip.id
                self.clip_selected.emit(clip.id)

            # Seek video tới vị trí click khi chọn clip
            seek_ms = self.px_to_ms(pos.x())
            self.seek_requested.emit(seek_ms)
        else:
            # Click trên vùng trống track -> Deselect & Seek
            if self._selected_clip_id is not None:
                self._selected_clip_id = None
                self.clip_deselected.emit()

            self._drag_mode = self.MODE_SEEK
            target_ms = self.px_to_ms(pos.x())
            self.seek_requested.emit(target_ms)

        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.pos()

        # Update Mouse Cursor khi hover trên handles
        if self._drag_mode == self.MODE_NONE:
            if pos.y() > RULER_HEIGHT:
                clip, handle_type = self.find_clip_at(pos)
                if handle_type in (self.MODE_RESIZE_LEFT, self.MODE_RESIZE_RIGHT):
                    self.setCursor(QCursor(Qt.SizeHorCursor))
                elif handle_type == self.MODE_MOVE:
                    self.setCursor(QCursor(Qt.PointingHandCursor))
                else:
                    self.setCursor(QCursor(Qt.ArrowCursor))
            else:
                self.setCursor(QCursor(Qt.PointingHandCursor))
            return

        # Handle Dragging
        delta_x = pos.x() - self._drag_start_x
        delta_ms = round((delta_x / self._px_per_sec) * 1000.0)

        if self._drag_mode == self.MODE_SEEK:
            target_ms = self.px_to_ms(pos.x())
            self.seek_requested.emit(target_ms)

        elif self._drag_mode in (self.MODE_MOVE, self.MODE_RESIZE_LEFT, self.MODE_RESIZE_RIGHT) and self._drag_clip_id:
            # Tìm ranh giới clip trước và clip sau dựa theo vị trí ban đầu
            other_clips = [c for c in self._clips if c.id != self._drag_clip_id]
            prev_clips = [c for c in other_clips if c.end_ms <= self._drag_orig_start_ms]
            next_clips = [c for c in other_clips if c.start_ms >= self._drag_orig_end_ms]

            min_start_bound = max([c.end_ms for c in prev_clips], default=0)
            max_end_bound = min([c.start_ms for c in next_clips], default=self._duration_ms if self._duration_ms > 0 else 99999999)

            if self._drag_mode == self.MODE_MOVE:
                dur = self._drag_orig_end_ms - self._drag_orig_start_ms
                desired_start = self._drag_orig_start_ms + delta_ms
                
                max_start_allowed = max_end_bound - dur
                new_start = max(min_start_bound, min(desired_start, max_start_allowed))
                new_end = new_start + dur
                self.clip_timing_changed.emit(self._drag_clip_id, new_start, new_end)

            elif self._drag_mode == self.MODE_RESIZE_LEFT:
                desired_start = self._drag_orig_start_ms + delta_ms
                max_start_allowed = self._drag_orig_end_ms - MIN_CLIP_DURATION
                new_start = max(min_start_bound, min(desired_start, max_start_allowed))
                self.clip_timing_changed.emit(self._drag_clip_id, new_start, self._drag_orig_end_ms)

            elif self._drag_mode == self.MODE_RESIZE_RIGHT:
                desired_end = self._drag_orig_end_ms + delta_ms
                min_end_allowed = self._drag_orig_start_ms + MIN_CLIP_DURATION
                new_end = max(min_end_allowed, min(desired_end, max_end_bound))
                self.clip_timing_changed.emit(self._drag_clip_id, self._drag_orig_start_ms, new_end)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_mode = self.MODE_NONE
            self._drag_clip_id = None
            self.setCursor(QCursor(Qt.ArrowCursor))
            self.update()

    # ──────────────────────────────────────────────────────────────────────
    # Painting
    # ──────────────────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # 1. Background
        painter.fillRect(self.rect(), QColor("#0e1016"))

        # 2. Draw Ruler
        self._draw_ruler(painter)

        # 3. Draw Track background & Grid
        painter.setPen(QPen(QColor(255, 255, 255, 15), 1))
        painter.drawLine(0, RULER_HEIGHT, self.width(), RULER_HEIGHT)
        painter.drawLine(0, CLIP_TRACK_TOP + CLIP_HEIGHT + 6, self.width(), CLIP_TRACK_TOP + CLIP_HEIGHT + 6)

        # 4. Draw Subtitle Clips
        for clip in self._clips:
            is_selected = (clip.id == self._selected_clip_id)
            is_active = clip.is_active_at(self._current_time_ms)
            self._draw_clip(painter, clip, selected=is_selected, active=is_active)

        # 5. Draw Playhead Line
        self._draw_playhead(painter)

    def _draw_ruler(self, painter: QPainter) -> None:
        ruler_rect = QRectF(0, 0, self.width(), RULER_HEIGHT)
        painter.fillRect(ruler_rect, QColor("#161922"))

        painter.setFont(QFont("Inter", 9))
        font_metrics = painter.fontMetrics()

        # Tính bước nhảy ruler tick (1s, 2s, 5s, 10s...) dựa vào zoom
        sec_step = 1
        if self._px_per_sec < 15:
            sec_step = 10
        elif self._px_per_sec < 30:
            sec_step = 5
        elif self._px_per_sec < 60:
            sec_step = 2

        total_sec = max(10, int(self.width() / self._px_per_sec))

        for sec in range(0, total_sec + 1, sec_step):
            x = sec * self._px_per_sec
            if x > self.width():
                break

            # Major tick
            painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
            painter.drawLine(int(x), RULER_HEIGHT - 10, int(x), RULER_HEIGHT)

            # Label text
            m, s = divmod(sec, 60)
            time_str = f"{m:02d}:{s:02d}"
            painter.setPen(QColor("#7a8099"))
            painter.drawText(int(x) + 4, RULER_HEIGHT - 10, time_str)

            # Minor ticks
            if sec_step > 1:
                for sub_sec in range(1, sec_step):
                    sub_x = (sec + sub_sec) * self._px_per_sec
                    painter.setPen(QPen(QColor(255, 255, 255, 25), 1))
                    painter.drawLine(int(sub_x), RULER_HEIGHT - 5, int(sub_x), RULER_HEIGHT)

    def _draw_clip(self, painter: QPainter, clip: SubtitleClip, selected: bool, active: bool = False) -> None:
        painter.save()
        rect = self.get_clip_rect(clip)

        # Style colors
        if selected:
            bg_color = QColor("#2b4c7e")
            border_color = QColor("#4f8aff")
            text_color = QColor("#ffffff")
        elif active:
            bg_color = QColor("#232b3a")
            border_color = QColor("#3d4960")
            text_color = QColor("#d0d6e6")
        else:
            bg_color = QColor("#1c202b")
            border_color = QColor("#282e3d")
            text_color = QColor("#8a92a6")

        # Clip body
        path = QPainterPath()
        path.addRoundedRect(rect, 6, 6)
        painter.fillPath(path, QBrush(bg_color))
        
        # Reset brush để tránh rò rỉ màu khi drawPath()
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(border_color, 2.0 if selected else 1.0))
        painter.drawPath(path)

        # Draw handles if selected
        if selected:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#4f8aff")))

            # Left handle
            left_rect = QRectF(rect.left(), rect.top() + 8, 3, rect.height() - 16)
            painter.drawRoundedRect(left_rect, 1.5, 1.5)

            # Right handle
            right_rect = QRectF(rect.right() - 3, rect.top() + 8, 3, rect.height() - 16)
            painter.drawRoundedRect(right_rect, 1.5, 1.5)

        # Clip Text
        painter.setFont(QFont("Inter", 9, QFont.Bold if selected else QFont.Normal))
        painter.setPen(text_color)

        elided_text = painter.fontMetrics().elidedText(
            clip.text, Qt.ElideRight, max(1, int(rect.width() - 16))
        )
        painter.drawText(
            rect.adjusted(8, 0, -8, 0),
            Qt.AlignLeft | Qt.AlignVCenter,
            elided_text,
        )
        painter.restore()

    def _draw_playhead(self, painter: QPainter) -> None:
        px = self.ms_to_px(self._current_time_ms)

        # Line
        painter.setPen(QPen(QColor("#ff4f4f"), 1.5))
        painter.drawLine(int(px), 0, int(px), self.height())

        # Top Triangle Handle on Ruler
        triangle = QPainterPath()
        triangle.moveTo(px - 6, 0)
        triangle.lineTo(px + 6, 0)
        triangle.lineTo(px, 10)
        triangle.closeSubpath()

        painter.fillPath(triangle, QBrush(QColor("#ff4f4f")))


# ──────────────────────────────────────────────────────────────────────────
# Main Timeline Widget
# ──────────────────────────────────────────────────────────────────────────

class TimelineWidget(QWidget):
    """
    Widget Timeline hoàn chỉnh với Toolbar, Scroll Area và Timeline Canvas.
    """

    clip_selected = Signal(str)
    clip_deselected = Signal()
    clip_timing_changed = Signal(str, int, int)  # clip_id, start_ms, end_ms
    add_subtitle_requested = Signal()
    play_pause_requested = Signal()
    seek_requested = Signal(int)  # ms

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TimelinePanel")
        self.setFixedHeight(154)

        self._px_per_sec: float = 50.0
        self._has_video: bool = False
        self._current_time_ms: int = 0
        self._duration_ms: int = 0
        self._clips: list[SubtitleClip] = []
        self._selected_clip_id: str | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Control bar ────────────────────────────────────────────────
        ctrl_bar = QWidget()
        ctrl_bar.setObjectName("TimelineCtrlBar")
        ctrl_bar.setFixedHeight(40)

        ctrl = QHBoxLayout(ctrl_bar)
        ctrl.setContentsMargins(12, 0, 16, 0)
        ctrl.setSpacing(10)

        # Play/Pause button
        self._play_btn = QPushButton("▶")
        self._play_btn.setObjectName("PlayPauseBtn")
        self._play_btn.setFixedSize(32, 28)
        self._play_btn.setCursor(Qt.PointingHandCursor)
        self._play_btn.setEnabled(False)
        self._play_btn.clicked.connect(self.play_pause_requested)
        ctrl.addWidget(self._play_btn)

        # Time display
        self._time_label = QLabel("00:00.0 / 00:00.0")
        self._time_label.setObjectName("TimeDisplay")
        ctrl.addWidget(self._time_label)

        ctrl.addSpacing(8)

        timeline_label = QLabel("TIMELINE")
        timeline_label.setObjectName("TimelineLabel")
        ctrl.addWidget(timeline_label)

        ctrl.addStretch()

        # ── Zoom Controls ──────────────────────────────────────────────
        zoom_label = QLabel("Zoom:")
        zoom_label.setStyleSheet("color: #7a8099; font-size: 11px;")
        ctrl.addWidget(zoom_label)

        self._zoom_out_btn = QPushButton("➖")
        self._zoom_out_btn.setFixedSize(26, 24)
        self._zoom_out_btn.setCursor(Qt.PointingHandCursor)
        self._zoom_out_btn.setToolTip("Thu nhỏ timeline")
        self._zoom_out_btn.clicked.connect(self._zoom_out)
        ctrl.addWidget(self._zoom_out_btn)

        self._zoom_in_btn = QPushButton("➕")
        self._zoom_in_btn.setFixedSize(26, 24)
        self._zoom_in_btn.setCursor(Qt.PointingHandCursor)
        self._zoom_in_btn.setToolTip("Phóng to timeline")
        self._zoom_in_btn.clicked.connect(self._zoom_in)
        ctrl.addWidget(self._zoom_in_btn)

        ctrl.addSpacing(10)

        self._add_btn = QPushButton("＋ Add Subtitle")
        self._add_btn.setObjectName("AddSubtitleBtn")
        self._add_btn.setCursor(Qt.PointingHandCursor)
        self._add_btn.setEnabled(False)
        self._add_btn.clicked.connect(self.add_subtitle_requested)
        ctrl.addWidget(self._add_btn)

        outer.addWidget(ctrl_bar)

        # ── Scroll Area for Canvas ─────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setObjectName("TimelineScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._canvas = _TimelineCanvas()
        self._canvas.clip_selected.connect(self.clip_selected)
        self._canvas.clip_deselected.connect(self.clip_deselected)
        self._canvas.clip_timing_changed.connect(self.clip_timing_changed)
        self._canvas.seek_requested.connect(self.seek_requested)

        self._scroll.setWidget(self._canvas)
        outer.addWidget(self._scroll, stretch=1)

        # ── Empty hint ─────────────────────────────────────────────────
        self._hint = QLabel("Import file SRT hoặc JSON để hiển thị timeline subtitle")
        self._hint.setObjectName("TimelineHint")
        self._hint.setAlignment(Qt.AlignCenter)
        outer.addWidget(self._hint)
        self._hint.hide()

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def set_has_video(self, has_video: bool) -> None:
        self._has_video = has_video
        self._play_btn.setEnabled(has_video)
        self._add_btn.setEnabled(has_video)

    def set_clips(
        self,
        clips: list[SubtitleClip],
        selected_clip_id: str | None = None,
    ) -> None:
        self._clips = clips
        self._selected_clip_id = selected_clip_id

        if not clips:
            self._scroll.hide()
            self._hint.show()
        else:
            self._hint.hide()
            self._scroll.show()

        self._refresh_canvas()

    def clear_selection(self) -> None:
        self._selected_clip_id = None
        self._refresh_canvas()

    @Slot(int, int)
    def set_current_time(self, current_ms: int, duration_ms: int) -> None:
        self._current_time_ms = current_ms
        if duration_ms > 0:
            self._duration_ms = duration_ms

        def fmt(ms: int) -> str:
            s = ms // 1000
            ds = (ms % 1000) // 100
            m, s = divmod(s, 60)
            return f"{m:02d}:{s:02d}.{ds}"

        self._time_label.setText(f"{fmt(current_ms)} / {fmt(self._duration_ms)}")
        self._refresh_canvas()

        # Tự động cuộn scrollbar để luôn thấy playhead khi video chạy
        px = self._canvas.ms_to_px(current_ms)
        hbar = self._scroll.horizontalScrollBar()
        if hbar and not hbar.isSliderDown():
            view_w = self._scroll.viewport().width()
            if px < hbar.value() or px > hbar.value() + view_w - 50:
                hbar.setValue(int(px - view_w / 2))

    @Slot(bool)
    def set_playing(self, playing: bool) -> None:
        self._play_btn.setText("⏸" if playing else "▶")

    # ──────────────────────────────────────────────────────────────────────
    # Zoom Logic
    # ──────────────────────────────────────────────────────────────────────

    def _zoom_in(self) -> None:
        self._px_per_sec = min(300.0, self._px_per_sec * 1.25)
        self._refresh_canvas()

    def _zoom_out(self) -> None:
        self._px_per_sec = max(10.0, self._px_per_sec / 1.25)
        self._refresh_canvas()

    def _refresh_canvas(self) -> None:
        self._canvas.set_data(
            self._clips,
            self._selected_clip_id,
            self._current_time_ms,
            self._duration_ms,
            self._px_per_sec,
        )
