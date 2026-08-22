"""
src/ui/main_window.py
──────────────────────
QMainWindow chính của MVP2:

  HeaderBar
  ─────────────────────────────────────────────────────
  VideoPanel (stretch=1) │ Inspector (fixed width=280)
  ─────────────────────────────────────────────────────
  TimelinePlaceholder
  ─────────────────────────────────────────────────────
  ExportBar

State machine:
  State 1 — chưa có video:      drop zone / hint
  State 2 — video, chưa có SRT: video info, style controls
  State 3 — có subtitle:        style controls, chip list
  State 4 — clip được chọn:     text editor + style + Delete
"""
from __future__ import annotations

import threading
import uuid
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, Slot, QObject
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .header_bar          import HeaderBar
from .video_panel         import VideoPanel
from .inspector           import Inspector
from .timeline_placeholder import TimelinePlaceholder
from .export_bar          import ExportBar

from ..models import (
    EditorProject, SubtitleClip, SubtitleStyle,
    clips_from_srt, clips_to_ssa,
)
from ..ass_builder    import save_ass
from ..subtitle_parser import SubtitleError
from ..word_timing    import load_timing
from ..video_info     import probe_video, FFmpegNotFoundError, VideoReadError
from ..exporter import (
    export_video,
    ExportCancelledError, DiskSpaceError, ExportError,
)


# ──────────────────────────────────────────────────────────────────────────
# Worker thread
# ──────────────────────────────────────────────────────────────────────────

