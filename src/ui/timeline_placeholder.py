"""
src/ui/timeline_placeholder.py
────────────────────────────────
Bước 3 update: Thêm playback controls + time display.

Bước 4 sẽ thay thế bằng timeline thật có drag/resize.

Signals
-------
clip_selected(clip_id)       – clip chip được click (chưa chọn)
clip_deselected()            – click lại clip đang chọn → bỏ chọn
add_subtitle_requested()     – nút + Add Subtitle gần timeline
play_pause_requested()       – nút play/pause (bước 3)
seek_requested(ms: int)      – click chip → seek video đến start_ms (bước 3)
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..models import SubtitleClip


class TimelinePlaceholder(QWidget):
    """
    Vùng timeline tạm — hiển thị clips dưới dạng chip.

    Signals
    -------
    clip_selected(clip_id: str)   – clip được click (và chưa được chọn)
    clip_deselected()             – click vào clip đang chọn → bỏ chọn
    add_subtitle_requested()      – nút + Add Subtitle được nhấn
    play_pause_requested()        – nút ▶/⏸ được nhấn
    seek_requested(ms: int)       – người dùng click chip muốn seek
    """

    clip_selected          = Signal(str)
    clip_deselected        = Signal()
    add_subtitle_requested = Signal()
    play_pause_requested   = Signal()
    seek_requested         = Signal(int)    # ms

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TimelinePanel")
        self.setFixedHeight(148)

        self._selected_clip_id: str | None = None
        self._is_playing: bool = False

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
        self._play_btn.clicked.connect(self._on_play_pause_clicked)
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

        self._add_btn = QPushButton("＋ Add Subtitle")
        self._add_btn.setObjectName("AddSubtitleBtn")
        self._add_btn.setCursor(Qt.PointingHandCursor)
        self._add_btn.setEnabled(False)
        self._add_btn.clicked.connect(self.add_subtitle_requested)
        ctrl.addWidget(self._add_btn)

        outer.addWidget(ctrl_bar)

        # ── Clips scroll area ──────────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setObjectName("TimelineScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._chips_container = QWidget()
        self._chips_container.setObjectName("TimelineClips")
        self._chips_layout = QHBoxLayout(self._chips_container)
        self._chips_layout.setContentsMargins(16, 8, 16, 8)
        self._chips_layout.setSpacing(8)
        self._chips_layout.addStretch()

        self._scroll.setWidget(self._chips_container)
        outer.addWidget(self._scroll, stretch=1)

        # ── Empty hint ─────────────────────────────────────────────────
        self._hint = QLabel("Import file SRT để hiển thị subtitle")
        self._hint.setObjectName("TimelineHint")
        self._hint.setAlignment(Qt.AlignCenter)
        outer.addWidget(self._hint)
        self._hint.hide()

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def set_has_video(self, has_video: bool) -> None:
        """Bật/tắt các thao tác cần video."""
        self._play_btn.setEnabled(has_video)
        self._add_btn.setEnabled(has_video)

    def set_clips(
        self,
        clips: list[SubtitleClip],
        selected_clip_id: str | None = None,
    ) -> None:
        """Render lại danh sách clip chips."""
        self._selected_clip_id = selected_clip_id

        # Xóa chips cũ (giữ stretch ở cuối)
        while self._chips_layout.count() > 1:
            item = self._chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        sorted_clips = sorted(clips, key=lambda c: c.start_ms)

        if not sorted_clips:
            self._scroll.hide()
            self._hint.show()
            return

        self._hint.hide()
        self._scroll.show()

        for clip in sorted_clips:
            chip = _ClipChip(clip, selected=(clip.id == selected_clip_id))
            chip.clicked_id.connect(self._on_chip_clicked)
            chip.seek_requested.connect(self.seek_requested)
            self._chips_layout.insertWidget(
                self._chips_layout.count() - 1, chip
            )

    def clear_selection(self) -> None:
        """Bỏ chọn clip hiện tại."""
        self._selected_clip_id = None
        for i in range(self._chips_layout.count() - 1):
            item = self._chips_layout.itemAt(i)
            if item and isinstance(item.widget(), _ClipChip):
                item.widget().set_selected(False)

    @Slot(int, int)
    def set_current_time(self, current_ms: int, duration_ms: int) -> None:
        """Cập nhật time display label."""
        def fmt(ms: int) -> str:
            s  = ms // 1000
            ds = (ms % 1000) // 100
            m, s = divmod(s, 60)
            return f"{m:02d}:{s:02d}.{ds}"

        self._time_label.setText(f"{fmt(current_ms)} / {fmt(duration_ms)}")

    @Slot(bool)
    def set_playing(self, playing: bool) -> None:
        """Cập nhật icon nút play/pause."""
        self._is_playing = playing
        self._play_btn.setText("⏸" if playing else "▶")

    # ──────────────────────────────────────────────────────────────────────
    # Private slots
    # ──────────────────────────────────────────────────────────────────────

    def _on_chip_clicked(self, clip_id: str) -> None:
        if clip_id == self._selected_clip_id:
            self._selected_clip_id = None
            self.clip_deselected.emit()
        else:
            self._selected_clip_id = clip_id
            self.clip_selected.emit(clip_id)

    def _on_play_pause_clicked(self) -> None:
        self.play_pause_requested.emit()


# ──────────────────────────────────────────────────────────────────────────
# Clip Chip widget
# ──────────────────────────────────────────────────────────────────────────

class _ClipChip(QWidget):
    """Chip nhỏ đại diện một subtitle clip trên timeline placeholder."""

    clicked_id    = Signal(str)   # clip_id
    seek_requested = Signal(int)  # start_ms

    def __init__(self, clip: SubtitleClip, selected: bool = False, parent=None):
        super().__init__(parent)
        self._clip_id  = clip.id
        self._start_ms = clip.start_ms
        self._selected = selected

        self.setObjectName("ClipChip")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(68)
        self.setMinimumWidth(110)
        self.setMaximumWidth(200)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(3)

        # Time label
        start_s = clip.start_ms / 1000
        m, s = divmod(int(start_s), 60)
        ms_frac = clip.start_ms % 1000
        time_str = f"{m:02d}:{s:02d}.{ms_frac // 100}"

        self._time_lbl = QLabel(time_str)
        self._time_lbl.setObjectName("ChipTime")
        layout.addWidget(self._time_lbl)

        # Text preview
        preview = clip.text[:24] + ("…" if len(clip.text) > 24 else "")
        self._text_lbl = QLabel(preview)
        self._text_lbl.setObjectName("ChipText")
        self._text_lbl.setWordWrap(False)
        layout.addWidget(self._text_lbl)

        self._refresh_style()

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._refresh_style()

    def _refresh_style(self) -> None:
        self.setProperty("selected", self._selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            # Single click: select + seek
            self.clicked_id.emit(self._clip_id)
            self.seek_requested.emit(self._start_ms)
