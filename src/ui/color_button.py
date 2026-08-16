"""
src/ui/color_button.py
──────────────────────
Nút bấm hiển thị màu, click mở QColorDialog.
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QColorDialog, QPushButton


class ColorButton(QPushButton):
    """Nút nhỏ hiển thị màu đã chọn; emit colorChanged(QColor) khi thay đổi."""

    colorChanged = Signal(QColor)

    def __init__(self, color: QColor | str = "#ffffff", parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self.setFixedSize(36, 28)
        self.setCursor(Qt_cursor())
        self._update_style()
        self.clicked.connect(self._pick_color)

    # ------------------------------------------------------------------
    def color(self) -> QColor:
        return self._color

    def set_color(self, color: QColor | str) -> None:
        self._color = QColor(color)
        self._update_style()

    def rgb_tuple(self) -> tuple[int, int, int]:
        c = self._color
        return (c.red(), c.green(), c.blue())

    # ------------------------------------------------------------------
    def _pick_color(self) -> None:
        chosen = QColorDialog.getColor(self._color, self, "Chọn màu")
        if chosen.isValid():
            self._color = chosen
            self._update_style()
            self.colorChanged.emit(self._color)

    def _update_style(self) -> None:
        hex_color = self._color.name()
        # Chọn màu chữ tương phản
        luminance = (
            0.299 * self._color.red()
            + 0.587 * self._color.green()
            + 0.114 * self._color.blue()
        ) / 255
        text_color = "#000" if luminance > 0.5 else "#fff"
        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {hex_color};
                color: {text_color};
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 5px;
                font-size: 9px;
            }}
            QPushButton:hover {{
                border: 1.5px solid rgba(255,255,255,0.4);
            }}
            """
        )
        self.setText(hex_color.upper())


def Qt_cursor():
    from PySide6.QtCore import Qt
    return Qt.PointingHandCursor
