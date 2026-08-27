import os
import shutil
import tempfile
from pathlib import Path

import pytest
from src.project_manager import (
    ProjectManager,
    DEFAULT_EXAMPLE_ID,
    get_default_projects_dir,
)
from src.models import ProjectMetadata, EditorProject


def test_default_example_id_constant():
    assert DEFAULT_EXAMPLE_ID == "5f60564a-01bf-4280-8924-d96817b8541d"


def test_is_example_properties():
    meta_example = ProjectMetadata(
        project_id=DEFAULT_EXAMPLE_ID,
        name="Ví dụ",
        created_at="",
        updated_at="",
    )
    meta_normal = ProjectMetadata(
        project_id="other-uuid-123",
        name="Project A",
        created_at="",
        updated_at="",
    )
    assert meta_example.is_example is True
    assert meta_normal.is_example is False

    proj_example = EditorProject(id=DEFAULT_EXAMPLE_ID, name="Ví dụ")
    proj_normal = EditorProject(id="other-uuid-123", name="Project A")
    assert proj_example.is_example is True
    assert proj_normal.is_example is False


def test_ensure_default_project_and_prevent_delete():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        pm = ProjectManager(projects_dir=temp_dir)
        # Example file should NOT be physically copied into user folder (keeps folder clean)
        example_file = temp_dir / f"{DEFAULT_EXAMPLE_ID}.subproj"
        assert not example_file.is_file()

        # Check list_projects still dynamically includes example project
        projects = pm.list_projects()
        ids = [p.project_id for p in projects]
        assert DEFAULT_EXAMPLE_ID in ids

        # Attempt to delete example project should fail
        deleted = pm.delete_project(DEFAULT_EXAMPLE_ID)
        assert deleted is False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_get_default_projects_dir():
    dir_path = get_default_projects_dir()
    assert isinstance(dir_path, Path)
    desktop = Path.home() / "Desktop"
    if desktop.exists():
        assert dir_path.resolve() == (desktop / "Subtitle_Editor_Projects").resolve()
    else:
        assert dir_path.resolve() == (Path.home() / "Subtitle_Editor_Projects").resolve()


def test_set_projects_dir():
    temp_dir1 = Path(tempfile.mkdtemp())
    temp_dir2 = Path(tempfile.mkdtemp())
    try:
        pm = ProjectManager(projects_dir=temp_dir1)
        assert pm.projects_dir.resolve() == temp_dir1.resolve()

        pm.set_projects_dir(temp_dir2, save_config=False)
        assert pm.projects_dir.resolve() == temp_dir2.resolve()

        # Dynamic resolving works in new projects_dir
        ids = [p.project_id for p in pm.list_projects()]
        assert DEFAULT_EXAMPLE_ID in ids
    finally:
        shutil.rmtree(temp_dir1, ignore_errors=True)
        shutil.rmtree(temp_dir2, ignore_errors=True)