class ExportWorker(QObject):
    """Chạy FFmpeg trong thread riêng."""

    progress = Signal(float)
    finished = Signal(str)
    error    = Signal(str)

    def __init__(
        self,
        video_info,
        ass_path: str,
        output_path: str,
        cancel_event: threading.Event,
    ):
        super().__init__()
        self._video_info   = video_info
        self._ass_path     = ass_path
        self._output_path  = output_path
        self._cancel_event = cancel_event

    @Slot()
    def run(self) -> None:
        try:
            result = export_video(
                self._video_info, self._ass_path, self._output_path,
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
        self.setMinimumSize(1100, 700)
        self.resize(1280, 780)

        # ── Application state ──────────────────────────────────────────
        self._project: EditorProject     = EditorProject()
        self._selected_clip_id: str | None = None
        self._current_time_ms: int        = 0   # playhead — wire từ QMediaPlayer (bước 3)
        self._video_duration_ms: int      = 0   # duration từ QMediaPlayer

        # ── Export state ───────────────────────────────────────────────
        self._cancel_event: threading.Event | None = None
        self._export_thread: QThread | None        = None
        self._temp_ass: str | None                 = None

        self._build_ui()
        self._apply_stylesheet()
        self._update_ui_state()

    # ──────────────────────────────────────────────────────────────────────
    # Build UI
    # ──────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ─────────────────────────────────────────────────────
        self._header_bar = HeaderBar()
        self._header_bar.import_video_requested.connect(self._on_video_selected)
        self._header_bar.import_srt_requested.connect(self._on_srt_loaded)
        self._header_bar.import_json_requested.connect(self._on_json_loaded)
        self._header_bar.export_requested.connect(self._on_header_export)
        root.addWidget(self._header_bar)

        # Separator
        root.addWidget(self._make_hsep())

        # ── Main content: VideoPanel | Inspector ────────────────────────
        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)

        self._video_panel = VideoPanel()
        self._video_panel.video_selected.connect(self._on_video_selected)
        # ── Bước 3: wire playback signals ─────────────────────────────
        self._video_panel.time_changed.connect(self._on_time_changed)
        self._video_panel.duration_changed.connect(self._on_duration_changed)
        self._video_panel.playback_state_changed.connect(self._on_playback_state_changed)
        self._video_panel.playback_error.connect(self._on_playback_error)
        content.addWidget(self._video_panel, stretch=1)

        content.addWidget(self._make_vsep())

        self._inspector = Inspector()
        self._inspector.style_changed.connect(self._on_style_changed)
        self._inspector.clip_text_changed.connect(self._on_clip_text_changed)
        self._inspector.clip_delete_requested.connect(self._on_clip_delete_requested)
        content.addWidget(self._inspector)

        root.addLayout(content, stretch=1)

        # Separator
        root.addWidget(self._make_hsep())

        # ── Timeline Placeholder ────────────────────────────────────────
        self._timeline = TimelinePlaceholder()
        self._timeline.clip_selected.connect(self._on_clip_selected)
        self._timeline.clip_deselected.connect(self._on_clip_deselected)
        self._timeline.add_subtitle_requested.connect(self._on_add_subtitle_requested)
        # ── Bước 3: playback controls ──────────────────────────────────
        self._timeline.play_pause_requested.connect(self._video_panel.toggle_play_pause)
        self._timeline.seek_requested.connect(self._video_panel.seek)
        root.addWidget(self._timeline)


        # Separator
        root.addWidget(self._make_hsep())

        # ── Export Bar ──────────────────────────────────────────────────
        self._export_bar = ExportBar()
        self._export_bar.cancel_requested.connect(self._on_cancel_requested)
        root.addWidget(self._export_bar)

    @staticmethod
    def _make_hsep() -> QWidget:
        w = QWidget()
        w.setFixedHeight(1)
        w.setObjectName("HSeparator")
        return w

    @staticmethod
    def _make_vsep() -> QWidget:
        w = QWidget()
        w.setFixedWidth(1)
        w.setObjectName("VSeparator")
        return w

    # ──────────────────────────────────────────────────────────────────────
    # State management
    # ──────────────────────────────────────────────────────────────────────

    def _update_ui_state(self) -> None:
        """Master function: cập nhật toàn bộ UI dựa theo project state."""
        has_video = self._project.has_video
        has_clips = self._project.has_clips
        can_export = has_video and has_clips

        selected_clip = (
            self._project.clip_by_id(self._selected_clip_id)
            if self._selected_clip_id
            else None
        )

        # Header
        self._header_bar.set_has_video(has_video)
        self._header_bar.set_export_enabled(can_export)

        # Video panel
        if has_video:
            vi = self._project.video_info
            self._video_panel.set_video_info(
                name=vi.path.name,
                resolution=vi.resolution,
                duration_str=vi.duration_str,
                clip_count=len(self._project.clips),
            )

        # Inspector
        self._inspector.set_has_video(has_video)
        self._inspector.select_clip(selected_clip)

        # Timeline
        self._timeline.set_has_video(has_video)
        self._timeline.set_clips(
            self._project.sorted_clips() if has_clips else [],
            selected_clip_id=self._selected_clip_id,
        )
        self._timeline.set_current_time(self._current_time_ms, self._video_duration_ms)
        self._refresh_overlay()

        # Export bar

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

        self._project.video_info = info

        # ── Bước 3: load video vào player ─────────────────────────────
        self._current_time_ms = 0
        self._video_duration_ms = int(info.duration * 1000)
        self._video_panel.load_video(path)

        # Gợi ý output path
        default_out = str(Path("output") / (info.path.stem + "_subtitled.mp4"))
        self._export_bar.set_output_path(default_out)

        self._update_ui_state()

    # ──────────────────────────────────────────────────────────────────────
    # Slots – SRT
    # ──────────────────────────────────────────────────────────────────────

    @Slot(str)
    def _on_srt_loaded(self, path: str) -> None:
        try:
            clips = clips_from_srt(path)
        except FileNotFoundError as exc:
            self._show_error("File không tồn tại", str(exc))
            return
        except SubtitleError as exc:
            self._show_error("Lỗi subtitle", str(exc))
            return

        self._project.clips = clips
        self._selected_clip_id = None  # bỏ selection cũ khi load SRT mới

        # Word timing tuỳ chọn
        timing_path = Path(path).with_suffix(".words.json")
        try:
            self._project.word_timings = load_timing(timing_path)
        except (FileNotFoundError, ValueError):
            self._project.word_timings = None

        self._update_ui_state()

    # ──────────────────────────────────────────────────────────────────
    # Slots – JSON
    # ──────────────────────────────────────────────────────────────────

    @Slot(str)
    def _on_json_loaded(self, path: str) -> None:
        """
        Placeholder — sẽ implement ở bước 2 (json_subtitle_parser).
        Hiện tại chỉ thông báo file đã chọn để xác nhận UI hoạt động đúng.
        """
        from pathlib import Path as _Path
        self._show_error(
            "Coming soon 🔧",
            f"JSON parser chưa được triển khai.\n"
            f"File đã chọn: {_Path(path).name}\n\n"
            f"Sẽ implement ở bước 2 (todophu.md).",
        )

    # ──────────────────────────────────────────────────────────────────
    # Slots – Style
    # ──────────────────────────────────────────────────────────────────────

    @Slot(object)
    def _on_style_changed(self, style: SubtitleStyle) -> None:
        self._project.style = style
        # Cập nhật trạng thái nút Import JSON theo mode
        self._header_bar.set_highlight_mode(style.mode == "highlight")
        self._refresh_overlay()

    def _refresh_overlay(self) -> None:
        """Cập nhật subtitle overlay dựa theo current_time_ms và style hiện tại."""
        active = self._project.active_clip_at(self._current_time_ms)
        vi     = self._project.video_info
        word_timing = None
        if active and self._project.word_timings:
            # Export tạo SSA events từ sorted_clips(), nên dùng cùng index để
            # preview highlight đúng các mốc timing custom của export.
            clip_index = self._project.sorted_clips().index(active)
            word_timing = self._project.word_timings.get_line(clip_index)
        self._video_panel.set_active_clip(
            active, self._project.style, self._current_time_ms,
            video_width  = vi.width  if vi else 1920,
            video_height = vi.height if vi else 1080,
            word_timing=word_timing,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Slots – Clip operations
    # ──────────────────────────────────────────────────────────────────────

    @Slot(str, str)
    def _on_clip_text_changed(self, clip_id: str, new_text: str) -> None:
        """Cập nhật text của clip trong project khi người dùng sửa inspector."""
        clip = self._project.clip_by_id(clip_id)
        if clip:
            clip.text = new_text
            # Cập nhật chip trên timeline (không cần rebuild toàn bộ)
            self._timeline.set_clips(
                self._project.sorted_clips(),
                selected_clip_id=self._selected_clip_id,
            )
            self._refresh_overlay()


    @Slot(str)
    def _on_clip_delete_requested(self, clip_id: str) -> None:
        """Xóa clip khỏi project."""
        self._project.clips = [
            c for c in self._project.clips if c.id != clip_id
        ]
        self._selected_clip_id = None
        self._update_ui_state()

    @Slot()
    def _on_add_subtitle_requested(self) -> None:
        """Thêm clip 2 giây tại playhead và chọn ngay để sửa trong Inspector."""
        start_ms = self._current_time_ms
        new_clip = SubtitleClip(
            id=str(uuid.uuid4()),
            text="New subtitle",
            start_ms=start_ms,
            end_ms=start_ms + 2000,
        )
        self._project.clips.append(new_clip)
        self._selected_clip_id = new_clip.id
        self._update_ui_state()

    @Slot(str)
    def _on_clip_selected(self, clip_id: str) -> None:
        self._selected_clip_id = clip_id
        self._update_ui_state()

    @Slot()
    def _on_clip_deselected(self) -> None:
        self._selected_clip_id = None
        self._update_ui_state()

    # ──────────────────────────────────────────────────────────────────────
    # Slots – Bước 3: Playback
    # ──────────────────────────────────────────────────────────────────────

    @Slot(int)
    def _on_time_changed(self, ms: int) -> None:
        """
        Gọi mỗi khi QMediaPlayer.positionChanged phát ra.
        • Cập nhật current_time_ms.
        • Tìm subtitle active và refresh overlay (với video dims đúng).
        • Cập nhật time display trên timeline.
        """
        self._current_time_ms = ms
        self._refresh_overlay()
        self._timeline.set_current_time(ms, self._video_duration_ms)


    @Slot(bool)
    def _on_playback_state_changed(self, playing: bool) -> None:
        """Đồng bộ icon nút play/pause trên timeline."""
        self._timeline.set_playing(playing)

    @Slot(int)
    def _on_duration_changed(self, duration_ms: int) -> None:
        """Ưu tiên duration thực tế từ media backend khi nó đã sẵn sàng."""
        if duration_ms > 0:
            self._video_duration_ms = duration_ms
        self._timeline.set_current_time(self._current_time_ms, self._video_duration_ms)

    @Slot(str)
    def _on_playback_error(self, message: str) -> None:
        self._show_error("Không phát được video", message)

    # ──────────────────────────────────────────────────────────────────────
    # Slots – Export (header button)
    # ──────────────────────────────────────────────────────────────────────

    @Slot()
    def _on_header_export(self) -> None:
        """Header Export MP4 button → dùng path từ ExportBar."""
        output_path = self._export_bar.get_output_path()
        self._on_export_requested(output_path)

    # ──────────────────────────────────────────────────────────────────────
    # Slots – Export (ExportBar)
    # ──────────────────────────────────────────────────────────────────────

    def _build_ass_to_temp(self) -> bool:
        try:
            vi = self._project.video_info
            ass = clips_to_ssa(
                self._project.clips,
                self._project.style,
                video_width=vi.width if vi else 0,
                video_height=vi.height if vi else 0,
                word_timings=self._project.word_timings,
            )
            temp_dir = Path("temp")
            temp_dir.mkdir(exist_ok=True)
            ass_path = temp_dir / "subtitle_temp.ass"
            save_ass(ass, ass_path)
            self._temp_ass = str(ass_path)
            return True
        except Exception as exc:
            self._show_error("Không tạo được subtitle", str(exc))
            return False

    def _start_worker(self, output_path: str) -> None:
        self._cancel_event  = threading.Event()
        self._export_thread = QThread()
        self._worker = ExportWorker(
            self._project.video_info,
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
        self._header_bar.set_exporting(True)
        self._export_thread.start()

    @Slot()
    def _on_cancel_requested(self) -> None:
        if self._cancel_event:
            self._cancel_event.set()

    @Slot(str)
    def _on_export_requested(self, output_path: str) -> None:
        if not self._project.has_video or not self._project.has_clips:
            return
        if not self._build_ass_to_temp():
            return
        self._start_worker(output_path or "output/output.mp4")

    @Slot(str)
    def _on_export_finished(self, output_path: str) -> None:
        self._export_bar.finish_export_ui(success=True)
        self._header_bar.set_exporting(False)
        self._header_bar.set_export_enabled(
            self._project.has_video and self._project.has_clips
        )
        self._show_success(output_path)

    @Slot(str)
    def _on_export_error(self, msg: str) -> None:
        self._export_bar.finish_export_ui(success=False)
        self._header_bar.set_exporting(False)
        self._header_bar.set_export_enabled(
            self._project.has_video and self._project.has_clips
        )
        if msg != "__cancelled__":
            self._show_error("Lỗi export", msg)

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────

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

/* ══════════════════════════════════════════════════════════════════════
   HEADER BAR
   ══════════════════════════════════════════════════════════════════════ */
#HeaderBar {
    background-color: #0d0f15;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

#AppTitle {
    color: #e8eaf0;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.2px;
}

#HeaderSecBtn {
    background-color: rgba(255, 255, 255, 0.06);
    color: #9ba3bb;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 7px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 500;
}
#HeaderSecBtn:hover {
    background-color: rgba(255, 255, 255, 0.1);
    border-color: rgba(255, 255, 255, 0.18);
    color: #e8eaf0;
}
#HeaderSecBtn:pressed {
    background-color: rgba(255, 255, 255, 0.07);
}
#HeaderSecBtn:disabled {
    background-color: rgba(255, 255, 255, 0.03);
    color: rgba(155, 163, 187, 0.3);
    border-color: rgba(255, 255, 255, 0.05);
}

