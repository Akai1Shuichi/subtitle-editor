import pytest
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton
from src.project_manager import ProjectManager
from src.ui.project_list_view import ProjectListView, NewProjectDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def pm(tmp_path):
    return ProjectManager(projects_dir=tmp_path / "projects")


def test_project_list_view_empty_state(qapp, pm):
    view = ProjectListView(project_manager=pm)
    assert view.stack.currentWidget() == view.empty_widget


def test_project_list_view_grid_render_and_search(qapp, pm):
    pm.create_project("Project Alpha")
    pm.create_project("Project Beta")

    view = ProjectListView(project_manager=pm)
    assert view.stack.currentWidget() == view.grid_scroll
    assert view.grid_layout.count() == 2

    # Search filter
    view.search_bar.setText("Alpha")
    assert view.grid_layout.count() == 1

    view.search_bar.setText("NonExistent")
    assert view.stack.currentWidget() == view.empty_widget

    view.search_bar.clear()
    assert view.stack.currentWidget() == view.grid_scroll
    assert view.grid_layout.count() == 2


def test_toggle_view_mode(qapp, pm):
    pm.create_project("Sample Project")
    view = ProjectListView(project_manager=pm)
    assert view.view_mode == "grid"
    assert view.stack.currentWidget() == view.grid_scroll

    view._toggle_view_mode()
    assert view.view_mode == "list"
    assert view.stack.currentWidget() == view.table
    assert view.table.rowCount() == 1


def test_new_project_dialog(qapp):
    dialog = NewProjectDialog()
    dialog.name_input.setText("Custom Project")
    dialog.video_input.setText("/path/video.mp4")
    dialog.srt_input.setText("/path/sub.srt")

    name, v_path, s_path = dialog.get_data()
    assert name == "Custom Project"
    assert v_path == "/path/video.mp4"
    assert s_path == "/path/sub.srt"
