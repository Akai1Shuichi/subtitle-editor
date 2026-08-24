"""
src/ui/video_panel.py
──────────────────────
Bước 3: Video Playback & Realtime Preview.

Panel trái gồm:
  • State 1 (no video): DropZone kéo-thả / click chọn file
  • State 2+ (has video): VideoCanvas — QVideoSink-based widget paint cả
      video frame lẫn subtitle overlay trong một paintEvent duy nhất.
      Cách này tránh vấn đề QVideoWidget che khuất child widgets trên Linux/xcb/Wayland.

Signals
-------
video_selected(path: str)          – người dùng chọn video (drop / pick)
time_changed(ms: int)              – position video thay đổi
playback_state_changed(bool)       – True = đang play, False = pause/stop
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import (
    Qt, QUrl, QRect, Signal, Slot,
)
from PySide6.QtGui import (
    QColor, QDragEnterEvent, QDropEvent, QFont, QFontMetrics,
    QImage, QPainter, QPainterPath, QPen,
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QVideoSink, QVideoFrame
from PySide6.QtWidgets import (
    QFileDialog, QLabel,
    QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)

from ..models import SubtitleClip, SubtitleStyle, style_to_subtitle_settings
from ..ass_builder import SubtitleRenderer, SubtitleSegment
from ..word_timing import LineTiming


# ──────────────────────────────────────────────────────────────────────────────
# VideoPanel
# ──────────────────────────────────────────────────────────────────────────────

class VideoPanel(QWidget):
    """
    Panel trái. Chuyển qua lại giữa DropZone và VideoCanvas.

    Public API
    ----------
    load_video(path)              – load video mới vào player
    seek(ms)                      – seek đến vị trí ms
    toggle_play_pause()           – play/pause
    set_active_clip(clip, style, current_ms) – cập nhật subtitle overlay
    set_video_info(...)           – cập nhật meta bar
    """

    video_selected          = Signal(str)       # path
    time_changed            = Signal(int)       # ms
    duration_changed        = Signal(int)       # ms
    playback_state_changed  = Signal(bool)      # True=play
    playback_error          = Signal(str)       # backend không mở/phát được media

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("VideoPanel")
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Stacked: DropZone (index 0) | VideoCanvas (index 1) ───────────
        self._stack = QStackedWidget()
        self._stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Page 0: Drop zone
        self._drop_zone = _DropZone()
        self._drop_zone.clicked.connect(self._pick_video)
        self._stack.addWidget(self._drop_zone)

        # Page 1: VideoCanvas (paint video frame + subtitle overlay)
        self._canvas = VideoCanvas()
        self._stack.addWidget(self._canvas)

        root.addWidget(self._stack, stretch=1)

        # ── Meta bar ───────────────────────────────────────────────────────
        self._meta_bar = _MetaBar()
        self._meta_bar.hide()
        root.addWidget(self._meta_bar)

        # ── Media player — dùng QVideoSink thay vì QVideoWidget ───────────
        self._player = QMediaPlayer(self)
        self._audio  = QAudioOutput(self)
        self._player.setAudioOutput(self._audio)
        self._audio.setVolume(0.8)

        # VideoSink nhận frame và chuyển cho canvas
        self._sink = QVideoSink(self)
        self._player.setVideoSink(self._sink)
        self._sink.videoFrameChanged.connect(self._canvas.on_video_frame)

        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.playbackStateChanged.connect(self._on_playback_state_changed)
        self._player.errorOccurred.connect(self._on_error)

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def load_video(self, path: str) -> None:
        """Load video mới vào player và chuyển sang trang canvas."""
        # Dừng và xoá frame cũ trước khi gán source mới, tránh flash frame/subtitle
        # của video trước trong lúc backend đang mở file mới.
        self._player.stop()
        self._canvas.reset_video()
        self._player.setSource(QUrl.fromLocalFile(path))
        self._stack.setCurrentIndex(1)
        self._player.pause()

    def seek(self, ms: int) -> None:
        self._player.setPosition(ms)

    def toggle_play_pause(self) -> None:
        if self._player.playbackState() == QMediaPlayer.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def set_active_clip(
        self,
        clip: Optional[SubtitleClip],
        style: SubtitleStyle,
        current_ms: int = 0,
        *,
        video_width: int = 1920,
        video_height: int = 1080,
        word_timing: Optional[LineTiming] = None,
    ) -> None:
        """Cập nhật subtitle overlay — canvas tự repaint."""
        self._canvas.set_active_clip(
            clip, style, current_ms,
            video_width=video_width, video_height=video_height,
            word_timing=word_timing,
        )

    def set_video_info(
        self,
        name: str,
        resolution: str,
        duration_str: str,
        clip_count: int = 0,
    ) -> None:
        self._meta_bar.set_info(name, resolution, duration_str)
        self._meta_bar.show()

    def update_clip_count(self, count: int) -> None:
        pass

    def clear(self) -> None:
        self._player.stop()
        self._player.setSource(QUrl())
        self._stack.setCurrentIndex(0)
        self._meta_bar.hide()
        self._canvas.set_active_clip(None, SubtitleStyle())

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
            self.video_selected.emit(urls[0].toLocalFile())

    # ──────────────────────────────────────────────────────────────────────
    # Private slots
    # ──────────────────────────────────────────────────────────────────────

    def _pick_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn video", "",
            "Video Files (*.mp4 *.mov *.avi *.mkv *.webm *.m4v);;All Files (*)",
        )
        if path:
            self.video_selected.emit(path)

    @Slot(int)
    def _on_position_changed(self, ms: int) -> None:
        self.time_changed.emit(ms)

    @Slot(int)
    def _on_duration_changed(self, ms: int) -> None:
        self.duration_changed.emit(max(0, ms))

    @Slot(object, str)
    def _on_error(self, _error, message: str) -> None:
        """Chuyển lỗi codec/media từ Qt backend ra cửa sổ chính."""
        if message:
            self.playback_error.emit(message)

    @Slot(object)
    def _on_playback_state_changed(self, state) -> None:
        self.playback_state_changed.emit(state == QMediaPlayer.PlayingState)


# ──────────────────────────────────────────────────────────────────────────────
# VideoCanvas — widget duy nhất paint cả video frame + subtitle
# ──────────────────────────────────────────────────────────────────────────────

class VideoCanvas(QWidget):
    """
    Widget nhận QVideoFrame từ QVideoSink, convert sang QImage và paint
    cùng với subtitle overlay trong một paintEvent.

    Lý do không dùng QVideoWidget:
    Trên Linux (xcb/Wayland), QVideoWidget render qua GPU và che khuất
    tất cả child QWidget đặt đè lên, kể cả WA_TranslucentBackground.
    Cách này đảm bảo subtitle luôn hiển thị trên mọi platform.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("VideoCanvas")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background: #000;")

        self._current_frame:  Optional[QImage]      = None
        self._clip:           Optional[SubtitleClip] = None
        self._style:          SubtitleStyle          = SubtitleStyle()
        self._current_ms:     int                    = 0
        self._video_width:    int                    = 1920   # kích thước thực của video nguồn
        self._video_height:   int                    = 1080   # dùng để scale font giống ASS export
        self._word_timing:    Optional[LineTiming]   = None

        # Cache segments highlight để tránh tính lại mỗi frame
        self._cached_clip_id: Optional[str]    = None
        self._cached_segments: list            = []

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    @Slot(QVideoFrame)
    def on_video_frame(self, frame: QVideoFrame) -> None:
        """Nhận frame mới từ QVideoSink, convert và repaint."""
        img = frame.toImage()
        if not img.isNull():
            self._current_frame = img
            self.update()   # trigger paintEvent

    def set_active_clip(
        self,
        clip: Optional[SubtitleClip],
        style: SubtitleStyle,
        current_ms: int = 0,
        *,
        video_width:  int = 1920,
        video_height: int = 1080,
        word_timing: Optional[LineTiming] = None,
    ) -> None:
        # Nếu clip khác → reset cache segments
        new_clip_id = clip.id if clip else None
        if new_clip_id != self._cached_clip_id:
            self._cached_clip_id   = new_clip_id
            self._cached_segments  = []

        self._clip         = clip
        self._style        = style
        self._current_ms   = current_ms
        self._video_width  = video_width
        self._video_height = video_height
        self._word_timing  = word_timing
        self.update()

    def reset_video(self) -> None:
        """Xoá frame và overlay của source cũ trước khi load video mới."""
        self._current_frame = None
        self._clip = None
        self._cached_clip_id = None
        self._cached_segments = []
        self.update()

    # ──────────────────────────────────────────────────────────────────────
    # Paint
    # ──────────────────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        w, h = self.width(), self.height()

        # 1. Vẽ video frame (letterbox — giữ aspect ratio)
        if self._current_frame and not self._current_frame.isNull():
            fw = self._current_frame.width()
            fh = self._current_frame.height()
            if fw > 0 and fh > 0:
                # Tính rect letterbox
                scale = min(w / fw, h / fh)
                dw = int(fw * scale)
                dh = int(fh * scale)
                dx = (w - dw) // 2
                dy = (h - dh) // 2
                painter.drawImage(QRect(dx, dy, dw, dh), self._current_frame)
                # Vùng vẽ subtitle tính theo letterbox rect
                self._draw_subtitle(painter, dx, dy, dw, dh)
            else:
                painter.fillRect(0, 0, w, h, QColor("#000"))
        else:
            painter.fillRect(0, 0, w, h, QColor("#000"))

        painter.end()

    @staticmethod
    def _wrap_text(fm: QFontMetrics, text: str, max_width: int) -> list[str]:
        """
        Word-wrap text để fit trong max_width pixels.
        Giữ nguyên dấu xuống dòng "\n" từ SRT, và wrap thêm nếu line vẫn quá dài.
        """
        result: list[str] = []
        for paragraph in text.split("\n"):
            words = paragraph.split()
            if not words:
                result.append("")
                continue
            current = ""
            for word in words:
                candidate = (current + " " + word).strip()
                if fm.horizontalAdvance(candidate) <= max_width:
                    current = candidate
                else:
                    if current:
                        result.append(current)
                    current = word
            if current:
                result.append(current)
        return result if result else [""]

    @staticmethod
    def _line_x(area_x: int, area_w: int, line_width: int, alignment: int) -> int:
        """Căn ngang theo cùng mã alignment ASS (1–9)."""
        if alignment in (1, 4, 7):
            return area_x
        if alignment in (3, 6, 9):
            return area_x + area_w - line_width
        return area_x + (area_w - line_width) // 2

    def _draw_subtitle(
        self,
        painter: QPainter,
        vx: int, vy: int, vw: int, vh: int,
    ) -> None:
        """
        Vẽ subtitle overlay bên trong vùng letterbox (vx, vy, vw, vh).

        Font size và margin được scale giống hệt ASS export:
        - fontsize ASS được quy đổi từ 72 DPI sang canvas Qt 96 DPI
        - margin ngang trong ASS = marginl=60, marginr=60 px trong video_width gốc
        - marginv trong ASS = (100 - position_y) * video_height / 100 px từ đáy
        Tất cả đều được scale theo tỉ lệ vw/video_width và vh/video_height.
        """
        if not self._clip:
            return

        style = self._style

        # ── Font size: scale đúng theo kích thước video thực tế ────────────
        # libass diễn giải Fontsize trong hệ 72 DPI, trong khi QFont pixelSize
        # là pixel logic 96 DPI. Không quy đổi sẽ làm realtime lớn 4/3 so với
        # video đã render. Hệ số này được áp dụng trước khi scale preview.
        src_h    = max(1, self._video_height)
        src_w    = max(1, self._video_width)
        font_px = max(1, round(style.fontsize * (72 / 96) * vh / src_h))
        # Dùng pixelSize để không bị phụ thuộc DPI màn hình.
        font = QFont(style.fontname)
        font.setPixelSize(font_px)
        font.setBold(True)
        painter.setFont(font)
        fm = QFontMetrics(font)

        # ── Margin ngang: tính từ subtitle_width (%) ────────────────────────────
        # subtitle_width = % chiều rộng video mà subtitle chiếm.
        # margin_x = phần thừa hai bên chia đôi.
        width_pct = getattr(style, "subtitle_width", 80)
        margin_x  = max(4, int((100 - width_pct) / 200 * vw))
        safe_w    = max(100, vw - margin_x * 2)

        # ── Vị trí Y: cùng semantics với ASS MarginV ──────────────────────
        if style.alignment in (2, 3, 1):   # bottom
            margin_v = max(0, int((100 - style.position_y) * vh / 100))
            base_y   = vy + vh - margin_v
        elif style.alignment in (5, 6, 4): # center
            base_y   = vy + vh // 2
        else:                               # top
            base_y   = vy + int(style.position_y * vh / 100)

        text_color   = QColor(*style.text_color)
        hl_color     = QColor(*style.highlight_color)
        stroke_color = QColor(*style.stroke_color)
        scale_y      = vh / src_h
        stroke_w     = style.stroke_width * scale_y
        shadow_offset = style.shadow * scale_y

        if style.mode in ("highlight", "punch"):
            self._paint_highlight_segment(
                painter, fm, safe_w, margin_x, vx, vy, vw, vh, base_y,
                text_color, hl_color, stroke_color, stroke_w, shadow_offset,
                is_punch=(style.mode == "punch"),
            )
        elif style.mode in ("soft_pop", "soft-pop"):
            wrapped = self._wrap_text(fm, self._clip.text, safe_w)
            elapsed_ms = self._current_ms - self._clip.start_ms
            if elapsed_ms < 0:
                return

            # Soft Pop entrance animation:
            # 0-100ms: scale 0.92 -> overshoot 1.04
            # 100-180ms: scale 1.04 -> end 1.00
            # > 180ms: scale 1.00
            # opacity: 0 -> 1 over 180ms
            if elapsed_ms <= 100:
                t = elapsed_ms / 100.0
                ease_t = 1.0 - (1.0 - t) ** 2
                scale = 0.92 + (1.04 - 0.92) * ease_t
            elif elapsed_ms <= 180:
                t = (elapsed_ms - 100.0) / 80.0
                ease_t = t * t
                scale = 1.04 + (1.00 - 1.04) * ease_t
            else:
                scale = 1.00

            alpha = max(0.0, min(1.0, elapsed_ms / 180.0)) if elapsed_ms < 180 else 1.0

            line_h = fm.lineSpacing()
            total_h = line_h * len(wrapped)
            if style.alignment in (2, 3, 1):      # bottom
                start_y = base_y - total_h
            elif style.alignment in (5, 6, 4):    # center
                start_y = base_y - total_h // 2
            else:                                  # top
                start_y = base_y

            cx = (vx + margin_x) + safe_w / 2.0
            cy = start_y + total_h / 2.0

            painter.save()
            painter.setOpacity(alpha)
            painter.translate(cx, cy)
            painter.scale(scale, scale)
            painter.translate(-cx, -cy)

            self._paint_lines(painter, fm, wrapped, vx + margin_x, safe_w, base_y,
                              text_color, stroke_color, stroke_w, shadow_offset,
                              alignment=style.alignment)
            painter.restore()
        else:
            wrapped = self._wrap_text(fm, self._clip.text, safe_w)
            self._paint_lines(painter, fm, wrapped, vx + margin_x, safe_w, base_y,
                              text_color, stroke_color, stroke_w, shadow_offset,
                              alignment=style.alignment)


    def _paint_lines(
        self, painter, fm, lines: list[str],
        area_x: int, area_w: int, base_y: int,
        text_color, stroke_color, stroke_w, shadow_offset,
        *,
        alignment: int = 2,
    ) -> None:
        """
        Vẽ một danh sách dòng text đã word-wrapped.
        base_y là vị trí tham chiếu:
          - bottom alignment (2,1,3): base_y = đáy của block text
          - center (5,4,6): base_y = giữa của block text
          - top (8,7,9): base_y = đỉnh của block text
        """
        line_h = fm.lineSpacing()
        total_h = line_h * len(lines)

        if alignment in (2, 3, 1):      # bottom
            start_y = base_y - total_h
        elif alignment in (5, 6, 4):    # center
            start_y = base_y - total_h // 2
        else:                            # top
            start_y = base_y

        for i, line in enumerate(lines):
            lw = fm.horizontalAdvance(line)
            x = self._line_x(area_x, area_w, lw, alignment)
            y = start_y + i * line_h + fm.ascent()
            _draw_text_with_stroke(
                painter, x, y, line, text_color, stroke_color, stroke_w, shadow_offset,
            )

    def _paint_highlight_segment(
        self,
        painter, fm,
        safe_w: int, margin_x: int,
        vx: int, vy: int, vw: int, vh: int, base_y: int,
        text_color: QColor, hl_color: QColor,
        stroke_color: QColor, stroke_w: float, shadow_offset: float,
        *,
        is_punch: bool = False,
    ) -> None:
        """
        Highlight mode & Punch mode: dùng đúng logic của ass_builder.SubtitleRenderer._segments().

        ass_builder chia SRT event thành các segment 2-5 từ.
        Tại current_ms, chỉ segment đang active được hiển thị, và chỉ từ
        đang active trong segment đó được tô màu highlight (và scale punch nếu ở Punch mode).
        """
        if not self._clip:
            return

        # Dùng cache để không tính lại segments mỗi frame
        if not self._cached_segments:
            settings  = style_to_subtitle_settings(self._style)
            renderer  = SubtitleRenderer(settings, mode="highlight")
            import pysubs2 as _pysubs2
            fake_event = _pysubs2.SSAEvent(
                start=self._clip.start_ms,
                end=self._clip.end_ms,
                text=self._clip.text,
            )
            self._cached_segments = renderer._segments(
                fake_event, self._clip.text, timing=self._word_timing,
            )

        segments = self._cached_segments
        if not segments:
            return

        # Tìm segment active tại current_ms
        active_seg: Optional[SubtitleSegment] = None
        active_word_idx: int = 0
        for seg in segments:
            if seg.start_ms <= self._current_ms < seg.end_ms:
                active_seg      = seg
                # Tìm từ active trong segment
                for wi, word in enumerate(seg.words):
                    if word.start_ms <= self._current_ms:
                        active_word_idx = wi
                break

        if active_seg is None:
            if self._current_ms < segments[0].start_ms:
                active_seg      = segments[0]
                active_word_idx = 0
            else:
                return

        # Word-wrap segment words theo pixel width (giống normal mode)
        words     = list(active_seg.words)
        word_texts = [w.text for w in words]

        lines_words: list[list[str]] = []
        current_line: list[str] = []
        current_w = 0
        space_w   = fm.horizontalAdvance(" ")

        for word_text in word_texts:
            ww = fm.horizontalAdvance(word_text)
            needed = ww if not current_line else current_w + space_w + ww
            if current_line and needed > safe_w:
                lines_words.append(current_line)
                current_line = [word_text]
                current_w    = ww
            else:
                current_line.append(word_text)
                current_w = needed

        if current_line:
            lines_words.append(current_line)

        # Paint
        line_h = fm.lineSpacing()
        total_h = line_h * len(lines_words)

        if self._style.alignment in (2, 3, 1):
            start_y = base_y - total_h
        elif self._style.alignment in (5, 6, 4):
            start_y = base_y - total_h // 2
        else:
            start_y = base_y

        word_offset = 0
        area_x      = vx + margin_x

        for li, line_ws in enumerate(lines_words):
            line_text = " ".join(line_ws)
            lw = fm.horizontalAdvance(line_text)
            cx = self._line_x(area_x, safe_w, lw, self._style.alignment)
            y = start_y + li * line_h + fm.ascent()

            for wi, word in enumerate(line_ws):
                global_wi = word_offset + wi
                color     = hl_color if global_wi == active_word_idx else text_color

                if is_punch and global_wi == active_word_idx:
                    active_word_obj = words[global_wi]
                    word_elapsed = self._current_ms - active_word_obj.start_ms
                    if 0 <= word_elapsed <= 80:
                        t = word_elapsed / 80.0
                        ease_t = 1.0 - (1.0 - t) ** 2
                        word_scale = 1.00 + (1.12 - 1.00) * ease_t
                    elif 80 < word_elapsed <= 160:
                        t = (word_elapsed - 80.0) / 80.0
                        ease_t = t * t
                        word_scale = 1.12 + (1.00 - 1.12) * ease_t
                    else:
                        word_scale = 1.00

                    if word_scale != 1.00:
                        ww = fm.horizontalAdvance(word)
                        wh = fm.height()
                        wcx = cx + ww / 2.0
                        wcy = y - fm.ascent() + wh / 2.0

                        painter.save()
                        painter.translate(wcx, wcy)
                        painter.scale(word_scale, word_scale)
                        painter.translate(-wcx, -wcy)
                        _draw_text_with_stroke(
                            painter, cx, y, word, color, stroke_color, stroke_w, shadow_offset,
                        )
                        painter.restore()
                    else:
                        _draw_text_with_stroke(
                            painter, cx, y, word, color, stroke_color, stroke_w, shadow_offset,
                        )
                else:
                    _draw_text_with_stroke(
                        painter, cx, y, word, color, stroke_color, stroke_w, shadow_offset,
                    )

                # Advance cx at normal scale — layout stays completely fixed!
                advance_str = word + (" " if wi < len(line_ws) - 1 else "")
                cx += fm.horizontalAdvance(advance_str)

            word_offset += len(line_ws)

