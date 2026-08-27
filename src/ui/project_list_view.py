"""
src/ui/project_list_view.py
────────────────────────────
View màn hình quản lý danh sách dự án (Dashboard / Project List).
Hỗ trợ hiển thị Grid (Cards) / List (Bảng), tìm kiếm, tạo dự án mới, đổi tên, nhân bản, xóa.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..models import ProjectMetadata
from ..project_manager import ProjectManager
from .project_card import ProjectCardWidget, _format_duration, _format_timestamp


def _get_asset_path(filename: str) -> Path:
    candidates = [
        Path(__file__).parent.parent.parent / "data" / "assets" / filename,
        Path("data/assets") / filename,
        Path.cwd() / "data" / "assets" / filename,
        Path.cwd() / "subtitle-editor" / "data" / "assets" / filename,
    ]
    for c in candidates:
        if c.is_file():
            return c
    return Path("data/assets") / filename


class PathSettingsDialog(QDialog):
    """Hộp thoại cài đặt đường dẫn lưu dự án và xuất video (giao diện gọn gàng, hiện đại)."""

    def __init__(self, project_manager: ProjectManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.pm = project_manager
        self.setWindowTitle("⚙ Cài Đặt Đường Dẫn")
        self.setMinimumWidth(560)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._setup_style()
        self._init_ui()

    def _setup_style(self) -> None:
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel.sectionTitle {
                font-size: 14px;
                font-weight: bold;
                color: #dddddd;
            }
            QLabel.pathBox {
                color: #4a9eff;
                font-size: 12px;
                background-color: #2b2b2b;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 7px 10px;
            }
            QPushButton.btnPick {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton.btnPick:hover {
                background-color: #383838;
                border-color: #007acc;
                color: #ffffff;
            }
            QPushButton#btnClose {
                background-color: #007acc;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 26px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton#btnClose:hover {
                background-color: #0098ff;
            }
        """)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 1. Projects Directory Section
        v_proj = QVBoxLayout()
        v_proj.setSpacing(8)

        lbl_proj_title = QLabel("📁 Thư Mục Lưu Dự Án (.subproj)")
        lbl_proj_title.setProperty("class", "sectionTitle")
        v_proj.addWidget(lbl_proj_title)

        row_proj = QHBoxLayout()
        row_proj.setSpacing(8)

        self.lbl_proj = QLabel(str(self.pm.projects_dir))
        self.lbl_proj.setProperty("class", "pathBox")
        self.lbl_proj.setWordWrap(True)
        row_proj.addWidget(self.lbl_proj, stretch=1)

        btn_change_proj = QPushButton("Chọn thư mục")
        btn_change_proj.setProperty("class", "btnPick")
        btn_change_proj.setCursor(Qt.PointingHandCursor)
        btn_change_proj.clicked.connect(self._on_change_proj_dir)
        row_proj.addWidget(btn_change_proj)

        v_proj.addLayout(row_proj)
        layout.addLayout(v_proj)

        # 2. Export Video Directory Section
        v_exp = QVBoxLayout()
        v_exp.setSpacing(8)

        lbl_exp_title = QLabel("🎬 Thư Mục Xuất Video (.mp4)")
        lbl_exp_title.setProperty("class", "sectionTitle")
        v_exp.addWidget(lbl_exp_title)

        row_exp = QHBoxLayout()
        row_exp.setSpacing(8)

        self.lbl_exp = QLabel(str(self.pm.export_dir))
        self.lbl_exp.setProperty("class", "pathBox")
        self.lbl_exp.setWordWrap(True)
        row_exp.addWidget(self.lbl_exp, stretch=1)

        btn_change_exp = QPushButton("Chọn thư mục")
        btn_change_exp.setProperty("class", "btnPick")
        btn_change_exp.setCursor(Qt.PointingHandCursor)
        btn_change_exp.clicked.connect(self._on_change_exp_dir)
        row_exp.addWidget(btn_change_exp)

        v_exp.addLayout(row_exp)
        layout.addLayout(v_exp)

        # Bottom Close button
        layout.addSpacing(10)
        btn_close = QPushButton("Đóng")
        btn_close.setObjectName("btnClose")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)

    def _on_change_proj_dir(self) -> None:
        new_dir = QFileDialog.getExistingDirectory(
            self, "Chọn thư mục lưu dự án mới", str(self.pm.projects_dir)
        )
        if new_dir:
            self.pm.set_projects_dir(new_dir)
            self.lbl_proj.setText(str(self.pm.projects_dir))

    def _on_change_exp_dir(self) -> None:
        new_dir = QFileDialog.getExistingDirectory(
            self, "Chọn thư mục xuất video mới", str(self.pm.export_dir)
        )
        if new_dir:
            self.pm.set_export_dir(new_dir)
            self.lbl_exp.setText(str(self.pm.export_dir))


