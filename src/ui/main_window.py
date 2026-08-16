"""
src/ui/main_window.py
──────────────────────
QMainWindow chính: ghép VideoPanel + Sidebar + ExportBar,
điều phối logic giữa các widget và các module backend.
"""
from __future__ import annotations

import threading
import tempfile
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, Slot, QObject
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .video_panel import VideoPanel
from .sidebar import Sidebar
from .export_bar import ExportBar

from ..subtitle_parser import load_srt, count_lines, SubtitleError
from ..ass_builder import build_ass, save_ass
from ..video_info import probe_video, VideoInfo, FFmpegNotFoundError, VideoReadError
from ..exporter import export_video, ExportCancelledError, DiskSpaceError, ExportError


# ──────────────────────────────────────────────────────────────────────────
# Worker thread (để không block UI)
# ──────────────────────────────────────────────────────────────────────────

class ExportWorker(QObject):
    """Chạy FFmpeg trong thread riêng, gửi progress / kết quả về UI thread."""

    progress = Signal(float)
    finished = Signal(str)    # path của file output
    error = Signal(str)       # message lỗi

    def __init__(
        self,
        video_info: VideoInfo,
        ass_path: str,
        output_path: str,
        cancel_event: threading.Event,
    ):
        super().__init__()
        self._video_info = video_info
        self._ass_path = ass_path
        self._output_path = output_path
        self._cancel_event = cancel_event

    @Slot()
    def run(self) -> None:
        try:
            result = export_video(
                self._video_info,
                self._ass_path,
                self._output_path,
                cancel_event=self._cancel_event,
                on_progress=lambda pct: self.progress.emit(pct),
            )
            self.finished.emit(str(result))
        except ExportCancelledError:
            self.error.emit("__cancelled__")
        except DiskSpaceError as exc:
            self.error.emit(str(exc))
        except (ExportError, FFmpegNotFoundError, VideoReadError) as exc:
            self.error.emit(str(exc))
        except Exception as exc:
            self.error.emit(f"Lỗi không xác định: {exc}")


