"""
src/ui/header_bar.py
─────────────────────
Thanh header cố định trên cùng: title, Import Video, Import SRT,
Import JSON (word timing — chỉ enable ở mode Word Highlight), Export MP4.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)


class HeaderBar(QWidget):
    """
    Thanh header trên cùng.

    Signals
    -------
    import_video_requested(path: str)  – người dùng chọn file video
    import_srt_requested(path: str)    – người dùng chọn file SRT
    import_json_requested(path: str)   – người dùng chọn file JSON (word timing)
    export_requested()                 – người dùng bấm Export MP4
    """

    import_video_requested = Signal(str)
    import_srt_requested   = Signal(str)
    import_json_requested  = Signal(str)
    export_requested       = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HeaderBar")
        self.setFixedHeight(52)

        # Internal state
        self._has_video: bool      = False
        self._highlight_mode: bool = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(10)

        # ── Title ─────────────────────────────────────────────────────────
        title = QLabel("Subtitle Video Editor")
        title.setObjectName("AppTitle")
        layout.addWidget(title)
        layout.addStretch()

        # ── Import Video ───────────────────────────────────────────────────
        self._import_video_btn = QPushButton("＋ Video")
        self._import_video_btn.setObjectName("HeaderSecBtn")
        self._import_video_btn.setCursor(Qt.PointingHandCursor)
        self._import_video_btn.setToolTip("Import video")
        self._import_video_btn.clicked.connect(self._on_import_video)
        layout.addWidget(self._import_video_btn)

        # ── Import SRT ─────────────────────────────────────────────────────
        self._import_srt_btn = QPushButton("＋ SRT")
        self._import_srt_btn.setObjectName("HeaderSecBtn")
        self._import_srt_btn.setCursor(Qt.PointingHandCursor)
        self._import_srt_btn.setToolTip("Import file SRT")
        self._import_srt_btn.setEnabled(False)
        self._import_srt_btn.clicked.connect(self._on_import_srt)
        layout.addWidget(self._import_srt_btn)

        # ── Import JSON (word timing) — chỉ enable ở Word Highlight mode ──
        self._import_json_btn = QPushButton("🎯 Import JSON")
        self._import_json_btn.setObjectName("HeaderSecBtn")
        self._import_json_btn.setCursor(Qt.PointingHandCursor)
        self._import_json_btn.setToolTip(
            "Import word timing từ file JSON (Word Highlight mode)\n"
            "Chuẩn xác hơn SRT — dùng timestamp thực từng từ theo giọng nói."
        )
        self._import_json_btn.setEnabled(False)
        self._import_json_btn.clicked.connect(self._on_import_json)
        layout.addWidget(self._import_json_btn)

        # ── Export ─────────────────────────────────────────────────────────
        self._export_btn = QPushButton("Export MP4")
        self._export_btn.setObjectName("HeaderExportBtn")
        self._export_btn.setCursor(Qt.PointingHandCursor)
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self.export_requested)
        layout.addWidget(self._export_btn)

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def set_has_video(self, has_video: bool) -> None:
        """Bật/tắt nút Import SRT dựa theo có video hay chưa."""
        self._has_video = has_video
        self._import_srt_btn.setEnabled(has_video)
        # JSON button: chỉ enable khi có video VÀ đang ở highlight mode
        self._import_json_btn.setEnabled(has_video and self._highlight_mode)

    def set_highlight_mode(self, is_highlight: bool) -> None:
        """
        Cập nhật trạng thái nút Import JSON theo mode.
        Gọi khi người dùng chuyển giữa Normal ↔ Word Highlight.
        """
        self._highlight_mode = is_highlight
        self._import_json_btn.setEnabled(self._has_video and is_highlight)

    def set_export_enabled(self, enabled: bool) -> None:
        """Bật/tắt nút Export MP4."""
        self._export_btn.setEnabled(enabled)

    def set_exporting(self, exporting: bool) -> None:
        """Cập nhật trạng thái khi đang/dừng export."""
        self._export_btn.setText("Đang xuất…" if exporting else "Export MP4")
        self._export_btn.setEnabled(False if exporting else None is None)
        # re-enable handled by set_export_enabled after finish

    # ──────────────────────────────────────────────────────────────────────
    # Private slots
    # ──────────────────────────────────────────────────────────────────────

    def _on_import_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn video", "",
            "Video Files (*.mp4 *.mov *.avi *.mkv *.webm *.m4v);;All Files (*)",
        )
        if path:
            self.import_video_requested.emit(path)

    def _on_import_srt(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file SRT", "",
            "Subtitle Files (*.srt);;All Files (*)",
        )
        if path:
            self.import_srt_requested.emit(path)

    def _on_import_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file JSON (word timing)", "",
            "JSON Files (*.json);;All Files (*)",
        )
        if path:
            self.import_json_requested.emit(path)