#HeaderExportBtn {
    background-color: #4f8aff;
    color: #fff;
    border: none;
    border-radius: 7px;
    padding: 6px 18px;
    font-size: 13px;
    font-weight: 600;
}
#HeaderExportBtn:hover:enabled {
    background-color: #6b9fff;
}
#HeaderExportBtn:pressed {
    background-color: #3d74e8;
}
#HeaderExportBtn:disabled {
    background-color: rgba(79, 138, 255, 0.2);
    color: rgba(255, 255, 255, 0.3);
}

/* ══════════════════════════════════════════════════════════════════════
   INSPECTOR
   ══════════════════════════════════════════════════════════════════════ */
#Inspector {
    background-color: #161a22;
    border-left: 1px solid rgba(255, 255, 255, 0.06);
}

#InspectorInner {
    background-color: #161a22;
}

#SectionHeader {
    color: #5b6278;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.4px;
}

#FieldLabel {
    color: #7a8099;
    font-size: 12px;
}

#AddSubtitleBtn {
    background-color: rgba(79, 138, 255, 0.08);
    color: #4f8aff;
    border: 1px solid rgba(79, 138, 255, 0.25);
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 12px;
    font-weight: 500;
}
#AddSubtitleBtn:hover:enabled {
    background-color: rgba(79, 138, 255, 0.16);
    border-color: rgba(79, 138, 255, 0.5);
    color: #7bb3ff;
}
#AddSubtitleBtn:pressed {
    background-color: rgba(79, 138, 255, 0.1);
}
#AddSubtitleBtn:disabled {
    background-color: rgba(79, 138, 255, 0.03);
    color: rgba(79, 138, 255, 0.3);
    border-color: rgba(79, 138, 255, 0.1);
}

