"""
src/updater.py
──────────────
Module quản lý tự động kiểm tra và tải bản cập nhật từ GitHub Releases API.
"""

from __future__ import annotations

import json
import os
import platform
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import Qt, QThread, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

APP_VERSION = "0.9.0"
DEFAULT_GITHUB_REPO = "Akai1Shuichi/subtitle-editor"


def parse_version(v_str: str) -> tuple[int, ...]:
    """Parse version string like 'v1.2.3' or '1.2.3' into tuple of integers for comparison."""
    clean = v_str.lstrip("vV").strip()
    parts = []
    for p in clean.split("."):
        num = ""
        for char in p:
            if char.isdigit():
                num += char
            else:
                break
        if num:
            parts.append(int(num))
    return tuple(parts) if parts else (0,)


def is_newer_version(latest_tag: str, current_ver: str = APP_VERSION) -> bool:
    """Return True if latest_tag is strictly newer than current_ver."""
    try:
        v_latest = parse_version(latest_tag)
        v_current = parse_version(current_ver)
        return v_latest > v_current
    except Exception:
        return False


def detect_os_asset(assets: list[dict[str, Any]]) -> tuple[Optional[dict[str, Any]], str]:
    """
    Tự động khớp asset tốt nhất tương ứng với Hệ Điều Hành hiện tại.
    Trả về (matched_asset_dict, os_name_display).
    """
    sys_name = platform.system().lower()
    os_display = platform.system()

    if sys_name == "windows":
        os_display = "Windows"
        for ext in [".exe", ".msi"]:
            for asset in assets:
                name = asset.get("name", "").lower()
                if name.endswith(ext):
                    return asset, os_display
        for asset in assets:
            name = asset.get("name", "").lower()
            if ("win" in name or "windows" in name) and name.endswith(".zip"):
                return asset, os_display

    elif sys_name == "darwin":
        os_display = "macOS"
        for ext in [".dmg", ".pkg"]:
            for asset in assets:
                name = asset.get("name", "").lower()
                if name.endswith(ext):
                    return asset, os_display
        for asset in assets:
            name = asset.get("name", "").lower()
            if ("mac" in name or "darwin" in name or "osx" in name) and name.endswith(".zip"):
                return asset, os_display

    elif sys_name == "linux":
        os_display = "Linux"
        for ext in [".appimage", ".deb", ".tar.gz"]:
            for asset in assets:
                name = asset.get("name", "").lower()
                if name.endswith(ext):
                    return asset, os_display
        for asset in assets:
            name = asset.get("name", "").lower()
            if "linux" in name:
                return asset, os_display

    if assets:
        return assets[0], os_display

    return None, os_display


class UpdateCheckerThread(QThread):
    """Thread kiểm tra bản cập nhật từ GitHub API."""
    update_available = Signal(dict)
    no_update = Signal(str)
    check_failed = Signal(str)

    def __init__(
        self,
        parent=None,
        repo: str = DEFAULT_GITHUB_REPO,
        current_version: str = APP_VERSION,
        force: bool = False,
    ):
        # Cho phép linh hoạt nếu tham số thứ 1 truyền vào là repo dạng chuỗi
        if isinstance(parent, str):
            repo = parent
            parent = None

        super().__init__(parent)
        self.repo = repo if isinstance(repo, str) else DEFAULT_GITHUB_REPO
        self.current_version = current_version
        self.force = force

    def run(self):
        print(f"[UpdateCheckerThread] Started run() -> Checking updates for repo '{self.repo}' (v{self.current_version}, force={self.force})...")
        url = f"https://api.github.com/repos/{self.repo}/releases/latest"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "SubtitleEditor-AutoUpdater",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as response:
                print(f"[UpdateCheckerThread] HTTP status: {response.status}")
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    print("data:" , data)
                    latest_tag = data.get("tag_name", "")
                    release_notes = data.get("body", "Không có nhật ký thay đổi.")
                    html_url = data.get("html_url", f"https://github.com/{self.repo}/releases")
                    assets = data.get("assets", [])

                    print(f"[UpdateCheckerThread] Latest tag from GitHub: '{latest_tag}'")
                    if self.force or is_newer_version(latest_tag, self.current_version):
                        matched_asset, os_name = detect_os_asset(assets)
                        download_url = matched_asset.get("browser_download_url", "") if matched_asset else ""
                        file_name = matched_asset.get("name", "") if matched_asset else ""
                        file_size = matched_asset.get("size", 0) if matched_asset else 0

                        print(f"[UpdateCheckerThread] Update available! New version: {latest_tag} (force={self.force})")
                        self.update_available.emit({
                            "version": latest_tag,
                            "current_version": self.current_version,
                            "notes": release_notes,
                            "download_url": download_url,
                            "release_url": html_url,
                            "file_name": file_name,
                            "file_size": file_size,
                            "os_name": os_name,
                        })
                    else:
                        msg = f"Bạn đang sử dụng phiên bản mới nhất ({self.current_version})."
                        print(f"[UpdateCheckerThread] {msg}")
                        self.no_update.emit(msg)
                else:
                    err = f"HTTP Error {response.status}"
                    print(f"[UpdateCheckerThread] {err}")
                    self.check_failed.emit(err)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                err = f"Chưa tìm thấy bản phát hành (Release) nào trên GitHub cho repo '{self.repo}'."
            else:
                err = f"Lỗi kết nối GitHub API: HTTP {e.code}"
            print(f"[UpdateCheckerThread] HTTPError: {err}")
            self.check_failed.emit(err)
        except Exception as e:
            err = f"Không thể kết nối GitHub để kiểm tra bản cập nhật: {e}"
            print(f"[UpdateCheckerThread] Exception: {err}")
            self.check_failed.emit(err)


