import pytest
from PySide6.QtWidgets import QApplication
from src.models import ProjectMetadata
from src.ui.header_bar import HeaderBar


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_header_bar_projects_and_recent_menu(qapp):
    header = HeaderBar()

    # Test projects_requested signal
    projects_clicked = []
    header.projects_requested.connect(lambda: projects_clicked.append(True))
    header._projects_btn.click()
    assert projects_clicked == [True]

    # Test recent projects dropdown
    recent_selected = []
    header.open_recent_project_requested.connect(lambda pid: recent_selected.append(pid))

    sample_projects = [
        ProjectMetadata(
            project_id="p1",
            name="Recent Alpha",
            created_at="2026-08-27T10:00:00",
            updated_at="2026-08-27T12:00:00",
        ),
        ProjectMetadata(
            project_id="p2",
            name="Recent Beta",
            created_at="2026-08-27T11:00:00",
            updated_at="2026-08-27T13:00:00",
        ),
    ]

    header.update_recent_projects(sample_projects)
    actions = header._recent_menu.actions()
    assert len(actions) == 2
    assert "Recent Alpha" in actions[0].text()

    # Trigger action
    actions[0].trigger()
    assert recent_selected == ["p1"]