# ──────────────────────────────────────────────────────────────────────────────
# Shared paint helper
# ──────────────────────────────────────────────────────────────────────────────

def _draw_text_with_stroke(
    painter: QPainter,
    x: int, y: int,
    text: str,
    text_color: QColor,
    stroke_color: QColor,
    stroke_width: float,
    shadow_offset: float,
) -> None:
    """Vẽ text có viền stroke bằng QPainterPath."""
    font = painter.font()
    path = QPainterPath()
    path.addText(x, y, font, text)

    # ASS dùng BackColour (đang là stroke_color) cho shadow, với offset
    # bằng thuộc tính Shadow trong toạ độ PlayRes.
    if shadow_offset > 0:
        painter.save()
        painter.translate(shadow_offset, shadow_offset)
        painter.fillPath(path, stroke_color)
        painter.restore()

    # Stroke
    if stroke_width > 0:
        pen = QPen(stroke_color, stroke_width * 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.strokePath(path, pen)

    # Fill
    painter.fillPath(path, text_color)


# ──────────────────────────────────────────────────────────────────────────────
# _DropZone (State 1)
# ──────────────────────────────────────────────────────────────────────────────

class _DropZone(QWidget):
    """Vùng kéo-thả / click để chọn video."""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DropZone")
        self.setCursor(Qt.PointingHandCursor)

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

    def set_drag_hover(self, active: bool) -> None:
        self.setProperty("dragHover", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()


# ──────────────────────────────────────────────────────────────────────────────
# _MetaBar
# ──────────────────────────────────────────────────────────────────────────────

class _MetaBar(QWidget):
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
