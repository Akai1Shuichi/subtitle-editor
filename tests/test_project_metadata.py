import pytest
from src.models import ProjectMetadata, EditorProject, SubtitleClip, VideoInfo
from pathlib import Path


def test_project_metadata_fields_and_dict_conversion():
    meta = ProjectMetadata(
        project_id="proj-123",
        name="Test Project",
        created_at="2026-08-27T15:00:00",
        updated_at="2026-08-27T15:30:00",
        video_path="/path/to/video.mp4",
        thumbnail_path="/path/to/thumb.jpg",
        duration_ms=40000,
        clip_count=12,
    )

    data = meta.to_dict()
    assert data["project_id"] == "proj-123"
    assert data["name"] == "Test Project"
    assert data["created_at"] == "2026-08-27T15:00:00"
    assert data["updated_at"] == "2026-08-27T15:30:00"
    assert data["video_path"] == "/path/to/video.mp4"
    assert data["thumbnail_path"] == "/path/to/thumb.jpg"
    assert data["duration_ms"] == 40000
    assert data["clip_count"] == 12

    restored = ProjectMetadata.from_dict(data)
    assert restored.project_id == meta.project_id
    assert restored.name == meta.name
    assert restored.created_at == meta.created_at
    assert restored.updated_at == meta.updated_at
    assert restored.video_path == meta.video_path
    assert restored.thumbnail_path == meta.thumbnail_path
    assert restored.duration_ms == meta.duration_ms
    assert restored.clip_count == meta.clip_count


def test_editor_project_to_metadata():
    project = EditorProject(
        name="My Demo Project",
        clips=[
            SubtitleClip(id="c1", text="Hello", start_ms=0, end_ms=1000),
            SubtitleClip(id="c2", text="World", start_ms=1000, end_ms=2000),
        ],
        video_info=VideoInfo(
            path=Path("/videos/demo.mp4"),
            duration=60.0,
            width=1920,
            height=1080,
            fps=30.0,
        ),
    )

    meta = project.to_metadata()
    assert meta.project_id == project.id
    assert meta.name == "My Demo Project"
    assert meta.clip_count == 2
    assert meta.duration_ms == 60000
    assert meta.video_path == str(Path("/videos/demo.mp4"))
    assert meta.created_at == project.created_at
    assert meta.updated_at == project.updated_at
