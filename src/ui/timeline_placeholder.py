"""
src/ui/timeline_placeholder.py
────────────────────────────────
Placeholder cho timeline (sẽ được thay thế ở bước 4).

Bước 2 cần một vùng phía dưới editor để:
- Hiển thị danh sách clips dưới dạng chip có thể click để select.
- Nút [+ Add Subtitle].
- Cho phép deselect khi click vào clip đang chọn.

Đây là scaffold để test các state 3/4 của editor trước khi timeline
thực sự được xây dựng.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
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
    clip_selected(clip_id: str)  – clip được click (và chưa được chọn)
    clip_deselected()            – click vào clip đang chọn → bỏ chọn
    add_subtitle_requested()     – nút + Add Subtitle được nhấn
    """

    clip_selected         = Signal(str)
    clip_deselected       = Signal()
    add_subtitle_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TimelinePanel")
        self.setFixedHeight(148)

        self._selected_clip_id: str | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Control bar ────────────────────────────────────────────────
        ctrl_bar = QWidget()
        ctrl_bar.setObjectName("TimelineCtrlBar")
        ctrl_bar.setFixedHeight(40)

        ctrl = QHBoxLayout(ctrl_bar)
        ctrl.setContentsMargins(16, 0, 16, 0)
        ctrl.setSpacing(12)

        timeline_label = QLabel("TIMELINE")
        timeline_label.setObjectName("TimelineLabel")
        ctrl.addWidget(timeline_label)

        ctrl.addStretch()

        add_btn = QPushButton("＋ Add Subtitle")
        add_btn.setObjectName("AddSubtitleBtn")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setEnabled(False)
        add_btn.clicked.connect(self.add_subtitle_requested)
        self._add_btn = add_btn
        ctrl.addWidget(add_btn)

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
        self._hint = QLabel("Import SRT hoặc nhấn ＋ Add Subtitle")
        self._hint.setObjectName("TimelineHint")
        self._hint.setAlignment(Qt.AlignCenter)
        outer.addWidget(self._hint)
        self._hint.hide()

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def set_has_video(self, has_video: bool) -> None:
        """Bật/tắt nút Add Subtitle."""
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

    # ──────────────────────────────────────────────────────────────────────
    # Private slots
    # ──────────────────────────────────────────────────────────────────────

    def _on_chip_clicked(self, clip_id: str) -> None:
        if clip_id == self._selected_clip_id:
            # Bỏ chọn nếu click lại clip đang chọn
            self._selected_clip_id = None
            self.clip_deselected.emit()
        else:
            self._selected_clip_id = clip_id
            self.clip_selected.emit(clip_id)


# ──────────────────────────────────────────────────────────────────────────
# Clip Chip widget
# ──────────────────────────────────────────────────────────────────────────

class _ClipChip(QWidget):
    """Chip nhỏ đại diện một subtitle clip trên timeline placeholder."""

    clicked_id = Signal(str)  # clip_id

    def __init__(self, clip: SubtitleClip, selected: bool = False, parent=None):
        super().__init__(parent)
        self._clip_id = clip.id
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
        ms = clip.start_ms % 1000
        time_str = f"{m:02d}:{s:02d}.{ms // 100}"

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
            self.clicked_id.emit(self._clip_id)
