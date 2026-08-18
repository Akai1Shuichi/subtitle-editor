"""
src/ui/video_panel.py
──────────────────────
Panel trái: vùng kéo-thả / chọn video + hiển thị placeholder preview.
Trong bước 3, vdừa drop zone sẽ được thay thế bằng QVideoWidget.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class VideoPanel(QWidget):
    """
    Panel trái của cửa sổ chính.
    Emit video_selected(path: str) khi người dùng chọn / kéo video vào.
    """

    video_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("VideoPanel")
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Drop zone / preview area ──────────────────────────────────────
        self._drop_zone = _DropZone()
        self._drop_zone.clicked.connect(self._pick_video)
        layout.addWidget(self._drop_zone, stretch=1)

        # ── Video meta info bar ───────────────────────────────────────────
        self._meta_bar = _MetaBar()
        self._meta_bar.hide()
        layout.addWidget(self._meta_bar)

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def set_video_info(
        self,
        name: str,
        resolution: str,
        duration_str: str,
        clip_count: int = 0,
    ) -> None:
        """Gọi sau khi probe_video() thành công."""
        self._drop_zone.set_loaded(name, resolution, duration_str, clip_count)
        self._meta_bar.set_info(name, resolution, duration_str)
        self._meta_bar.show()

    def update_clip_count(self, count: int) -> None:
        """Cập nhật số lượng clip hiển thị trên panel (gọi sau import SRT)."""
        self._drop_zone.set_clip_count(count)

    def clear(self) -> None:
        self._drop_zone.clear()
        self._meta_bar.hide()

    # ──────────────────────────────────────────────────────────────────────
    # Drag & Drop
    # ──────────────────────────────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].toLocalFile().lower().endswith(
                (".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v")
            ):
                event.acceptProposedAction()
                self._drop_zone.set_drag_hover(True)
                return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._drop_zone.set_drag_hover(False)

    def dropEvent(self, event: QDropEvent) -> None:
        self._drop_zone.set_drag_hover(False)
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self.video_selected.emit(path)

    # ──────────────────────────────────────────────────────────────────────
    # Slots
    # ──────────────────────────────────────────────────────────────────────

    def _pick_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn video",
            "",
            "Video Files (*.mp4 *.mov *.avi *.mkv *.webm *.m4v);;All Files (*)",
        )
        if path:
            self.video_selected.emit(path)


# ──────────────────────────────────────────────────────────────────────────
# Internal widgets
# ──────────────────────────────────────────────────────────────────────────

class _DropZone(QWidget):
    """Vùng kéo-thả / click để chọn video."""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DropZone")
        self.setCursor(Qt.PointingHandCursor)
        self._loaded = False

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)

        self._icon = QLabel("🎬")
        self._icon.setAlignment(Qt.AlignCenter)
        self._icon.setObjectName("DropIcon")
        layout.addWidget(self._icon)

        self._title = QLabel("Kéo video vào đây")
        self._title.setAlignment(Qt.AlignCenter)
        self._title.setObjectName("DropTitle")
        layout.addWidget(self._title)

        self._sub = QLabel("hoặc click để chọn file\n(MP4, MOV, AVI, MKV)")
        self._sub.setAlignment(Qt.AlignCenter)
        self._sub.setObjectName("DropSub")
        layout.addWidget(self._sub)

    def set_loaded(
        self,
        name: str,
        resolution: str = "",
        duration_str: str = "",
        clip_count: int = 0,
    ) -> None:
        self._loaded = True
        self._icon.setText("🎬")
        self._title.setText(name)
        meta_parts = [p for p in [resolution, duration_str] if p]
        meta_text = "  ·  ".join(meta_parts) if meta_parts else "Click để đổi video"
        clip_info = f"  ·  {clip_count} subtitles" if clip_count > 0 else ""
        self._sub.setText(meta_text + clip_info)

    def set_clip_count(self, count: int) -> None:
        if not self._loaded:
            return
        # Re-read current sub text and append clip info
        # Simplest: just update sub
        text = self._sub.text()
        # Remove previous subtitle count if present
        if " · " in text:
            base = text.rsplit("  ·  ", 1)[0]
        else:
            base = text
        if count > 0:
            self._sub.setText(f"{base}  ·  {count} subtitles")
        else:
            self._sub.setText(base)

    def clear(self) -> None:
        self._loaded = False
        self._icon.setText("🎬")
        self._title.setText("Kéo video vào đây")
        self._sub.setText("hoặc click để chọn file\n(MP4, MOV, AVI, MKV)")

    def set_drag_hover(self, active: bool) -> None:
        self.setProperty("dragHover", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()


class _MetaBar(QWidget):
    """Bar hiển thị resolution và duration bên dưới drop zone."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MetaBar")
        self.setFixedHeight(44)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setAlignment(Qt.AlignVCenter)

        self._label = QLabel()
        self._label.setObjectName("MetaLabel")
        self._label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._label)

    def set_info(self, name: str, resolution: str, duration: str) -> None:
        self._label.setText(f"{resolution}  ·  {duration}")