# ──────────────────────────────────────────────────────────────────────────
# Main Window
# ──────────────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Subtitle Video Editor")
        self.setMinimumSize(1000, 650)
        self.resize(1200, 720)

        # State
        self._video_info: VideoInfo | None = None
        self._srt_path: str | None = None
        self._cancel_event: threading.Event | None = None
        self._export_thread: QThread | None = None
        self._temp_ass: str | None = None

        self._build_ui()
        self._apply_stylesheet()

    # ──────────────────────────────────────────────────────────────────────
    # Build UI
    # ──────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top: video panel + sidebar ────────────────────────────────────
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(0)

        self._video_panel = VideoPanel()
        self._video_panel.video_selected.connect(self._on_video_selected)
        top.addWidget(self._video_panel, stretch=1)

        # Vertical separator
        sep = QWidget()
        sep.setFixedWidth(1)
        sep.setObjectName("VSeparator")
        top.addWidget(sep)

        self._sidebar = Sidebar()
        self._sidebar.srt_loaded.connect(self._on_srt_loaded)
        self._sidebar.style_changed.connect(self._on_style_changed)
        top.addWidget(self._sidebar)

        root.addLayout(top, stretch=1)

        # ── Horizontal separator ──────────────────────────────────────────
        hsep = QWidget()
        hsep.setFixedHeight(1)
        hsep.setObjectName("HSeparator")
        root.addWidget(hsep)

        # ── Bottom: export bar ────────────────────────────────────────────
        self._export_bar = ExportBar()
        self._export_bar.export_requested.connect(self._on_export_requested)
        self._export_bar.cancel_requested.connect(self._on_cancel_requested)
        root.addWidget(self._export_bar)

    # ──────────────────────────────────────────────────────────────────────
    # Slots – Video
    # ──────────────────────────────────────────────────────────────────────

    @Slot(str)
    def _on_video_selected(self, path: str) -> None:
        try:
            info = probe_video(path)
        except FFmpegNotFoundError as exc:
            self._show_error("FFmpeg không tìm thấy", str(exc))
            return
        except VideoReadError as exc:
            self._show_error("Không đọc được video", str(exc))
            return
        except FileNotFoundError as exc:
            self._show_error("File không tồn tại", str(exc))
            return

        self._video_info = info
        self._video_panel.set_video_info(
            name=info.path.name,
            resolution=info.resolution,
            duration_str=info.duration_str,
        )

        # Gợi ý output path
        default_out = str(
            Path("output") / (info.path.stem + "_subtitled.mp4")
        )
        self._export_bar.set_output_path(default_out)
        self._update_export_btn()

    # ──────────────────────────────────────────────────────────────────────
    # Slots – SRT
    # ──────────────────────────────────────────────────────────────────────

    @Slot(str)
    def _on_srt_loaded(self, path: str) -> None:
        try:
            subs = load_srt(path)
            n = count_lines(subs)
        except FileNotFoundError as exc:
            self._show_error("File không tồn tại", str(exc))
            return
        except SubtitleError as exc:
            self._show_error("Lỗi subtitle", str(exc))
            return

        self._srt_path = path
        self._sidebar.set_srt_info(path, n)
        self._update_export_btn()

    # ──────────────────────────────────────────────────────────────────────
    # Slots – Style changed
    # ──────────────────────────────────────────────────────────────────────

    @Slot(dict)
    def _on_style_changed(self, settings: dict) -> None:
        # Có thể dùng sau để cập nhật preview
        pass

    # ──────────────────────────────────────────────────────────────────────
    # Slots – Export
    # ──────────────────────────────────────────────────────────────────────

    @Slot(str)
    def _on_export_requested(self, output_path: str) -> None:
        if not self._video_info or not self._srt_path:
            return

        # Build ASS file tạm
        try:
            subs = load_srt(self._srt_path)
            settings = self._sidebar.get_style_settings()
            ass = build_ass(
                subs,
                mode=settings["mode"],
                fontname=settings["fontname"],
                fontsize=settings["fontsize"],
                text_color=settings["text_color"],
                highlight_color=settings["highlight_color"],
                alignment=settings["alignment"],
            )
            # Lưu ra temp/
            temp_dir = Path("temp")
            temp_dir.mkdir(exist_ok=True)
            ass_path = temp_dir / "subtitle_temp.ass"
            save_ass(ass, ass_path)
            self._temp_ass = str(ass_path)
        except Exception as exc:
            self._show_error("Không tạo được subtitle", str(exc))
            return

        # Khởi chạy export thread
        self._cancel_event = threading.Event()
        self._export_thread = QThread()
        self._worker = ExportWorker(
            self._video_info,
            self._temp_ass,
            output_path,
            self._cancel_event,
        )
        self._worker.moveToThread(self._export_thread)
        self._export_thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._export_bar.update_progress)
        self._worker.finished.connect(self._on_export_finished)
        self._worker.error.connect(self._on_export_error)
        self._worker.finished.connect(self._export_thread.quit)
        self._worker.error.connect(self._export_thread.quit)

        self._export_bar.start_export_ui()
        self._export_thread.start()

    @Slot()
    def _on_cancel_requested(self) -> None:
        if self._cancel_event:
            self._cancel_event.set()

    @Slot(str)
    def _on_export_finished(self, output_path: str) -> None:
        self._export_bar.finish_export_ui(success=True)
        self._show_success(output_path)

    @Slot(str)
    def _on_export_error(self, msg: str) -> None:
        self._export_bar.finish_export_ui(success=False)
        if msg != "__cancelled__":
            self._show_error("Lỗi export", msg)

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────

    def _update_export_btn(self) -> None:
        ready = bool(self._video_info and self._srt_path)
        self._export_bar.set_export_enabled(ready)

    def _show_error(self, title: str, msg: str) -> None:
        dlg = QMessageBox(self)
        dlg.setWindowTitle(title)
        dlg.setText(msg)
        dlg.setIcon(QMessageBox.Critical)
        dlg.exec()

    def _show_success(self, output_path: str) -> None:
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Export thành công ✅")
        dlg.setText(f"Video đã được lưu tại:\n{output_path}")
        dlg.setIcon(QMessageBox.Information)
        open_btn = dlg.addButton("Mở thư mục", QMessageBox.ActionRole)
        dlg.addButton("Đóng", QMessageBox.AcceptRole)
        dlg.exec()
        if dlg.clickedButton() is open_btn:
            import subprocess, platform
            folder = str(Path(output_path).parent)
            if platform.system() == "Windows":
                subprocess.Popen(["explorer", folder])
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])

    # ──────────────────────────────────────────────────────────────────────
    # Stylesheet
    # ──────────────────────────────────────────────────────────────────────

    def _apply_stylesheet(self) -> None:
        self.setStyleSheet(STYLESHEET)


