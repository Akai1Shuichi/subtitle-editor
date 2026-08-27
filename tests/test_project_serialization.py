import json
import pytest
from pathlib import Path
from src.models import EditorProject, SubtitleClip, SubtitleStyle, VideoInfo


def test_subtitle_clip_serialization():
    clip = SubtitleClip(id="c100", text="Xin chào bạn", start_ms=1000, end_ms=5000)
    data = clip.to_dict()
    assert data["id"] == "c100"
    assert data["text"] == "Xin chào bạn"
    assert data["start_ms"] == 1000
    assert data["end_ms"] == 5000

    restored = SubtitleClip.from_dict(data)
    assert restored.id == clip.id
    assert restored.text == clip.text
    assert restored.start_ms == clip.start_ms
    assert restored.end_ms == clip.end_ms


def test_subtitle_style_serialization():
    style = SubtitleStyle(
        mode="highlight",
        fontname="Montserrat",
        fontsize=60,
        text_color=(255, 255, 0),
        highlight_color=(255, 0, 0),
        stroke_color=(10, 10, 10),
        stroke_width=2.5,
        shadow=1.5,
        position_y=85,
        alignment=2,
        subtitle_width=90,
    )
    data = style.to_dict()
    assert data["mode"] == "highlight"
    assert data["fontname"] == "Montserrat"
    assert data["fontsize"] == 60
    assert data["text_color"] == [255, 255, 0]
    assert data["highlight_color"] == [255, 0, 0]

    restored = SubtitleStyle.from_dict(data)
    assert restored.mode == style.mode
    assert restored.fontname == style.fontname
    assert restored.fontsize == style.fontsize
    assert restored.text_color == style.text_color
    assert restored.highlight_color == style.highlight_color
    assert restored.stroke_width == style.stroke_width


def test_video_info_serialization():
    vinfo = VideoInfo(
        width=1920,
        height=1080,
        duration=120.5,
        fps=60.0,
        path=Path("C:/media/sample.mp4"),
    )
    data = vinfo.to_dict()
    assert data["width"] == 1920
    assert data["height"] == 1080
    assert data["duration"] == 120.5
    assert data["fps"] == 60.0
    assert data["path"] == "C:\\media\\sample.mp4" or data["path"] == "C:/media/sample.mp4"

    restored = VideoInfo.from_dict(data)
    assert restored.width == vinfo.width
    assert restored.height == vinfo.height
    assert restored.duration == vinfo.duration
    assert restored.fps == vinfo.fps
    assert str(restored.path) == str(vinfo.path)


def test_editor_project_json_file_serialization(tmp_path):
    vinfo = VideoInfo(
        width=1280,
        height=720,
        duration=45.0,
        fps=30.0,
        path=Path("/videos/intro.mp4"),
    )
    clips = [
        SubtitleClip(id="c1", text="First subtitle", start_ms=0, end_ms=2500),
        SubtitleClip(id="c2", text="Second subtitle", start_ms=2500, end_ms=5000),
    ]
    style = SubtitleStyle(fontname="Arial", fontsize=48, mode="normal")

    project = EditorProject(
        name="Intro Project",
        video_info=vinfo,
        clips=clips,
        style=style,
    )

    # Serialize to dict and JSON string
    p_dict = project.to_dict()
    assert p_dict["name"] == "Intro Project"
    assert len(p_dict["clips"]) == 2
    assert p_dict["video_info"]["width"] == 1280

    json_str = project.to_json()
    assert "Intro Project" in json_str

    # Save to file .subproj
    proj_file = tmp_path / "intro_project.subproj"
    project.save_to_file(proj_file)
    assert proj_file.is_file()

    # Load back from file
    loaded_proj = EditorProject.load_from_file(proj_file)
    assert loaded_proj.id == project.id
    assert loaded_proj.name == "Intro Project"
    assert len(loaded_proj.clips) == 2
    assert loaded_proj.clips[0].text == "First subtitle"
    assert loaded_proj.clips[1].text == "Second subtitle"
    assert loaded_proj.video_info is not None
    assert loaded_proj.video_info.duration == 45.0
    assert loaded_proj.style.fontname == "Arial"
