"""
src/ui/footer_bar.py
────────────────────
Thanh Footer dùng chung cho Dashboard và Project Editor.
"""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


def _get_asset_path(filename: str) -> Path:
    candidates = [
        Path(__file__).parent.parent.parent / "data" / "assets" / filename,
        Path("data/assets") / filename,
        Path.cwd() / "data" / "assets" / filename,
        Path.cwd() / "subtitle-editor" / "data" / "assets" / filename,
    ]
    for c in candidates:
        if c.is_file():
            return c
    return Path("data/assets") / filename


class AppFooter(QWidget):
    """Footer bar hiển thị thông tin giới thiệu, liên hệ và donate."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DashboardFooter")
        self.setStyleSheet("""
            QWidget#DashboardFooter {
                background-color: #252526;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignCenter)

        def _make_icon_label(icon_filename: str) -> QLabel:
            lbl = QLabel()
            icon_path = _get_asset_path(icon_filename)
            if icon_path.is_file():
                pixmap = QPixmap(str(icon_path))
                if not pixmap.isNull():
                    lbl.setPixmap(pixmap.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            return lbl

        # AI Item
        layout.addWidget(_make_icon_label("telegram.png"))
        ai_label = QLabel('AI mình dùng để vibe code <a href="https://t.me/DichVuIT_bot" style="color: #0098ff; text-decoration: none; font-weight: bold;">tại đây : @DichVuIT_bot</a>')
        ai_label.setStyleSheet("color: #cccccc; font-size: 12px;")
        ai_label.setOpenExternalLinks(True)
        layout.addWidget(ai_label)

        # Separator 1
        sep1 = QLabel("•")
        sep1.setStyleSheet("color: #555555; font-size: 12px; margin: 0 4px;")
        layout.addWidget(sep1)

        # Fanpage Item
        layout.addWidget(_make_icon_label("fanpage.png"))
        fp_label = QLabel('<a href="https://web.facebook.com/profile.php?id=61567027726244" style="color: #0098ff; text-decoration: none; font-weight: bold;">Fanpage</a>')
        fp_label.setStyleSheet("color: #cccccc; font-size: 12px;")
        fp_label.setOpenExternalLinks(True)
        layout.addWidget(fp_label)

        # Separator 2
        sep2 = QLabel("•")
        sep2.setStyleSheet("color: #555555; font-size: 12px; margin: 0 4px;")
        layout.addWidget(sep2)

        # Zalo Item
        layout.addWidget(_make_icon_label("zalo.png"))
        zalo_label = QLabel('<a href="https://zalo.me/g/b98og9ldg1rjg7uxg8pt" style="color: #0098ff; text-decoration: none; font-weight: bold;">Zalo</a>')
        zalo_label.setStyleSheet("color: #cccccc; font-size: 12px;")
        zalo_label.setOpenExternalLinks(True)
        layout.addWidget(zalo_label)

        # Separator 3
        sep3 = QLabel("•")
        sep3.setStyleSheet("color: #555555; font-size: 12px; margin: 0 4px;")
        layout.addWidget(sep3)

        # Donate Item
        donate_icon = QLabel("💖")
        donate_icon.setStyleSheet("font-size: 14px;")
        layout.addWidget(donate_icon)

        donate_label = QLabel('Ủng hộ mình tại <a href="https://qr-donate.vercel.app/" style="color: #0098ff; text-decoration: none; font-weight: bold;">Donate</a>')
        donate_label.setStyleSheet("color: #cccccc; font-size: 12px;")
        donate_label.setOpenExternalLinks(True)
        layout.addWidget(donate_label)