class ProjectListView(QWidget):
    """
    View màn hình danh sách dự án (Dashboard).

    Signals
    -------
    open_project_requested(project_id: str) : Người dùng chọn mở dự án
    """

    open_project_requested = Signal(str)

    def __init__(
        self,
        project_manager: Optional[ProjectManager] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.pm = project_manager or ProjectManager()
        self.view_mode = "grid"  # "grid" hoặc "list"
        self.projects_cache: list[ProjectMetadata] = []

        self._setup_style()
        self._init_ui()
        self.refresh_projects()

    def _setup_style(self) -> None:
        self.setStyleSheet("""
            QWidget#ProjectListView {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLineEdit#searchBar {
                background-color: #2b2b2b;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 6px 12px;
                color: #ffffff;
                font-size: 13px;
            }
            QPushButton#btnNewProject {
                background-color: #007acc;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton#btnNewProject:hover {
                background-color: #0098ff;
            }
            QPushButton#btnToggleView {
                background-color: #2b2b2b;
                color: #cccccc;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QPushButton#btnToggleView:hover {
                background-color: #383838;
                color: #ffffff;
            }
            QTableWidget {
                background-color: #2b2b2b;
                color: #e0e0e0;
                gridline-color: #3c3c3c;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
            }
            QHeaderView::section {
                background-color: #1e1e1e;
                color: #aaaaaa;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #3c3c3c;
                font-weight: bold;
            }
            QWidget#DashboardFooter {
                background-color: #252526;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
            }
        """)

    def _init_ui(self) -> None:
        self.setObjectName("ProjectListView")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # 1. Header Toolbar
        toolbar = QHBoxLayout()

        title_label = QLabel("Dashboard Dự Án")
        title_font = title_label.font()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        toolbar.addWidget(title_label)

        toolbar.addStretch()

        # Search Bar
        self.search_bar = QLineEdit()
        self.search_bar.setObjectName("searchBar")
        self.search_bar.setPlaceholderText("🔍 Tìm kiếm dự án...")
        self.search_bar.setFixedWidth(240)
        self.search_bar.textChanged.connect(self._on_search_changed)
        toolbar.addWidget(self.search_bar)

        # Toggle View Mode button
        self.btn_toggle_view = QPushButton("Mode: Grid")
        self.btn_toggle_view.setObjectName("btnToggleView")
        self.btn_toggle_view.clicked.connect(self._toggle_view_mode)
        toolbar.addWidget(self.btn_toggle_view)

        # Path Settings button (Combine projects_dir and export_dir)
        self.btn_settings = QPushButton("⚙ Cài Đặt Đường Dẫn")
        self.btn_settings.setObjectName("btnToggleView")
        self.btn_settings.setToolTip("Cài đặt đường dẫn lưu dự án và xuất video")
        self.btn_settings.clicked.connect(self._show_storage_settings_dialog)
        toolbar.addWidget(self.btn_settings)

        # New Project Button
        btn_new = QPushButton("+ Tạo Dự Án Mới")
        btn_new.setObjectName("btnNewProject")
        btn_new.clicked.connect(self._show_create_project_dialog)
        toolbar.addWidget(btn_new)

        main_layout.addLayout(toolbar)

        # 2. Main Content Area (StackedWidget: Grid, List, Empty State)
        self.stack = QStackedWidget()

        # Page 0: Grid View (Scroll Area)
        self.grid_scroll = QScrollArea()
        self.grid_scroll.setWidgetResizable(True)
        self.grid_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.grid_scroll.setWidget(self.grid_container)

        self.stack.addWidget(self.grid_scroll)

        # Page 1: List / Table View
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Tên Dự Án", "Thời Lượng", "Số Clips", "Cập Nhật Lần Cuối", "Thao Tác"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.stack.addWidget(self.table)

        # Page 2: Empty State
        self.empty_widget = QWidget()
        empty_layout = QVBoxLayout(self.empty_widget)
        empty_layout.setAlignment(Qt.AlignCenter)
        empty_layout.setSpacing(12)

        icon_empty = QLabel("📂")
        icon_font = icon_empty.font()
        icon_font.setPointSize(48)
        icon_empty.setFont(icon_font)
        icon_empty.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(icon_empty)

        label_empty = QLabel("Chưa có dự án nào")
        label_empty.setStyleSheet("color: #888888; font-size: 16px; font-weight: bold;")
        label_empty.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(label_empty)

        sub_empty = QLabel("Hãy tạo dự án mới để bắt đầu tạo phụ đề video cho riêng bạn.")
        sub_empty.setStyleSheet("color: #666666; font-size: 12px;")
        sub_empty.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(sub_empty)

        btn_empty_create = QPushButton("+ Tạo dự án đầu tiên")
        btn_empty_create.setObjectName("btnNewProject")
        btn_empty_create.clicked.connect(self._show_create_project_dialog)
        empty_layout.addWidget(btn_empty_create, alignment=Qt.AlignCenter)

        self.stack.addWidget(self.empty_widget)

        main_layout.addWidget(self.stack)

        # 3. Footer Bar (Dùng icon ảnh từ data\assets)
        footer = QWidget()
        footer.setObjectName("DashboardFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(14, 8, 14, 8)
        footer_layout.setSpacing(8)
        footer_layout.setAlignment(Qt.AlignCenter)

        def _make_icon_label(icon_filename: str) -> QLabel:
            lbl = QLabel()
            icon_path = _get_asset_path(icon_filename)
            if icon_path.is_file():
                pixmap = QPixmap(str(icon_path))
                if not pixmap.isNull():
                    lbl.setPixmap(pixmap.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            return lbl

        # AI Item
        footer_layout.addWidget(_make_icon_label("telegram.png"))
        ai_label = QLabel('AI mình dùng để vibe code <a href="https://t.me/DichVuIT_bot" style="color: #0098ff; text-decoration: none; font-weight: bold;">tại đây : @DichVuIT_bot</a>')
        ai_label.setStyleSheet("color: #cccccc; font-size: 12px;")
        ai_label.setOpenExternalLinks(True)
        footer_layout.addWidget(ai_label)

        # Separator 1
        sep1 = QLabel("•")
        sep1.setStyleSheet("color: #555555; font-size: 12px; margin: 0 4px;")
        footer_layout.addWidget(sep1)

        # Fanpage Item
        footer_layout.addWidget(_make_icon_label("fanpage.png"))
        fp_label = QLabel('<a href="https://web.facebook.com/profile.php?id=61567027726244" style="color: #0098ff; text-decoration: none; font-weight: bold;">Fanpage</a>')
        fp_label.setStyleSheet("color: #cccccc; font-size: 12px;")
        fp_label.setOpenExternalLinks(True)
        footer_layout.addWidget(fp_label)

        # Separator 2
        sep2 = QLabel("•")
        sep2.setStyleSheet("color: #555555; font-size: 12px; margin: 0 4px;")
        footer_layout.addWidget(sep2)

        # Zalo Item
        footer_layout.addWidget(_make_icon_label("zalo.png"))
        zalo_label = QLabel('<a href="https://zalo.me/g/b98og9ldg1rjg7uxg8pt" style="color: #0098ff; text-decoration: none; font-weight: bold;">Zalo</a>')
        zalo_label.setStyleSheet("color: #cccccc; font-size: 12px;")
        zalo_label.setOpenExternalLinks(True)
        footer_layout.addWidget(zalo_label)

        # Separator 3
        sep3 = QLabel("•")
        sep3.setStyleSheet("color: #555555; font-size: 12px; margin: 0 4px;")
        footer_layout.addWidget(sep3)

        # Donate Item
        donate_icon = QLabel("💖")
        donate_icon.setStyleSheet("font-size: 14px;")
        footer_layout.addWidget(donate_icon)

        donate_label = QLabel('Ủng hộ mình tại <a href="https://qr-donate.vercel.app/" style="color: #0098ff; text-decoration: none; font-weight: bold;">Donate</a>')
        donate_label.setStyleSheet("color: #cccccc; font-size: 12px;")
        donate_label.setOpenExternalLinks(True)
        footer_layout.addWidget(donate_label)

        main_layout.addWidget(footer)

    def refresh_projects(self) -> None:
        """Nạp lại danh sách dự án từ ProjectManager và render lại UI."""
        self.projects_cache = self.pm.list_projects()
        self._render_current_view()

    def _on_search_changed(self, text: str) -> None:
        self._render_current_view()

    def _get_filtered_projects(self) -> list[ProjectMetadata]:
        query = self.search_bar.text().strip().lower()
        if not query:
            return self.projects_cache
        return [p for p in self.projects_cache if query in p.name.lower()]

    def _toggle_view_mode(self) -> None:
        if self.view_mode == "grid":
            self.view_mode = "list"
            self.btn_toggle_view.setText("Mode: List")
        else:
            self.view_mode = "grid"
            self.btn_toggle_view.setText("Mode: Grid")
        self._render_current_view()

    def _render_current_view(self) -> None:
        projects = self._get_filtered_projects()

        if not projects:
            self.stack.setCurrentWidget(self.empty_widget)
            return

        if self.view_mode == "grid":
            self._render_grid_view(projects)
            self.stack.setCurrentWidget(self.grid_scroll)
        else:
            self._render_list_view(projects)
            self.stack.setCurrentWidget(self.table)

    def _render_grid_view(self, projects: list[ProjectMetadata]) -> None:
        # Xóa các item cũ trong grid layout
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cols = 4  # Số cột trong grid
        for idx, meta in enumerate(projects):
            row = idx // cols
            col = idx % cols
            card = ProjectCardWidget(meta)
            card.open_requested.connect(self._on_open_project)
            card.rename_requested.connect(self._on_rename_project)
            card.delete_requested.connect(self._on_delete_project)
            self.grid_layout.addWidget(card, row, col)

    def _render_list_view(self, projects: list[ProjectMetadata]) -> None:
        self.table.setRowCount(len(projects))
        for row, meta in enumerate(projects):
            # Name
            self.table.setItem(row, 0, QTableWidgetItem(meta.name))
            # Duration
            self.table.setItem(row, 1, QTableWidgetItem(_format_duration(meta.duration_ms)))
            # Clips
            self.table.setItem(row, 2, QTableWidgetItem(str(meta.clip_count)))
            # Updated date
            self.table.setItem(row, 3, QTableWidgetItem(_format_timestamp(meta.updated_at)))

            # Action buttons cell
            actions_widget = QWidget()
            a_layout = QHBoxLayout(actions_widget)
            a_layout.setContentsMargins(4, 2, 4, 2)
            a_layout.setSpacing(4)

            btn_open = QPushButton("Mở")
            btn_open.clicked.connect(lambda _, pid=meta.project_id: self._on_open_project(pid))
            a_layout.addWidget(btn_open)

            if not getattr(meta, "is_example", False):
                btn_rename = QPushButton("Sửa")
                btn_rename.clicked.connect(lambda _, pid=meta.project_id: self._on_rename_project(pid))
                a_layout.addWidget(btn_rename)

                btn_del = QPushButton("Xóa")
                btn_del.setStyleSheet("color: #ff6b6b;")
                btn_del.clicked.connect(lambda _, pid=meta.project_id: self._on_delete_project(pid))
                a_layout.addWidget(btn_del)

            self.table.setCellWidget(row, 4, actions_widget)

    def _show_storage_settings_dialog(self) -> None:
        dlg = PathSettingsDialog(self.pm, parent=self)
        dlg.exec()
        self.refresh_projects()

    def _show_create_project_dialog(self) -> None:
        """Khởi tạo dự án mới trực tiếp không qua dialog."""
        existing_projects = self.pm.list_projects()
        count = len(existing_projects) + 1
        name = f"Dự án mới {count}"
        try:
            new_project = self.pm.create_project(name=name)
            self.refresh_projects()
            self.open_project_requested.emit(new_project.id)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể tạo dự án: {e}")

    def _on_open_project(self, project_id: str) -> None:
        # Relink check
        try:
            proj = self.pm.load_project(project_id)
            if proj.video_info and proj.video_info.path:
                vpath = Path(proj.video_info.path)
                if not vpath.is_file():
                    reply = QMessageBox.warning(
                        self,
                        "Thiếu File Video Gốc",
                        f"File video không tồn tại tại: {vpath}\nBạn có muốn chọn vị trí file video mới không?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes,
                    )
                    if reply == QMessageBox.Yes:
                        new_path, _ = QFileDialog.getOpenFileName(
                            self,
                            "Chọn file Video mới",
                            "",
                            "Video Files (*.mp4 *.mkv *.avi *.mov *.webm);;All Files (*.*)",
                        )
                        if new_path:
                            proj.video_info.path = Path(new_path)
                            self.pm.save_project(proj)
        except Exception as e:
            print(f"[ProjectListView] Warning when checking project assets: {e}")

        self.open_project_requested.emit(project_id)

    def _on_rename_project(self, project_id: str) -> None:
        if project_id == "5f60564a-01bf-4280-8924-d96817b8541d":
            QMessageBox.warning(self, "Không thể sửa tên", "Dự án Ví dụ không thể đổi tên.")
            return

        try:
            proj = self.pm.load_project(project_id)
        except Exception:
            return

        new_name, ok = QInputDialog.getText(
            self, "Đổi Tên Dự Án", "Tên dự án mới:", QLineEdit.Normal, proj.name
        )
        if ok and new_name.strip():
            self.pm.rename_project(project_id, new_name.strip())
            self.refresh_projects()

    def _on_delete_project(self, project_id: str) -> None:
        if project_id == "5f60564a-01bf-4280-8924-d96817b8541d":
            QMessageBox.warning(self, "Không thể xóa", "Dự án Ví dụ mặc định không thể xóa.")
            return

        reply = QMessageBox.question(
            self,
            "Xác Nhận Xóa",
            "Bạn có chắc chắn muốn xóa dự án này không? Thao tác này không thể hoàn tác.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.pm.delete_project(project_id)
            self.refresh_projects()