# ──────────────────────────────────────────────────────────────────────────
# QSS Theme
# ──────────────────────────────────────────────────────────────────────────

STYLESHEET = """
/* ── Base ─────────────────────────────────────────────────────────────── */
QMainWindow, QWidget {
    background-color: #111318;
    color: #e8eaf0;
    font-family: "Inter", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

/* ── Separators ────────────────────────────────────────────────────────── */
#VSeparator, #HSeparator {
    background-color: rgba(255, 255, 255, 0.06);
}

/* ── Sidebar ───────────────────────────────────────────────────────────── */
#Sidebar, #SidebarInner {
    background-color: #161a22;
}

#SectionHeader {
    color: #5b6278;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    margin-bottom: 2px;
}

#Divider {
    color: rgba(255, 255, 255, 0.06);
    border: none;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
}

#SrtLabel {
    color: #c8ccd8;
    font-size: 12px;
}

#SrtMeta {
    color: #5b6278;
    font-size: 11px;
}

/* ── Import SRT Button ─────────────────────────────────────────────────── */
#ImportBtn {
    background-color: rgba(255, 255, 255, 0.06);
    color: #c8ccd8;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px;
    font-weight: 500;
}
#ImportBtn:hover {
    background-color: rgba(255, 255, 255, 0.1);
    border-color: rgba(255, 255, 255, 0.18);
    color: #fff;
}
#ImportBtn:pressed {
    background-color: rgba(255, 255, 255, 0.07);
}

/* ── Radio buttons ─────────────────────────────────────────────────────── */
QRadioButton {
    color: #c8ccd8;
    font-size: 13px;
    spacing: 8px;
}
QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 2px solid #3a3f50;
    background-color: #1e2230;
}
QRadioButton::indicator:checked {
    border-color: #4f8aff;
    background-color: #4f8aff;
}
QRadioButton:hover {
    color: #fff;
}

/* ── ComboBox ──────────────────────────────────────────────────────────── */
QComboBox {
    background-color: #1e2230;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 7px;
    padding: 5px 10px;
    color: #c8ccd8;
    font-size: 12px;
    min-width: 140px;
}
QComboBox:hover {
    border-color: rgba(255,255,255,0.2);
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #1e2230;
    border: 1px solid rgba(255,255,255,0.1);
    selection-background-color: #2a2f42;
    color: #c8ccd8;
}

/* ── SpinBox ───────────────────────────────────────────────────────────── */
QSpinBox {
    background-color: #1e2230;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 7px;
    padding: 5px 8px;
    color: #c8ccd8;
    font-size: 12px;
    min-width: 80px;
}
QSpinBox:hover {
    border-color: rgba(255,255,255,0.2);
}
QSpinBox::up-button, QSpinBox::down-button {
    background: transparent;
    border: none;
    width: 14px;
}

/* ── Form labels ───────────────────────────────────────────────────────── */
QFormLayout QLabel {
    color: #7a8099;
    font-size: 12px;
    min-width: 68px;
}

/* ── Drop Zone ─────────────────────────────────────────────────────────── */
#DropZone {
    background-color: #13161e;
    border: 2px dashed rgba(255,255,255,0.1);
    border-radius: 0px;
}
#DropZone:hover {
    border-color: rgba(79,138,255,0.35);
    background-color: rgba(79,138,255,0.04);
}
#DropZone[dragHover="true"] {
    border-color: #4f8aff;
    background-color: rgba(79,138,255,0.08);
}
#DropIcon {
    font-size: 42px;
}
#DropTitle {
    color: #c8ccd8;
    font-size: 15px;
    font-weight: 600;
}
#DropSub {
    color: #4a5168;
    font-size: 12px;
}

/* ── Meta Bar ──────────────────────────────────────────────────────────── */
#MetaBar {
    background-color: #0e1016;
}
#MetaLabel {
    color: #5b6278;
    font-size: 12px;
}

/* ── Export Bar ────────────────────────────────────────────────────────── */
#ExportBar {
    background-color: #0e1016;
}

#PathEdit {
    background-color: #1e2230;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 7px;
    padding: 6px 12px;
    color: #c8ccd8;
    font-size: 12px;
}
#PathEdit:focus {
    border-color: rgba(79,138,255,0.5);
}

#BrowseBtn {
    background-color: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 7px;
    color: #7a8099;
    font-weight: 600;
    font-size: 14px;
}
#BrowseBtn:hover {
    background-color: rgba(255,255,255,0.1);
    color: #fff;
}

/* ── Export Button ─────────────────────────────────────────────────────── */
#ExportBtn {
    background-color: #4f8aff;
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 7px 18px;
    font-size: 13px;
    font-weight: 600;
}
#ExportBtn:hover:enabled {
    background-color: #6b9fff;
}
#ExportBtn:pressed {
    background-color: #3d74e8;
}
#ExportBtn:disabled {
    background-color: rgba(79,138,255,0.25);
    color: rgba(255,255,255,0.3);
}

/* ── Cancel Button ─────────────────────────────────────────────────────── */
#CancelBtn {
    background-color: rgba(255, 80, 80, 0.12);
    color: #ff5050;
    border: 1px solid rgba(255,80,80,0.3);
    border-radius: 7px;
    font-size: 12px;
}
#CancelBtn:hover {
    background-color: rgba(255, 80, 80, 0.22);
}

/* ── Progress Bar ──────────────────────────────────────────────────────── */
QProgressBar#ExportProgress {
    background-color: rgba(255,255,255,0.06);
    border: none;
    border-radius: 4px;
}
QProgressBar#ExportProgress::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #4f8aff, stop:1 #38cfff);
    border-radius: 4px;
}

/* ── Timer Label ───────────────────────────────────────────────────────── */
#TimerLabel {
    color: #5b6278;
    font-size: 11px;
    font-family: "JetBrains Mono", "Courier New", monospace;
}

/* ── Scroll Area ───────────────────────────────────────────────────────── */
QScrollArea {
    background: transparent;
}
QScrollBar:vertical {
    background: transparent;
    width: 5px;
}
QScrollBar::handle:vertical {
    background: rgba(255,255,255,0.12);
    border-radius: 2px;
    min-height: 30px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* ── Message Box ───────────────────────────────────────────────────────── */
QMessageBox {
    background-color: #1a1e2a;
}
QMessageBox QPushButton {
    background-color: rgba(255,255,255,0.08);
    color: #c8ccd8;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 7px;
    padding: 6px 18px;
    min-width: 80px;
}
QMessageBox QPushButton:hover {
    background-color: rgba(255,255,255,0.14);
}
"""