#SubtitleTextEdit {
    background-color: #1e2230;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 8px;
    color: #e8eaf0;
    font-size: 13px;
    line-height: 1.5;
    selection-background-color: #2a3558;
}
#SubtitleTextEdit:focus {
    border-color: rgba(79, 138, 255, 0.5);
}

#DeleteBtn {
    background-color: rgba(255, 80, 80, 0.08);
    color: #ff6060;
    border: 1px solid rgba(255, 80, 80, 0.2);
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 12px;
    font-weight: 500;
}
#DeleteBtn:hover {
    background-color: rgba(255, 80, 80, 0.16);
    border-color: rgba(255, 80, 80, 0.4);
    color: #ff8080;
}
#DeleteBtn:pressed {
    background-color: rgba(255, 80, 80, 0.1);
}

#Divider {
    color: rgba(255, 255, 255, 0.06);
    border: none;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
    max-height: 1px;
}

/* ══════════════════════════════════════════════════════════════════════
   TIMELINE PLACEHOLDER
   ══════════════════════════════════════════════════════════════════════ */
#TimelinePanel {
    background-color: #0e1016;
}

#TimelineCtrlBar {
    background-color: #0e1016;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

#TimelineLabel {
    color: #3e4558;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.4px;
}

#TimelineScroll {
    background-color: #0e1016;
}
#TimelineClips {
    background-color: #0e1016;
}

