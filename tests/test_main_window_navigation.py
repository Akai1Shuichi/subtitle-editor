import pytest
from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.models import SubtitleClip


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_main_window_view_switching_and_autosave(qapp, tmp_path):
    projects_dir = tmp_path / "nav_projects"
    win = MainWindow(projects_dir=projects_dir)

    # Initially in Dashboard view
    assert win._view_stack.currentWidget() == win._project_list_view

    # Create a project via project manager
    project = win._project_manager.create_project("Navigation Test Project")

    # Open project
    win.open_project(project.id)
    assert win._view_stack.currentWidget() == win._editor_container
    assert win._project.id == project.id

    # Modify clips and save checkpoint
    clip = SubtitleClip(id="nav1", text="Auto Save Test", start_ms=0, end_ms=1500)
    win._project.clips.append(clip)
    win._save_checkpoint()

    # Switch back to Dashboard view
    win._show_project_list_view()
    assert win._view_stack.currentWidget() == win._project_list_view

    # Verify project was auto-saved to disk
    reloaded = win._project_manager.load_project(project.id)
    assert len(reloaded.clips) == 1
    assert reloaded.clips[0].text == "Auto Save Test"
