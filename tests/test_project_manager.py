import pytest
from pathlib import Path
from src.project_manager import ProjectManager
from src.models import EditorProject, SubtitleClip, SubtitleStyle, VideoInfo


@pytest.fixture
def pm(tmp_path):
    projects_dir = tmp_path / "projects"
    return ProjectManager(projects_dir=projects_dir)


def test_create_and_list_projects(pm):
    initial_count = len(pm.list_projects())
    assert initial_count >= 1  # Includes default example project

    p1 = pm.create_project("Project Alpha")
    p2 = pm.create_project("Project Beta")

    projects = pm.list_projects()
    assert len(projects) == initial_count + 2
    names = [p.name for p in projects]
    assert "Project Alpha" in names
    assert "Project Beta" in names


def test_load_project(pm):
    created = pm.create_project("Project Gamma")
    loaded = pm.load_project(created.id)
    assert loaded.id == created.id
    assert loaded.name == "Project Gamma"


def test_load_non_existent_project(pm):
    with pytest.raises(FileNotFoundError):
        pm.load_project("non-existent-id")


def test_save_and_update_project(pm):
    project = pm.create_project("Editable Project")
    project.clips.append(SubtitleClip(id="c1", text="Sample clip", start_ms=0, end_ms=2000))
    pm.save_project(project)

    reloaded = pm.load_project(project.id)
    assert len(reloaded.clips) == 1
    assert reloaded.clips[0].text == "Sample clip"


def test_rename_project(pm):
    project = pm.create_project("Old Name")
    renamed = pm.rename_project(project.id, "New Awesome Name")
    assert renamed.name == "New Awesome Name"

    reloaded = pm.load_project(project.id)
    assert reloaded.name == "New Awesome Name"


def test_duplicate_project(pm):
    initial_count = len(pm.list_projects())
    orig = pm.create_project("Original Project")
    orig.clips.append(SubtitleClip(id="c1", text="Clip 1", start_ms=100, end_ms=500))
    pm.save_project(orig)

    dup = pm.duplicate_project(orig.id, "Copied Project")
    assert dup.id != orig.id
    assert dup.name == "Copied Project"
    assert len(dup.clips) == 1
    assert dup.clips[0].text == "Clip 1"

    projects = pm.list_projects()
    assert len(projects) == initial_count + 2


def test_delete_project(pm):
    initial_count = len(pm.list_projects())
    p = pm.create_project("To Be Deleted")
    p_id = p.id
    assert pm._get_project_path(p_id).is_file()

    result = pm.delete_project(p_id)
    assert result is True
    assert not pm._get_project_path(p_id).is_file()
    assert len(pm.list_projects()) == initial_count

    # Delete non-existent project returns False
    assert pm.delete_project(p_id) is False