#TimelineHint {
    color: #3e4558;
    font-size: 12px;
}

#PlayPauseBtn {
    background-color: rgba(79, 138, 255, 0.12);
    color: #4f8aff;
    border: 1px solid rgba(79, 138, 255, 0.3);
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
}
#PlayPauseBtn:hover:enabled {
    background-color: rgba(79, 138, 255, 0.22);
    border-color: rgba(79, 138, 255, 0.6);
    color: #7bb3ff;
}
#PlayPauseBtn:pressed { background-color: rgba(79, 138, 255, 0.1); }
#PlayPauseBtn:disabled {
    background-color: transparent;
    color: rgba(79, 138, 255, 0.25);
    border-color: rgba(79, 138, 255, 0.1);
}

#TimeDisplay {
    color: #5b6278;
    font-size: 11px;
    font-family: "JetBrains Mono", "Courier New", monospace;
    font-weight: 500;
}

/* Clip Chip */
#ClipChip {
    background-color: rgba(79, 138, 255, 0.08);
    border: 1px solid rgba(79, 138, 255, 0.2);
    border-radius: 8px;
}
#ClipChip:hover {
    background-color: rgba(79, 138, 255, 0.14);
    border-color: rgba(79, 138, 255, 0.4);
}
#ClipChip[selected="true"] {
    background-color: rgba(79, 138, 255, 0.22);
    border-color: rgba(79, 138, 255, 0.7);
}

#ChipTime {
    color: #4f8aff;
    font-size: 10px;
    font-family: "JetBrains Mono", "Courier New", monospace;
    font-weight: 500;
}
#ChipText {
    color: #c8ccd8;
    font-size: 11px;
}

/* ══════════════════════════════════════════════════════════════════════
   SHARED FORM CONTROLS
   ══════════════════════════════════════════════════════════════════════ */
