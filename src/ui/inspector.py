"""
src/ui/inspector.py
────────────────────
Panel Inspector bên phải: thích ứng theo 4 trạng thái của editor.

State 1 (no video)         : ẩn hết, chỉ label gợi ý
State 2 (video, no clips)  : nút Add Subtitle + style controls
State 3 (has clips)        : nút Add Subtitle + style controls
State 4 (clip selected)    : text editor + style controls + Delete
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFormLayout,
    QFrame,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .color_button import ColorButton
from ..models import SubtitleClip, SubtitleStyle


# ── Constants ──────────────────────────────────────────────────────────────

FONTS = [
    "Arial Black", "Impact", "Anton", "Montserrat ExtraBold", "Montserrat",
    "Inter", "Roboto", "Open Sans", "Lato",
    "Nunito", "Poppins", "Source Sans Pro", "Ubuntu", "Arial",
    "Helvetica Neue", "Georgia", "Times New Roman",
]

POSITIONS = [
    ("Đáy màn hình", 2),
    ("Giữa màn hình", 5),
    ("Đỉnh màn hình", 8),
]


# ── Inspector widget ───────────────────────────────────────────────────────

class Inspector(QWidget):
    """
    Panel phải của editor. Thích ứng theo clip được chọn.

    Signals
    -------
    style_changed(SubtitleStyle)         – người dùng thay đổi style controls
    clip_text_changed(clip_id, new_text) – người dùng sửa text clip
    clip_delete_requested(clip_id)       – người dùng nhấn Delete
    """

    style_changed          = Signal(object)      # SubtitleStyle
    clip_text_changed      = Signal(str, str)    # (clip_id, new_text)
    clip_delete_requested  = Signal(str)         # clip_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Inspector")
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setFixedWidth(280)

        self._selected_clip_id: str | None = None
        self._block_text_signal: bool = False

        # ── Root layout ────────────────────────────────────────────────
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Scrollable content ─────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        inner = QWidget()
        inner.setObjectName("InspectorInner")
        self._inner_layout = QVBoxLayout(inner)
        self._inner_layout.setContentsMargins(20, 20, 20, 20)
        self._inner_layout.setSpacing(0)

        # Section: SUBTITLE header
        self._inner_layout.addWidget(self._build_subtitle_header())
        self._inner_layout.addSpacing(14)

        # Section: Clip text (shown when clip selected)
        self._clip_section = self._build_clip_section()
        self._clip_section.hide()
        self._inner_layout.addWidget(self._clip_section)

        # Divider
        self._style_divider = self._build_divider()
        self._style_divider.hide()
        self._inner_layout.addWidget(self._style_divider)
        self._inner_layout.addSpacing(14)

        # Section: STYLE controls (shown when has_video)
        self._style_section = self._build_style_section()
        self._style_section.hide()
        self._inner_layout.addWidget(self._style_section)
        self._inner_layout.addSpacing(16)

        # Delete button (shown when clip selected)
        self._delete_btn = QPushButton("🗑  Delete Subtitle")
        self._delete_btn.setObjectName("DeleteBtn")
        self._delete_btn.setCursor(Qt.PointingHandCursor)
        self._delete_btn.clicked.connect(self._on_delete)
        self._delete_btn.hide()
        self._inner_layout.addWidget(self._delete_btn)

        self._inner_layout.addStretch()

        scroll.setWidget(inner)
        root.addWidget(scroll)

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def set_has_video(self, has_video: bool) -> None:
        """Bật/tắt phần style."""
        self._style_section.setVisible(has_video)
        self._style_divider.setVisible(has_video)

    def select_clip(self, clip: SubtitleClip | None) -> None:
        """
        Hiển thị / ẩn phần text editor dựa theo clip đang được chọn.
        Gọi với None để bỏ chọn.
        """
        self._selected_clip_id = clip.id if clip else None
        self._block_text_signal = True
        if clip:
            self._text_edit.setPlainText(clip.text)
            self._clip_section.show()
            self._delete_btn.show()
        else:
            self._text_edit.clear()
            self._clip_section.hide()
            self._delete_btn.hide()
        self._block_text_signal = False

    def get_style(self) -> SubtitleStyle:
        """Trả về SubtitleStyle hiện tại từ các control."""
        if self._radio_pill.isChecked():
            mode = "pill"
        elif self._radio_soft_pop.isChecked():
            mode = "soft_pop"
        elif self._radio_punch.isChecked():
            mode = "punch"
        elif self._radio_rise.isChecked():
            mode = "rise"
        elif self._radio_highlight.isChecked():
            mode = "highlight"
        else:
            mode = "normal"

        return SubtitleStyle(
            mode=mode,
            fontname=self._font_combo.currentText(),
            fontsize=self._size_spin.value(),
            text_color=self._text_color_btn.rgb_tuple(),
            highlight_color=self._hl_color_btn.rgb_tuple(),
            alignment=POSITIONS[self._pos_combo.currentIndex()][1],
            position_y=self._position_y_spin.value(),
            stroke_width=float(self._stroke_spin.value()),
            subtitle_width=self._width_spin.value(),
        )

    def apply_style(self, style: SubtitleStyle) -> None:
        """Áp dụng SubtitleStyle lên các control (dùng khi load project)."""
        self._radio_pill.setChecked(style.mode == "pill")
        self._radio_soft_pop.setChecked(style.mode in ("soft_pop", "soft-pop"))
        self._radio_punch.setChecked(style.mode == "punch")
        self._radio_rise.setChecked(style.mode == "rise")
        self._radio_highlight.setChecked(style.mode == "highlight")
        if style.mode == "normal":
            self._radio_normal.setChecked(True)

        idx = next(
            (i for i, (_, v) in enumerate(POSITIONS) if v == style.alignment), 0
        )
        self._pos_combo.setCurrentIndex(idx)
        fi = self._font_combo.findText(style.fontname)
        if fi >= 0:
            self._font_combo.setCurrentIndex(fi)
        self._size_spin.setValue(style.fontsize)
        self._position_y_spin.setValue(style.position_y)
        self._stroke_spin.setValue(int(style.stroke_width))
        self._text_color_btn.set_color_rgb(style.text_color)
        self._hl_color_btn.set_color_rgb(style.highlight_color)
        self._width_spin.setValue(style.subtitle_width)

    # ──────────────────────────────────────────────────────────────────────
    # Build sections
    # ──────────────────────────────────────────────────────────────────────

    def _build_subtitle_header(self) -> QLabel:
        lbl = QLabel("SUBTITLE")
        lbl.setObjectName("SectionHeader")
        return lbl

    def _build_clip_section(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 14)
        layout.setSpacing(8)

        label = QLabel("Text")
        label.setObjectName("FieldLabel")
        layout.addWidget(label)

        self._text_edit = QPlainTextEdit()
        self._text_edit.setObjectName("SubtitleTextEdit")
        self._text_edit.setPlaceholderText("Nội dung subtitle…")
        self._text_edit.setMinimumHeight(72)
        self._text_edit.setMaximumHeight(120)
        self._text_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._text_edit)

        return w

    def _build_style_section(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # STYLE header
        header = QLabel("STYLE")
        header.setObjectName("SectionHeader")
        layout.addWidget(header)

        # Mode radio
        mode_w = QWidget()
        mode_l = QVBoxLayout(mode_w)
        mode_l.setContentsMargins(0, 0, 0, 0)
        mode_l.setSpacing(6)

        self._radio_normal = QRadioButton("Normal")
        self._radio_normal.setChecked(True)
        self._radio_soft_pop = QRadioButton("Soft Pop")
        self._radio_punch = QRadioButton("Punch")
        self._radio_rise = QRadioButton("Rise")
        self._radio_highlight = QRadioButton("Word Highlight")
        self._radio_pill = QRadioButton("Pill Animation")

        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self._radio_normal)
        self._mode_group.addButton(self._radio_soft_pop)
        self._mode_group.addButton(self._radio_punch)
        self._mode_group.addButton(self._radio_rise)
        self._mode_group.addButton(self._radio_highlight)
        self._mode_group.addButton(self._radio_pill)
        self._mode_group.buttonClicked.connect(self._emit_style)

        mode_l.addWidget(self._radio_normal)
        mode_l.addWidget(self._radio_soft_pop)
        mode_l.addWidget(self._radio_punch)
        mode_l.addWidget(self._radio_rise)
        mode_l.addWidget(self._radio_highlight)
        mode_l.addWidget(self._radio_pill)
        layout.addWidget(mode_w)

        # Small divider
        div = self._build_divider()
        layout.addWidget(div)

        # Form
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignLeft)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self._font_combo = QComboBox()
        self._font_combo.addItems(FONTS)
        self._font_combo.setCursor(Qt.PointingHandCursor)
        self._font_combo.currentTextChanged.connect(self._emit_style)
        form.addRow("Font", self._font_combo)

        self._size_spin = QSpinBox()
        self._size_spin.setRange(10, 120)
        self._size_spin.setValue(54)
        self._size_spin.setSuffix(" px")
        self._size_spin.valueChanged.connect(self._emit_style)
        form.addRow("Cỡ chữ", self._size_spin)

        self._text_color_btn = ColorButton("#ffffff")
        self._text_color_btn.colorChanged.connect(self._emit_style)
        form.addRow("Màu chữ", self._text_color_btn)

        self._hl_color_btn = ColorButton("#ffd900")
        self._hl_color_btn.colorChanged.connect(self._emit_style)
        form.addRow("Highlight", self._hl_color_btn)

        self._position_y_spin = QSpinBox()
        self._position_y_spin.setRange(50, 95)
        self._position_y_spin.setValue(82)
        self._position_y_spin.setSuffix(" %")
        self._position_y_spin.valueChanged.connect(self._emit_style)
        form.addRow("Vị trí dọc", self._position_y_spin)

        self._stroke_spin = QSpinBox()
        self._stroke_spin.setRange(1, 8)
        self._stroke_spin.setValue(4)
        self._stroke_spin.setSuffix(" px")
        self._stroke_spin.valueChanged.connect(self._emit_style)
        form.addRow("Viền chữ", self._stroke_spin)

        self._width_spin = QSpinBox()
        self._width_spin.setRange(30, 100)
        self._width_spin.setValue(80)
        self._width_spin.setSuffix(" %")
        self._width_spin.setToolTip(
            "Chiều rộng vùng subtitle tính theo % chiều rộng video.\n"
            "Hẹp hơn → tự động xuống dòng sớm hơn."
        )
        self._width_spin.valueChanged.connect(self._emit_style)
        form.addRow("Chiều rộng", self._width_spin)

        self._pos_combo = QComboBox()
        for label, _ in POSITIONS:
            self._pos_combo.addItem(label)
        self._pos_combo.setCursor(Qt.PointingHandCursor)
        self._pos_combo.currentIndexChanged.connect(self._emit_style)
        form.addRow("Vị trí", self._pos_combo)

        layout.addLayout(form)
        return w

    def _build_divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setObjectName("Divider")
        return line

    # ──────────────────────────────────────────────────────────────────────
    # Private slots
    # ──────────────────────────────────────────────────────────────────────

    def _on_text_changed(self) -> None:
        if self._block_text_signal or not self._selected_clip_id:
            return
        self.clip_text_changed.emit(
            self._selected_clip_id,
            self._text_edit.toPlainText(),
        )

    def _on_delete(self) -> None:
        if self._selected_clip_id:
            self.clip_delete_requested.emit(self._selected_clip_id)

    def _emit_style(self, *_) -> None:
        self.style_changed.emit(self.get_style())
