"""
tests/test_updater.py
──────────────────────
Unit tests cho module updater: version parsing, version comparison, asset matching và update checker.
"""

import pytest
from src.updater import (
    parse_version,
    is_newer_version,
    detect_os_asset,
    APP_VERSION,
)


def test_parse_version():
    assert parse_version("1.0.0") == (1, 0, 0)
    assert parse_version("v1.2.3") == (1, 2, 3)
    assert parse_version("v2.1.0-alpha") == (2, 1, 0)
    assert parse_version("3.0") == (3, 0)


def test_is_newer_version():
    assert is_newer_version("v1.1.0", "1.0.0") is True
    assert is_newer_version("v2.0.0", "1.9.9") is True
    assert is_newer_version("v1.0.0", "1.0.0") is False
    assert is_newer_version("v0.9.0", "1.0.0") is False


def test_detect_os_asset():
    assets = [
        {"name": "subtitle-editor-mac.dmg", "browser_download_url": "http://mac.dmg", "size": 100},
        {"name": "subtitle-editor-win-setup.exe", "browser_download_url": "http://win.exe", "size": 200},
        {"name": "subtitle-editor-linux.AppImage", "browser_download_url": "http://linux.appimage", "size": 300},
    ]

    matched, os_name = detect_os_asset(assets)
    assert matched is not None
    assert "browser_download_url" in matched
