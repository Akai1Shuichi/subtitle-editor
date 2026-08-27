"""
src/ui/project_card.py
───────────────────────
Widget hiển thị thông tin dạng Card cho một dự án trong Project List.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..models import ProjectMetadata


def _format_duration(duration_ms: int) -> str:
    """Định dạng duration_ms (milliseconds) -> mm:ss hoặc hh:mm:ss."""
    seconds = duration_ms // 1000
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _format_timestamp(iso_str: str) -> str:
    """Định dạng timestamp ISO string -> YYYY-MM-DD HH:MM."""
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return iso_str


class ProjectCardWidget(QFrame):
    """
    Card widget đại diện cho một dự án trong màn hình danh sách.

    Signals
    -------
    open_requested(project_id: str)      : Click mở dự án
    rename_requested(project_id: str)    : Yêu cầu đổi tên
    duplicate_requested(project_id: str) : Yêu cầu nhân bản
    delete_requested(project_id: str)    : Yêu cầu xóa
    """

    open_requested = Signal(str)
    rename_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, metadata: ProjectMetadata, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.metadata = metadata
        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setFixedSize(280, 240)

        self._setup_style()
        self._init_ui()

    def _setup_style(self) -> None:
        self.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border: 1px solid #3c3c3c;
                border-radius: 8px;
            }
            QFrame:hover {
                border: 1px solid #007acc;
                background-color: #323232;
            }
            QLabel {
                border: none;
                background: transparent;
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #383838;
                color: #e0e0e0;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #007acc;
                border-color: #007acc;
                color: #ffffff;
            }
            QPushButton#btnDelete:hover {
                background-color: #d9534f;
                border-color: #d9534f;
                color: #ffffff;
            }
        """)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # 1. Thumbnail Area
        self.thumb_label = QLabel()
        self.thumb_label.setFixedHeight(110)
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                border-radius: 6px;
                color: #888888;
                font-size: 13px;
            }
        """)
        self._load_thumbnail()
        layout.addWidget(self.thumb_label)

        # 2. Project Name & Badge
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        self.name_label = QLabel(self.metadata.name)
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        self.name_label.setFont(font)
        self.name_label.setToolTip(self.metadata.name)
        title_layout.addWidget(self.name_label)

        if getattr(self.metadata, "is_example", False):
            badge = QLabel("Ví dụ")
            badge.setStyleSheet("background-color: #007acc; color: #ffffff; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: bold;")
            title_layout.addWidget(badge)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # 3. Details (Duration + Clip count)
        dur_str = _format_duration(self.metadata.duration_ms)
        updated_str = _format_timestamp(self.metadata.updated_at)
        info_text = f"⏱ {dur_str}  •  📝 {self.metadata.clip_count} clips"
        self.info_label = QLabel(info_text)
        self.info_label.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        layout.addWidget(self.info_label)

        # Updated date
        self.date_label = QLabel(f"📅 {updated_str}")
        self.date_label.setStyleSheet("color: #777777; font-size: 11px;")
        layout.addWidget(self.date_label)

        # 4. Action Buttons (Open, Rename, Delete - Rename and Delete are hidden for example project)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)

        btn_open = QPushButton("Mở")
        btn_open.setToolTip("Mở dự án này")
        btn_open.clicked.connect(lambda: self.open_requested.emit(self.metadata.project_id))
        btn_layout.addWidget(btn_open)

        if not getattr(self.metadata, "is_example", False):
            btn_rename = QPushButton("Sửa tên")
            btn_rename.clicked.connect(lambda: self.rename_requested.emit(self.metadata.project_id))
            btn_layout.addWidget(btn_rename)

            btn_del = QPushButton("Xóa")
            btn_del.setObjectName("btnDelete")
            btn_del.clicked.connect(lambda: self.delete_requested.emit(self.metadata.project_id))
            btn_layout.addWidget(btn_del)

        layout.addLayout(btn_layout)

    def _load_thumbnail(self) -> None:
        """Nạp ảnh thumbnail nếu có file, ngược lại dùng icon/text mặc định."""
        thumb_path = Path(self.metadata.thumbnail_path) if self.metadata.thumbnail_path else None
        if thumb_path and thumb_path.is_file():
            pixmap = QPixmap(str(thumb_path))
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    260, 110, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
                )
                self.thumb_label.setPixmap(scaled)
                return

        # Fallback text/icon
        if self.metadata.video_path:
            self.thumb_label.setText("🎬 Video Project")
        else:
            self.thumb_label.setText("📄 Subtitle Project")

    def mousePressEvent(self, event) -> None:
        """Click vào card để phát tín hiệu mở dự án."""
        if event.button() == Qt.LeftButton:
            self.open_requested.emit(self.metadata.project_id)
        super().mousePressEvent(event)
