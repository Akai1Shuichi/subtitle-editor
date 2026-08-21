"""
src/ui/export_bar.py
─────────────────────
Thanh dưới cùng: chọn output path, progress bar, Cancel, timer.
"""
from __future__ import annotations

import threading
import time

from PySide6.QtCore import Qt, Signal, QTimer, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class ExportBar(QWidget):
    """
    Thanh export ở cuối cửa sổ.

    Signals
    -------
    cancel_requested()                  – người dùng nhấn Cancel
    """

    cancel_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ExportBar")
        self.setFixedHeight(90)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 10, 20, 10)
        outer.setSpacing(8)

        # ── Row 1: output path ───────────────────────────────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Thư mục / tên file output…")
        self._path_edit.setObjectName("PathEdit")
        row1.addWidget(self._path_edit, stretch=1)

        browse_btn = QPushButton("…")
        browse_btn.setObjectName("BrowseBtn")
        browse_btn.setFixedWidth(36)
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setToolTip("Chọn thư mục output")
        browse_btn.clicked.connect(self._pick_output)
        row1.addWidget(browse_btn)

        outer.addLayout(row1)

        # ── Row 2: progress bar + timer + cancel ─────────────────────────
        row2 = QHBoxLayout()
        row2.setSpacing(10)

        self._progress = QProgressBar()
        self._progress.setObjectName("ExportProgress")
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(8)
        row2.addWidget(self._progress, stretch=1)

        self._timer_label = QLabel("00:00")
        self._timer_label.setObjectName("TimerLabel")
        self._timer_label.setAlignment(Qt.AlignCenter)
        self._timer_label.setFixedWidth(50)
        row2.addWidget(self._timer_label)

        self._cancel_btn = QPushButton("Hủy")
        self._cancel_btn.setObjectName("CancelBtn")
        self._cancel_btn.setFixedWidth(60)
        self._cancel_btn.setCursor(Qt.PointingHandCursor)
        self._cancel_btn.setVisible(False)
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)
        row2.addWidget(self._cancel_btn)

        outer.addLayout(row2)

        # ── Timer nội bộ ─────────────────────────────────────────────────
        self._elapsed_secs = 0
        self._qtimer = QTimer(self)
        self._qtimer.setInterval(1000)
        self._qtimer.timeout.connect(self._tick)

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def output_path(self) -> str:
        return self._path_edit.text().strip()

    def get_output_path(self) -> str:
        """Alias cho output_path() — dùng từ MainWindow header export."""
        return self._path_edit.text().strip()

    def set_output_path(self, path: str) -> None:
        self._path_edit.setText(path)

    @Slot(float)
    def update_progress(self, percent: float) -> None:
        """Gọi từ worker thread (qua signal) để cập nhật progress bar."""
        self._progress.setValue(int(percent))

    def start_export_ui(self) -> None:
        """Chuyển UI sang trạng thái đang export."""
        self._cancel_btn.setVisible(True)
        self._progress.setValue(0)
        self._elapsed_secs = 0
        self._timer_label.setText("00:00")
        self._qtimer.start()

    def finish_export_ui(self, success: bool = True) -> None:
        """Kết thúc export (thành công hoặc lỗi/hủy)."""
        self._qtimer.stop()
        self._cancel_btn.setVisible(False)
        if success:
            self._progress.setValue(100)
        else:
            self._progress.setValue(0)

    # ──────────────────────────────────────────────────────────────────────
    # Slots
    # ──────────────────────────────────────────────────────────────────────

    def _pick_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Lưu video output",
            self._path_edit.text() or "output/output.mp4",
            "MP4 Video (*.mp4)",
        )
        if path:
            self._path_edit.setText(path)

    def _on_cancel_clicked(self) -> None:
        self.cancel_requested.emit()

    def _tick(self) -> None:
        self._elapsed_secs += 1
        m, s = divmod(self._elapsed_secs, 60)
        self._timer_label.setText(f"{m:02d}:{s:02d}")