QRadioButton {
    color: #c8ccd8;
    font-size: 13px;
    spacing: 8px;
}
QRadioButton::indicator {
    width: 15px; height: 15px;
    border-radius: 8px;
    border: 2px solid #3a3f50;
    background-color: #1e2230;
}
QRadioButton::indicator:checked {
    border-color: #4f8aff;
    background-color: #4f8aff;
}
QRadioButton:hover { color: #fff; }

QComboBox {
    background-color: #1e2230;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 7px;
    padding: 5px 10px;
    color: #c8ccd8;
    font-size: 12px;
    min-width: 130px;
}
QComboBox:hover { border-color: rgba(255, 255, 255, 0.2); }
QComboBox::drop-down { border: none; padding-right: 8px; }
QComboBox QAbstractItemView {
    background-color: #1e2230;
    border: 1px solid rgba(255, 255, 255, 0.1);
    selection-background-color: #2a2f42;
    color: #c8ccd8;
}

QSpinBox {
    background-color: #1e2230;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 7px;
    padding: 5px 8px;
    color: #c8ccd8;
    font-size: 12px;
    min-width: 75px;
}
QSpinBox:hover { border-color: rgba(255, 255, 255, 0.2); }
QSpinBox::up-button, QSpinBox::down-button {
    background: transparent; border: none; width: 14px;
}

QFormLayout QLabel {
    color: #7a8099;
    font-size: 12px;
    min-width: 72px;
}

/* ══════════════════════════════════════════════════════════════════════
   VIDEO PANEL
   ══════════════════════════════════════════════════════════════════════ */
#DropZone {
    background-color: #13161e;
    border: 2px dashed rgba(255, 255, 255, 0.08);
    border-radius: 0px;
}
#DropZone:hover {
    border-color: rgba(79, 138, 255, 0.3);
    background-color: rgba(79, 138, 255, 0.04);
}
#DropZone[dragHover="true"] {
    border-color: #4f8aff;
    background-color: rgba(79, 138, 255, 0.08);
}
#DropIcon  { font-size: 44px; }
#DropTitle { color: #c8ccd8; font-size: 15px; font-weight: 600; }
#DropSub   { color: #4a5168; font-size: 12px; }
#MetaBar   { background-color: #0e1016; }
#MetaLabel { color: #5b6278; font-size: 12px; }

/* ══════════════════════════════════════════════════════════════════════
   EXPORT BAR
   ══════════════════════════════════════════════════════════════════════ */
#ExportBar { background-color: #0d0f15; }

#PathEdit {
    background-color: #1e2230;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 7px;
    padding: 6px 12px;
    color: #c8ccd8;
    font-size: 12px;
}
#PathEdit:focus { border-color: rgba(79, 138, 255, 0.5); }

#BrowseBtn {
    background-color: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 7px;
    color: #7a8099;
    font-weight: 600;
    font-size: 14px;
}
#BrowseBtn:hover { background-color: rgba(255, 255, 255, 0.1); color: #fff; }

#CancelBtn {
    background-color: rgba(255, 80, 80, 0.12);
    color: #ff5050;
    border: 1px solid rgba(255, 80, 80, 0.3);
    border-radius: 7px;
    font-size: 12px;
}
#CancelBtn:hover { background-color: rgba(255, 80, 80, 0.22); }

QProgressBar#ExportProgress {
    background-color: rgba(255, 255, 255, 0.06);
    border: none;
    border-radius: 4px;
}
QProgressBar#ExportProgress::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #4f8aff, stop:1 #38cfff);
    border-radius: 4px;
}

#TimerLabel {
    color: #5b6278;
    font-size: 11px;
    font-family: "JetBrains Mono", "Courier New", monospace;
}

/* ══════════════════════════════════════════════════════════════════════
   SCROLL + MESSAGE
   ══════════════════════════════════════════════════════════════════════ */
QScrollArea { background: transparent; }
QScrollBar:vertical {
    background: transparent;
    width: 5px;
}
QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 0.12);
    border-radius: 2px;
    min-height: 30px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }

QScrollBar:horizontal {
    background: transparent;
    height: 5px;
}
QScrollBar::handle:horizontal {
    background: rgba(255, 255, 255, 0.12);
    border-radius: 2px;
    min-width: 30px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }

QMessageBox { background-color: #1a1e2a; }
QMessageBox QPushButton {
    background-color: rgba(255, 255, 255, 0.08);
    color: #c8ccd8;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 7px;
    padding: 6px 18px;
    min-width: 80px;
}
QMessageBox QPushButton:hover { background-color: rgba(255, 255, 255, 0.14); }
"""
