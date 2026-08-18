"""
src/ui/sidebar.py
──────────────────
Panel bên phải: Subtitle import, Style controls.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QIntValidator
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .color_button import ColorButton
from ..models import SubtitleStyle



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


class Sidebar(QWidget):
    # ── Signals ──────────────────────────────────────────────────────────
    srt_loaded = Signal(str)              # path tới file .srt
    style_changed = Signal(object)        # SubtitleStyle object

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setFixedWidth(280)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Scroll area để sidebar không bị clip trên màn hình nhỏ
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        inner = QWidget()
        inner.setObjectName("SidebarInner")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        layout.addWidget(self._build_subtitle_section())
        layout.addWidget(self._build_divider())
        layout.addWidget(self._build_style_section())
        layout.addStretch()

        scroll.setWidget(inner)
        root.addWidget(scroll)

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def get_style_settings(self) -> SubtitleStyle:
        """Trả về SubtitleStyle hiện tại từ các control."""
        return SubtitleStyle(
            mode="highlight" if self._radio_highlight.isChecked() else "normal",
            fontname=self._font_combo.currentText(),
            fontsize=self._size_spin.value(),
            text_color=self._text_color_btn.rgb_tuple(),
            highlight_color=self._hl_color_btn.rgb_tuple(),
            alignment=POSITIONS[self._pos_combo.currentIndex()][1],
            position_y=self._position_y_spin.value(),
            stroke_width=float(self._stroke_spin.value()),
        )

    def apply_style(self, style: SubtitleStyle) -> None:
        """Áp dụng SubtitleStyle lên các control (dùng khi load project)."""
        self._radio_highlight.setChecked(style.mode == "highlight")
        self._radio_normal.setChecked(style.mode == "normal")
        idx = next(
            (i for i, (_, v) in enumerate(POSITIONS) if v == style.alignment), 0
        )
        self._pos_combo.setCurrentIndex(idx)
        font_idx = self._font_combo.findText(style.fontname)
        if font_idx >= 0:
            self._font_combo.setCurrentIndex(font_idx)
        self._size_spin.setValue(style.fontsize)
        self._position_y_spin.setValue(style.position_y)
        self._stroke_spin.setValue(int(style.stroke_width))
        self._text_color_btn.set_color_rgb(style.text_color)
        self._hl_color_btn.set_color_rgb(style.highlight_color)

    def set_srt_info(self, path: str, line_count: int) -> None:
        """Cập nhật label sau khi load SRT thành công."""
        name = Path(path).name
        self._srt_label.setText(f"📄 {name}")
        self._srt_meta.setText(f"{line_count} dòng subtitle")
        self._srt_meta.show()

    def clear_srt(self) -> None:
        self._srt_label.setText("Chưa chọn file")
        self._srt_meta.hide()

    # ──────────────────────────────────────────────────────────────────────
    # Build sections
    # ──────────────────────────────────────────────────────────────────────

    def _build_subtitle_section(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Header
        header = QLabel("SUBTITLE")
        header.setObjectName("SectionHeader")
        layout.addWidget(header)

        # Import SRT button
        import_btn = QPushButton("Import SRT")
        import_btn.setObjectName("ImportBtn")
        import_btn.setCursor(Qt.PointingHandCursor)
        import_btn.clicked.connect(self._on_import_srt)
        layout.addWidget(import_btn)

        # SRT info labels
        self._srt_label = QLabel("Chưa chọn file")
        self._srt_label.setObjectName("SrtLabel")
        self._srt_label.setWordWrap(True)
        layout.addWidget(self._srt_label)

        self._srt_meta = QLabel("")
        self._srt_meta.setObjectName("SrtMeta")
        self._srt_meta.hide()
        layout.addWidget(self._srt_meta)

        return w

    def _build_style_section(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # Header
        header = QLabel("STYLE")
        header.setObjectName("SectionHeader")
        layout.addWidget(header)

        # Mode radio
        mode_widget = QWidget()
        mode_layout = QVBoxLayout(mode_widget)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(6)

        self._radio_normal = QRadioButton("Normal")
        self._radio_normal.setChecked(True)
        self._radio_highlight = QRadioButton("Word Highlight")

        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self._radio_normal)
        self._mode_group.addButton(self._radio_highlight)
        self._mode_group.buttonClicked.connect(self._emit_style)

        mode_layout.addWidget(self._radio_normal)
        mode_layout.addWidget(self._radio_highlight)
        layout.addWidget(mode_widget)

        # Divider nhỏ
        layout.addWidget(self._build_divider())

        # Form layout cho font, size, color, position
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignLeft)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        # Font
        self._font_combo = QComboBox()
        self._font_combo.addItems(FONTS)
        self._font_combo.setCursor(Qt.PointingHandCursor)
        self._font_combo.currentTextChanged.connect(self._emit_style)
        form.addRow("Font", self._font_combo)

        # Size
        self._size_spin = QSpinBox()
        self._size_spin.setRange(10, 120)
        self._size_spin.setValue(54)
        self._size_spin.setSuffix(" px")
        self._size_spin.valueChanged.connect(self._emit_style)
        form.addRow("Cỡ chữ", self._size_spin)

        # Text color
        self._text_color_btn = ColorButton("#ffffff")
        self._text_color_btn.colorChanged.connect(self._emit_style)
        form.addRow("Màu chữ", self._text_color_btn)

        # Highlight color
        self._hl_color_btn = ColorButton("#ffd900")
        self._hl_color_btn.colorChanged.connect(self._emit_style)
        form.addRow("Highlight", self._hl_color_btn)

        # 82 means subtitle's baseline is at 82% of the video height — the
        # requested lower-middle position (bottom: 18%).
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

        # Position
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
    # Slots
    # ──────────────────────────────────────────────────────────────────────

    def _on_import_srt(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file SRT", "",
            "Subtitle Files (*.srt);;All Files (*)"
        )
        if path:
            self.srt_loaded.emit(path)

    def _emit_style(self, *_) -> None:
        self.style_changed.emit(self.get_style_settings())

