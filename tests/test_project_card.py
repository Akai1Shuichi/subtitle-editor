import pytest
from PySide6.QtWidgets import QApplication, QPushButton
from src.models import ProjectMetadata
from src.ui.project_card import ProjectCardWidget, _format_duration, _format_timestamp


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_format_helpers():
    assert _format_duration(65000) == "01:05"
    assert _format_duration(3665000) == "01:01:05"
    assert _format_timestamp("2026-08-27T15:30:00") == "2026-08-27 15:30"


def test_project_card_widget_init_and_signals(qapp):
    meta = ProjectMetadata(
        project_id="test-card-1",
        name="Demo Subtitle Project",
        created_at="2026-08-27T10:00:00",
        updated_at="2026-08-27T12:00:00",
        video_path="",
        thumbnail_path="",
        duration_ms=45000,
        clip_count=10,
    )

    card = ProjectCardWidget(meta)

    assert card.name_label.text() == "Demo Subtitle Project"
    assert "00:45" in card.info_label.text()
    assert "10 clips" in card.info_label.text()

    # Test signals
    open_received = []
    rename_received = []
    dup_received = []
    del_received = []

    card.open_requested.connect(lambda pid: open_received.append(pid))
    card.rename_requested.connect(lambda pid: rename_received.append(pid))
    card.duplicate_requested.connect(lambda pid: dup_received.append(pid))
    card.delete_requested.connect(lambda pid: del_received.append(pid))

    # Find buttons
    buttons = card.findChildren(QPushButton)
    btn_map = {btn.text(): btn for btn in buttons}

    assert "Mở" in btn_map
    assert "Sửa tên" in btn_map
    assert "Nhân bản" in btn_map
    assert "Xóa" in btn_map

    btn_map["Mở"].click()
    assert open_received == ["test-card-1"]

    btn_map["Sửa tên"].click()
    assert rename_received == ["test-card-1"]

    btn_map["Nhân bản"].click()
    assert dup_received == ["test-card-1"]

    btn_map["Xóa"].click()
    assert del_received == ["test-card-1"]
