"""
src/ui/preset_selector.py
───────────────────────────
Visual Mode Preview Selector: 2-column card grid.

Fix layout: GIF widget override sizeHint để không dictate card width.
Cards dùng Expanding policy, grid chia đều 2 cột.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import (
    QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QBrush, QMovie,
)
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget,
)

import sys

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    PREVIEW_DIR = Path(sys._MEIPASS) / "data" / "preset_previews"
else:
    PREVIEW_DIR = Path(__file__).parent.parent.parent / "data" / "preset_previews"

PREVIEW_H = 90


# ─────────────────────────────────────────────────────────────────────────────

class _PlaceholderWidget(QWidget):
    """Dark gradient placeholder + accent bar + icon + label."""

    def __init__(self, icon: str, label: str, accent_hex: str, parent=None):
        super().__init__(parent)
        self._icon = icon
        self._label = label.upper()
        self._accent = QColor(accent_hex)
        # Không set fixed width — expand theo column
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(PREVIEW_H)

    def sizeHint(self) -> QSize:
        return QSize(0, PREVIEW_H)  # width=0 cho phép grid tự quyết định

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()

        path = QPainterPath()
        path.addRoundedRect(0, 0, r.width(), r.height(), 7, 7)
        p.setClipPath(path)

        grad = QLinearGradient(0, 0, 0, r.height())
        grad.setColorAt(0.0, QColor(32, 37, 56))
        grad.setColorAt(1.0, QColor(16, 18, 28))
        p.fillPath(path, QBrush(grad))

        # Accent bar top
        bar = QColor(self._accent)
        bar.setAlpha(200)
        p.fillRect(0, 0, r.width(), 3, bar)

        # Icon
        icon_font = QFont()
        icon_font.setPixelSize(28)
        p.setFont(icon_font)
        p.setPen(QPen(QColor(255, 255, 255, 220)))
        p.drawText(r.adjusted(0, 0, 0, -18), Qt.AlignCenter, self._icon)

        # Label
        lbl_font = QFont()
        lbl_font.setPixelSize(9)
        lbl_font.setBold(True)
        lbl_font.setLetterSpacing(QFont.AbsoluteSpacing, 0.8)
        p.setFont(lbl_font)
        accent_text = QColor(self._accent).lighter(140)
        accent_text.setAlpha(210)
        p.setPen(QPen(accent_text))
        p.drawText(r.adjusted(0, r.height() - 20, 0, -4), Qt.AlignCenter, self._label)

        p.end()


# ─────────────────────────────────────────────────────────────────────────────

class _GifWidget(QLabel):
    """
    GIF preview label. Override sizeHint để width=0 (expand theo grid),
    height cố định. Scale movie khi resize.
    """

    def __init__(self, gif_path: Path, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(PREVIEW_H)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("border-radius: 7px; background-color: #0A0B10;")

        self._movie = QMovie(str(gif_path))
        self.setMovie(self._movie)
        self._movie.start()

    def sizeHint(self) -> QSize:
        # Trả về width=0 để không force card width theo GIF size
        return QSize(0, PREVIEW_H)

    def minimumSizeHint(self) -> QSize:
        return QSize(0, PREVIEW_H)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        if w > 0 and self._movie:
            self._movie.setScaledSize(QSize(w, PREVIEW_H))


# ─────────────────────────────────────────────────────────────────────────────

class ModePreviewCard(QFrame):
    """Card preview mode. Expand full width, không fixed width."""

    clicked = Signal(str)

    def __init__(
        self,
        mode_key: str,
        title: str,
        gif_filename: Optional[str] = None,
        icon: str = "✦",
        accent_color: str = "#5B6AFF",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.mode_key = mode_key
        self._is_selected = False
        self._accent = accent_color

        self.setObjectName("ModePreviewCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # KHÔNG setFixedWidth

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 6)
        layout.setSpacing(5)

        # Preview area
        gif_loaded = False
        if gif_filename:
            gif_path = PREVIEW_DIR / gif_filename
            if gif_path.exists():
                self._preview = _GifWidget(gif_path)
                layout.addWidget(self._preview)
                gif_loaded = True

        if not gif_loaded:
            self._preview = _PlaceholderWidget(
                icon=icon, label=title, accent_hex=accent_color,
            )
            layout.addWidget(self._preview)

        # Title
        self.title_lbl = QLabel(title)
        self.title_lbl.setAlignment(Qt.AlignCenter)
        self.title_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.title_lbl)

        self._update_style()

    def set_selected(self, selected: bool) -> None:
        if self._is_selected != selected:
            self._is_selected = selected
            self._update_style()

    def _update_style(self) -> None:
        if self._is_selected:
            bcolor = self._accent
            bw = 2
            bg = "#181C2E"
            tc = "#FFFFFF"
            fw = "700"
        else:
            bcolor = "#1E2238"
            bw = 1
            bg = "#10121E"
            tc = "#6A7090"
            fw = "500"

        self.setStyleSheet(f"""
            QFrame#ModePreviewCard {{
                background-color: {bg};
                border: {bw}px solid {bcolor};
                border-radius: 9px;
            }}
            QFrame#ModePreviewCard:hover {{
                background-color: #181D32;
                border-color: #32406A;
            }}
        """)
        self.title_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: {fw}; color: {tc}; "
            "background: transparent; border: none; padding: 0;"
        )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.mode_key)
        super().mousePressEvent(event)


# ─────────────────────────────────────────────────────────────────────────────

class PresetSelectorWidget(QWidget):
    """Grid 2 cột ModePreviewCard."""

    preset_changed = Signal(str)

    MODES = [
        ("normal",      "Normal",         None,            "T",  "#6C8AFF"),
        ("highlight",   "Word Highlight", "highlight.gif", "✦",  "#FFD900"),
        ("punch",       "Punch",          "punch.gif",     "👊", "#F87171"),
        ("pill",        "Pill",           "pill.gif",      "💊", "#60A5FA"),
        ("rounded_box", "Rounded Box",    "rounded_box.gif", "▣", "#FB923C"),
        ("rise",        "Rise",           "rise.gif",      "⬆", "#34D399"),
        ("soft_pop",    "Soft Pop",       "soft_pop.gif",  "💫", "#A78BFA"),
    ]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._cards: dict[str, ModePreviewCard] = {}
        self._current_mode = "normal"

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(6)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        for idx, (mode_key, title, gif_file, icon, accent) in enumerate(self.MODES):
            card = ModePreviewCard(
                mode_key=mode_key,
                title=title,
                gif_filename=gif_file,
                icon=icon,
                accent_color=accent,
            )
            card.clicked.connect(self._on_card_clicked)
            row, col = divmod(idx, 2)
            grid.addWidget(card, row, col)
            self._cards[mode_key] = card

        self.set_active_preset("normal")

    def set_active_preset(self, mode_key: str) -> None:
        key = mode_key
        if key == "soft-pop":
            key = "soft_pop"
        elif key == "rounded-box":
            key = "rounded_box"
        self._current_mode = key
        for m, card in self._cards.items():
            card.set_selected(m == key)

    def _on_card_clicked(self, mode_key: str) -> None:
        self.set_active_preset(mode_key)
        self.preset_changed.emit(mode_key)
