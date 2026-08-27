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

        # ── Title ─────────────────────────────────────────────────────────
        title = QLabel("Subtitle Video Editor version 1.0.0")
        title.setObjectName("AppTitle")
        layout.addWidget(title)

        # ── Home / Dashboard Button ────────────────────────────────────────
        self._projects_btn = QPushButton("🏠 Home")
        self._projects_btn.setObjectName("HeaderSecBtn")
        self._projects_btn.setCursor(Qt.PointingHandCursor)
        self._projects_btn.setToolTip("Quay về màn hình chính Dashboard")
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

        layout.addStretch()

        # ── Import Video ───────────────────────────────────────────────────
        self._import_video_btn = QPushButton("＋ Video")
        self._import_video_btn.setObjectName("HeaderSecBtn")
        self._import_video_btn.setCursor(Qt.PointingHandCursor)
        self._import_video_btn.setToolTip("Import video")
        self._import_video_btn.clicked.connect(self._on_import_video)
        layout.addWidget(self._import_video_btn)

        # ── Import Phụ Đề (Gộp chung SRT, CapCut JSON, VEED JSON) ───────────
        self._import_sub_btn = QPushButton("📥 Import Phụ Đề ▼")
        self._import_sub_btn.setObjectName("HeaderSecBtn")
        self._import_sub_btn.setCursor(Qt.PointingHandCursor)
        self._import_sub_btn.setToolTip("Import phụ đề từ file SRT, CapCut JSON, hoặc VEED JSON")
        self._import_sub_btn.setEnabled(False)

        # Trỏ các thuộc tính cũ sang nút gộp để bảo toàn tương thích
        self._import_srt_btn = self._import_sub_btn
        self._import_capcut_json_btn = self._import_sub_btn
        self._import_json_btn = self._import_sub_btn

        self._sub_menu = QMenu(self)

        # Loại 1: File SRT
        srt_menu = self._sub_menu.addMenu("📄 File Phụ Đề SRT")
        act_srt_open = srt_menu.addAction("📂 Chọn file SRT từ máy tính...")
        act_srt_open.triggered.connect(self._on_import_srt)
        srt_menu.addSeparator()
        act_srt_sample = srt_menu.addAction("📥 Tải file mẫu (example.srt)")
        act_srt_sample.triggered.connect(
            lambda: self._download_sample("example.srt", "example.srt", "SRT Files (*.srt)", "srt")
        )

        # Loại 2: CapCut JSON
        capcut_menu = self._sub_menu.addMenu("🎬 File Phụ Đề theo CapCut")
        act_capcut_open = capcut_menu.addAction("📂 Chọn file CapCut JSON (draft_content.json)...")
        act_capcut_open.triggered.connect(self._on_import_capcut_json)
        capcut_menu.addSeparator()
        act_capcut_sample = capcut_menu.addAction("📥 Tải file mẫu (draft_content.json)")
        act_capcut_sample.triggered.connect(
            lambda: self._download_sample("draft_content.json", "draft_content.json", "JSON Files (*.json)", "capcut")
        )
        act_capcut_yt = capcut_menu.addAction("📺 Video hướng dẫn lấy file (YouTube)")
        act_capcut_yt.triggered.connect(
            lambda: self._open_youtube_tutorial("https://youtu.be/28OfwAitbBs")
        )

        # Loại 3: VEED JSON
        veed_menu = self._sub_menu.addMenu("🎯 File Phụ Đề theo VEED")
        act_veed_open = veed_menu.addAction("📂 Chọn file VEED JSON (subtitle.json)...")
        act_veed_open.triggered.connect(self._on_import_json)
        veed_menu.addSeparator()
        act_veed_sample = veed_menu.addAction("📥 Tải file mẫu (subtitle.json)")
        act_veed_sample.triggered.connect(
            lambda: self._download_sample("subtitle.json", "subtitle.json", "JSON Files (*.json)", "veed")
        )
        act_veed_yt = veed_menu.addAction("📺 Video hướng dẫn lấy file (YouTube)")
        act_veed_yt.triggered.connect(
            lambda: self._open_youtube_tutorial("https://youtu.be/qjWCeXaY5KI")
        )

        self._import_sub_btn.setMenu(self._sub_menu)
        layout.addWidget(self._import_sub_btn)

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

    def set_editor_mode(self, is_editor: bool) -> None:
        """
        Thiết lập hiển thị các phần tử trên HeaderBar:
        - ở ngoài Dashboard (is_editor=False): Hiện 'Gần đây ▼', ẩn 'Home', ẩn các nút Import/Export tool.
        - ở trong Editor (is_editor=True): Hiện 'Home', ẩn 'Gần đây ▼', hiện các nút Import/Export tool.
        """
        self._projects_btn.setVisible(is_editor)
        self._recent_btn.setVisible(not is_editor)

        self._import_video_btn.setVisible(is_editor)
        self._import_sub_btn.setVisible(is_editor)
        self._export_btn.setVisible(is_editor)

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
        """Bật/tắt nút Import Phụ Đề dựa theo có video hay chưa."""
        self._has_video = has_video
        self._import_sub_btn.setEnabled(has_video)

    def set_highlight_mode(self, is_highlight: bool) -> None:
        """
        Cập nhật trạng thái mode (Normal ↔ Word Highlight).
        """
        self._highlight_mode = is_highlight
        self._import_sub_btn.setEnabled(self._has_video)

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

    def _download_sample(self, filename: str, default_name: str, file_filter: str, import_type: str) -> None:
        """Cho phép người dùng lưu file mẫu về máy và tùy chọn nạp vào ứng dụng ngay."""
        root_data = Path(__file__).parent.parent.parent / "data" / filename
        local_data = Path("data") / filename
        src_path = root_data if root_data.is_file() else local_data

        if not src_path.is_file():
            QMessageBox.warning(self, "Lỗi", f"Không tìm thấy file mẫu: {filename}")
            return

        dest_path, _ = QFileDialog.getSaveFileName(
            self, f"Lưu file mẫu {filename}", default_name, file_filter
        )
        if dest_path:
            try:
                import shutil
                shutil.copyfile(src_path, dest_path)
                reply = QMessageBox.question(
                    self,
                    "Tải File Mẫu Thành Công",
                    f"Đã lưu file mẫu thành công tại:\n{dest_path}\n\nBạn có muốn nạp file mẫu này vào dự án ngay không?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )
                if reply == QMessageBox.Yes:
                    if import_type == "srt":
                        self.import_srt_requested.emit(dest_path)
                    elif import_type == "capcut":
                        self.import_capcut_json_requested.emit(dest_path)
                    elif import_type == "veed":
                        self.import_json_requested.emit(dest_path)
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể lưu file mẫu: {e}")

    def _open_youtube_tutorial(self, url: str) -> None:
        """Mở đường dẫn video hướng dẫn trên trình duyệt web mặc định."""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl(url))
