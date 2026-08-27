"""
src/ui/header_bar.py
─────────────────────
Thanh header cố định trên cùng: title, nút Projects/Dashboard, Recent Projects menu,
Import Video, Import SRT, Import CapCut JSON, Import JSON (Veed / word timing), Export MP4.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QWidget,
)

from ..models import ProjectMetadata


class HeaderBar(QWidget):
    """
    Thanh header trên cùng.

    Signals
    -------
    projects_requested()                     – chuyển sang giao diện danh sách dự án
    open_recent_project_requested(id: str)   – chọn mở dự án từ danh sách gần đây
    import_video_requested(path: str)        – người dùng chọn file video
    import_srt_requested(path: str)          – người dùng chọn file SRT
    import_capcut_json_requested(path: str)  – người dùng chọn file CapCut JSON
    import_json_requested(path: str)         – người dùng chọn file JSON (Veed word timing)
    export_requested()                       – người dùng bấm Export MP4
    """

    projects_requested            = Signal()
    open_recent_project_requested = Signal(str)
    import_video_requested        = Signal(str)
    import_srt_requested          = Signal(str)
    import_capcut_json_requested  = Signal(str)
    import_json_requested         = Signal(str)
    export_requested              = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HeaderBar")
        self.setFixedHeight(52)

        # Internal state
        self._has_video: bool      = False
        self._highlight_mode: bool = False
        self._recent_projects: list[ProjectMetadata] = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(10)

        # ── Projects / Dashboard Button ────────────────────────────────────
        self._projects_btn = QPushButton("📂 Projects")
        self._projects_btn.setObjectName("HeaderSecBtn")
        self._projects_btn.setCursor(Qt.PointingHandCursor)
        self._projects_btn.setToolTip("Quản lý danh sách dự án")
        self._projects_btn.clicked.connect(self.projects_requested)
        layout.addWidget(self._projects_btn)

        # ── Recent Projects Dropdown ───────────────────────────────────────
        self._recent_btn = QPushButton("Gần đây ▼")
        self._recent_btn.setObjectName("HeaderSecBtn")
        self._recent_btn.setCursor(Qt.PointingHandCursor)
        self._recent_btn.setToolTip("Các dự án mở gần đây")
        self._recent_menu = QMenu(self)
        self._recent_btn.setMenu(self._recent_menu)
        layout.addWidget(self._recent_btn)

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

        # ── Import CapCut JSON ──────────────────────────────────────────────
        self._import_capcut_json_btn = QPushButton("🎬 Import CapCut JSON")
        self._import_capcut_json_btn.setObjectName("HeaderSecBtn")
        self._import_capcut_json_btn.setCursor(Qt.PointingHandCursor)
        self._import_capcut_json_btn.setToolTip(
            "Import subtitle từ file JSON CapCut (draft_content.json)\n"
            "Tự động đọc phụ đề từ materials -> texts và timing từ tracks."
        )
        self._import_capcut_json_btn.setEnabled(False)
        self._import_capcut_json_btn.clicked.connect(self._on_import_capcut_json)
        layout.addWidget(self._import_capcut_json_btn)

        # ── Import JSON (Veed word timing) ──────────────────────────────────
        self._import_json_btn = QPushButton("🎯 Import JSON (Veed)")
        self._import_json_btn.setObjectName("HeaderSecBtn")
        self._import_json_btn.setCursor(Qt.PointingHandCursor)
        self._import_json_btn.setToolTip(
            "Import subtitle từ file JSON Veed (word timing)\n"
            "Chạy được ở cả 2 mode: Normal (dòng tĩnh) và Word Highlight (animate từng từ theo giọng nói)."
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

    def update_recent_projects(self, projects: list[ProjectMetadata]) -> None:
        """Cập nhật danh sách dự án gần đây trong menu dropdown."""
        self._recent_projects = projects
        self._recent_menu.clear()

        if not projects:
            action = self._recent_menu.addAction("Không có dự án nào")
            action.setEnabled(False)
            return

        for meta in projects[:8]:  # Hiển thị tối đa 8 dự án gần nhất
            label_text = f"{meta.name}"
            if meta.clip_count > 0:
                label_text += f" ({meta.clip_count} clips)"
            action = self._recent_menu.addAction(label_text)
            action.triggered.connect(
                lambda checked=False, pid=meta.project_id: self.open_recent_project_requested.emit(pid)
            )

    def set_has_video(self, has_video: bool) -> None:
        """Bật/tắt các nút import subtitle dựa theo có video hay chưa."""
        self._has_video = has_video
        self._import_srt_btn.setEnabled(has_video)
        self._import_capcut_json_btn.setEnabled(has_video)
        self._import_json_btn.setEnabled(has_video)

    def set_highlight_mode(self, is_highlight: bool) -> None:
        """
        Cập nhật trạng thái mode (Normal ↔ Word Highlight).
        Các nút import JSON luôn enabled khi đã có video.
        """
        self._highlight_mode = is_highlight
        self._import_capcut_json_btn.setEnabled(self._has_video)
        self._import_json_btn.setEnabled(self._has_video)

    def set_export_enabled(self, enabled: bool) -> None:
        """Bật/tắt nút Export MP4."""
        self._export_btn.setEnabled(enabled)

    def set_exporting(self, exporting: bool) -> None:
        """Cập nhật trạng thái khi đang/dừng export."""
        self._export_btn.setText("Đang xuất…" if exporting else "Export MP4")
        self._export_btn.setEnabled(False if exporting else None is None)

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

    def _on_import_capcut_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file CapCut JSON", "",
            "JSON Files (*.json);;All Files (*)",
        )
        if path:
            self.import_capcut_json_requested.emit(path)

    def _on_import_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file JSON (word timing)", "",
            "JSON Files (*.json);;All Files (*)",
        )
        if path:
            self.import_json_requested.emit(path)
