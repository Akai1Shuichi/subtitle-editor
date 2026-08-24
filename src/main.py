"""
src/main.py
──────────────
Entry point của ứng dụng.
Chạy:  python -m src.main   hoặc   python src/main.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from .ui.main_window import MainWindow


def main() -> None:
    # High-DPI support
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    app.setApplicationName("Subtitle Video Editor")
    app.setOrganizationName("LocalTool")

    # Load Inter font từ system nếu có, fallback sang Segoe UI / sans-serif
    _load_fonts(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


def _load_fonts(app: QApplication) -> None:
    """Đặt font mặc định cho toàn app với danh sách ưu tiên tự động fallback."""
    font = QFont()
    font.setFamilies(["Inter", "Segoe UI", "Helvetica Neue", "Arial"])
    font.setPointSize(10)
    app.setFont(font)


if __name__ == "__main__":
    main()