class UpdateDownloaderThread(QThread):
    """Thread tải file asset cập nhật về máy."""
    progress = Signal(int, int, float)  # bytes_received, total_bytes, percent
    finished = Signal(str)              # save_path
    failed = Signal(str)                # error_msg

    def __init__(self, download_url: str, file_name: str, parent=None):
        super().__init__(parent)
        self.download_url = download_url
        self.file_name = file_name
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            temp_dir = Path(tempfile.gettempdir()) / "SubtitleEditor_Updates"
            temp_dir.mkdir(parents=True, exist_ok=True)
            save_path = temp_dir / self.file_name

            req = urllib.request.Request(
                self.download_url,
                headers={"User-Agent": "SubtitleEditor-AutoUpdater"},
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                total_bytes = int(response.headers.get("Content-Length", 0))
                bytes_received = 0
                block_size = 65536

                with open(save_path, "wb") as f:
                    while True:
                        if self._is_cancelled:
                            self.failed.emit("Đã hủy tải bản cập nhật.")
                            return
                        buffer = response.read(block_size)
                        if not buffer:
                            break
                        f.write(buffer)
                        bytes_received += len(buffer)
                        percent = (bytes_received / total_bytes * 100) if total_bytes > 0 else 0
                        self.progress.emit(bytes_received, total_bytes, percent)

            self.finished.emit(str(save_path))
        except Exception as e:
            self.failed.emit(f"Lỗi khi tải bản cập nhật: {e}")


class UpdateDialog(QDialog):
    """Dialog hiển thị thông tin bản cập nhật mới & giao diện tải về."""

    def __init__(self, update_info: dict, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.downloader_thread: Optional[UpdateDownloaderThread] = None

        self.setWindowTitle("🚀 Bản Cập Nhật Mới - Subtitle Editor")
        self.setFixedSize(520, 420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #cccccc;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #ffffff;
            }
            QTextEdit {
                background-color: #252526;
                color: #dddddd;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
            }
            QPushButton#PrimaryBtn {
                background-color: #007acc;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton#PrimaryBtn:hover {
                background-color: #0098ff;
            }
            QPushButton#PrimaryBtn:disabled {
                background-color: #3a3d41;
                color: #777777;
            }
            QPushButton#SecondaryBtn {
                background-color: #3c3c3c;
                color: #cccccc;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton#SecondaryBtn:hover {
                background-color: #464646;
                color: #ffffff;
            }
            QProgressBar {
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                background-color: #252526;
                text-align: center;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #007acc;
                border-radius: 3px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header Title
        title_lbl = QLabel(f"🎉 Đã có bản cập nhật mới: <b>{update_info['version']}</b>")
        title_lbl.setStyleSheet("font-size: 16px; color: #4ec9b0;")
        layout.addWidget(title_lbl)

        # Sub info
        ver_info = QLabel(
            f"Phiên bản hiện tại: <b>{update_info['current_version']}</b> | Hệ điều hành: <b>{update_info['os_name']}</b>"
        )
        ver_info.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        layout.addWidget(ver_info)

        # Release notes title
        notes_hdr = QLabel("Nội dung thay đổi / Nhật ký phát hành:")
        notes_hdr.setStyleSheet("font-size: 13px; font-weight: bold;")
        layout.addWidget(notes_hdr)

        # Release notes content
        self.notes_edit = QTextEdit()
        self.notes_edit.setReadOnly(True)
        self.notes_edit.setPlainText(update_info.get("notes", "Không có mô tả."))
        layout.addWidget(self.notes_edit)

        # File asset info
        file_name = update_info.get("file_name")
        file_size_mb = update_info.get("file_size", 0) / (1024 * 1024)
        if file_name:
            asset_info = f"File cài đặt tương ứng: <b>{file_name}</b> ({file_size_mb:.1f} MB)"
        else:
            asset_info = "Chưa tìm thấy file cài đặt tự động cho OS này. Bạn có thể xem trên GitHub để tải thủ công."
        self.asset_lbl = QLabel(asset_info)
        self.asset_lbl.setStyleSheet("color: #888888; font-size: 12px;")
        layout.addWidget(self.asset_lbl)

        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Action Buttons Layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_github = QPushButton("🌐 Xem trên GitHub")
        self.btn_github.setObjectName("SecondaryBtn")
        self.btn_github.clicked.connect(self._on_open_github)
        btn_layout.addWidget(self.btn_github)

        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Để sau")
        self.btn_cancel.setObjectName("SecondaryBtn")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_update = QPushButton("⚡ Cập nhật ngay")
        self.btn_update.setObjectName("PrimaryBtn")
        self.btn_update.setEnabled(bool(update_info.get("download_url")))
        self.btn_update.clicked.connect(self._start_download)
        btn_layout.addWidget(self.btn_update)

        layout.addLayout(btn_layout)

    def _on_open_github(self):
        url = self.update_info.get("release_url", f"https://github.com/{DEFAULT_GITHUB_REPO}/releases")
        QDesktopServices.openUrl(QUrl(url))

    def _start_download(self):
        download_url = self.update_info.get("download_url")
        file_name = self.update_info.get("file_name", "update_installer")
        if not download_url:
            self._on_open_github()
            return

        self.btn_update.setEnabled(False)
        self.btn_github.setEnabled(False)
        self.btn_cancel.setText("Hủy tải")
        self.progress_bar.setVisible(True)

        self.downloader_thread = UpdateDownloaderThread(download_url, file_name, self)
        self.downloader_thread.progress.connect(self._on_download_progress)
        self.downloader_thread.finished.connect(self._on_download_finished)
        self.downloader_thread.failed.connect(self._on_download_failed)
        self.downloader_thread.start()

    @Slot(int, int, float)
    def _on_download_progress(self, bytes_rec: int, total_bytes: int, percent: float):
        self.progress_bar.setValue(int(percent))
        mb_rec = bytes_rec / (1024 * 1024)
        mb_total = total_bytes / (1024 * 1024) if total_bytes > 0 else 0
        self.progress_bar.setFormat(f"Đang tải... {percent:.1f}% ({mb_rec:.1f}/{mb_total:.1f} MB)")

    @Slot(str)
    def _on_download_finished(self, file_path: str):
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("Tải hoàn tất!")
        self.btn_cancel.setText("Đóng")

        reply = QMessageBox.question(
            self,
            "Cập Nhật Thành Công",
            f"Đã tải bản cập nhật thành công về:\n{file_path}\n\nBạn có muốn mở / cài đặt file ngay bây giờ không?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            try:
                if sys.platform == "win32":
                    os.startfile(file_path)
                else:
                    QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể mở file cập nhật: {e}")

    @Slot(str)
    def _on_download_failed(self, error_msg: str):
        self.progress_bar.setVisible(False)
        self.btn_update.setEnabled(True)
        self.btn_github.setEnabled(True)
        self.btn_cancel.setText("Để sau")
        QMessageBox.warning(self, "Lỗi Tải Bản Cập Nhật", error_msg)

    def reject(self):
        if self.downloader_thread and self.downloader_thread.isRunning():
            self.downloader_thread.cancel()
            self.downloader_thread.wait()
        super().reject()
