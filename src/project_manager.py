"""
src/project_manager.py
───────────────────────
Quản lý danh sách dự án, lưu trữ và thao tác CRUD trên EditorProject.
"""

from __future__ import annotations

import copy
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from .models import EditorProject, ProjectMetadata, SubtitleClip, clips_from_srt
from .video_info import probe_video, VideoInfo


DEFAULT_EXAMPLE_ID = "5f60564a-01bf-4280-8924-d96817b8541d"
CONFIG_FILE = Path.home() / ".subtitle_editor" / "app_config.json"


def get_default_projects_dir() -> Path:
    """Trả về đường dẫn mặc định lưu project trong thư mục Subtitle_Editor_Projects tại Home của HĐH."""
    return Path.home() / "Subtitle_Editor_Projects"


def get_default_export_dir() -> Path:
    """Trả về đường dẫn mặc định xuất video trong thư mục Subtitle_Editor_Video_Export tại Home của HĐH."""
    return Path.home() / "Subtitle_Editor_Video_Export"


def load_app_config() -> dict:
    """Đọc file cấu hình JSON."""
    if CONFIG_FILE.is_file():
        try:
            import json
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                p = data.get("projects_dir", "")
                e = data.get("export_dir", "")
                res = {}
                if p and not ("tmp" in p.lower() or "temp" in p.lower()):
                    res["projects_dir"] = p
                if e and not ("tmp" in e.lower() or "temp" in e.lower()):
                    res["export_dir"] = e
                return res
        except Exception:
            pass
    return {}


def save_app_config(config: dict) -> None:
    """Lưu file cấu hình JSON."""
    try:
        import json
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Merge with existing config
        current = load_app_config()
        current.update(config)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ProjectManager] Lỗi lưu cấu hình: {e}")


class ProjectManager:
    """
    Service quản lý dự án (Project Manager).

    Chịu trách nhiệm quét, tạo mới, lưu, đọc, đổi tên, xóa và nhân bản các dự án
    trong thư mục lưu trữ (`data/projects/`).
    """

    def __init__(
        self,
        projects_dir: str | Path | None = None,
        export_dir: str | Path | None = None,
    ) -> None:
        cfg = load_app_config()

        if projects_dir is None:
            saved_pdir = cfg.get("projects_dir")
            if saved_pdir:
                self.projects_dir = Path(saved_pdir)
            else:
                self.projects_dir = get_default_projects_dir()
        else:
            self.projects_dir = Path(projects_dir)

        if export_dir is None:
            saved_edir = cfg.get("export_dir")
            if saved_edir:
                self.export_dir = Path(saved_edir)
            else:
                self.export_dir = get_default_export_dir()
        else:
            self.export_dir = Path(export_dir)

        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_default_project()

    def set_projects_dir(self, new_dir: str | Path, save_config: bool = True) -> None:
        """Thay đổi thư mục lưu trữ dự án và lưu cấu hình."""
        self.projects_dir = Path(new_dir)
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        if save_config and "tmp" not in str(self.projects_dir).lower() and "temp" not in str(self.projects_dir).lower():
            save_app_config({"projects_dir": str(self.projects_dir)})
        self._ensure_default_project()

    def set_export_dir(self, new_dir: str | Path, save_config: bool = True) -> None:
        """Thay đổi thư mục xuất video và lưu cấu hình."""
        self.export_dir = Path(new_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        if save_config and "tmp" not in str(self.export_dir).lower() and "temp" not in str(self.export_dir).lower():
            save_app_config({"export_dir": str(self.export_dir)})

    def _get_example_project_path(self) -> Optional[Path]:
        """Tìm file dự án mẫu mặc định trong dữ liệu ứng dụng."""
        default_filename = f"{DEFAULT_EXAMPLE_ID}.subproj"
        candidates = [
            Path(__file__).parent.parent / "data" / "projects" / default_filename,
            Path("data/projects") / default_filename,
            Path.cwd() / "data" / "projects" / default_filename,
            Path.cwd() / "subtitle-editor" / "data" / "projects" / default_filename,
        ]
        for cand in candidates:
            if cand.is_file():
                return cand
        return None

    def _ensure_default_project(self) -> None:
        """Đảm bảo dự án mẫu mặc định tồn tại trong dữ liệu ứng dụng."""
        pass

    def _get_project_path(self, project_id: str) -> Path:
        """Trả về đường dẫn file dự án (.subproj) tương ứng với project_id."""
        return self.projects_dir / f"{project_id}.subproj"

    def list_projects(self) -> list[ProjectMetadata]:
        """
        Quét thư mục lưu trữ và trả về danh sách ProjectMetadata
        của tất cả các dự án, bao gồm cả dự án ví dụ mặc định.
        """
        metadata_list: list[ProjectMetadata] = []
        found_ids = set()

        for item in self.projects_dir.glob("*.subproj"):
            try:
                project = EditorProject.load_from_file(item)
                metadata_list.append(project.to_metadata())
                found_ids.add(project.id)
            except Exception as e:
                print(f"[ProjectManager] Lỗi đọc file dự án {item}: {e}")

        # Nạp dự án ví dụ mặc định nếu không có trong thư mục của người dùng
        if DEFAULT_EXAMPLE_ID not in found_ids:
            ex_path = self._get_example_project_path()
            if ex_path and ex_path.is_file():
                try:
                    ex_proj = EditorProject.load_from_file(ex_path)
                    metadata_list.append(ex_proj.to_metadata())
                except Exception as e:
                    print(f"[ProjectManager] Lỗi đọc dự án mẫu mặc định: {e}")

        # Sắp xếp theo updated_at mới nhất đến cũ nhất
        metadata_list.sort(key=lambda m: m.updated_at, reverse=True)
        return metadata_list

    def create_project(
        self,
        name: str,
        video_path: str | Path = "",
        srt_path: str | Path = "",
    ) -> EditorProject:
        """
        Khởi tạo dự án mới và lưu trữ ban đầu.

        Parameters
        ----------
        name       : Tên dự án
        video_path : Đường dẫn tới file video (nếu có)
        srt_path   : Đường dẫn tới file SRT (nếu có)
        """
        project = EditorProject(
            id=str(uuid.uuid4()),
            name=name.strip() or "Untitled Project",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )

        # 1. Đọc video info nếu có video_path
        if video_path:
            vpath = Path(video_path)
            if vpath.is_file():
                try:
                    project.video_info = probe_video(vpath)
                except Exception as e:
                    # Nếu ffprobe lỗi hoặc file video có vấn đề, lưu thông tin đường dẫn cơ bản
                    project.video_info = VideoInfo(
                        width=0,
                        height=0,
                        duration=0.0,
                        fps=0.0,
                        path=vpath,
                    )
                    print(f"[ProjectManager] Không thể probe video {vpath}: {e}")

        # 2. Đọc clips từ SRT nếu có srt_path
        if srt_path:
            spath = Path(srt_path)
            if spath.is_file():
                try:
                    project.clips = clips_from_srt(spath)
                except Exception as e:
                    print(f"[ProjectManager] Không thể load SRT {spath}: {e}")

        # 3. Lưu dự án vừa tạo
        self.save_project(project)
        return project

    def load_project(self, project_id: str) -> EditorProject:
        """
        Khôi phục đối tượng EditorProject từ file dự án.
        Nạp từ thư mục ứng dụng nếu là dự án ví dụ mặc định.
        """
        path = self._get_project_path(project_id)
        if not path.is_file():
            if project_id == DEFAULT_EXAMPLE_ID:
                ex_path = self._get_example_project_path()
                if ex_path and ex_path.is_file():
                    return EditorProject.load_from_file(ex_path)
            raise FileNotFoundError(f"Không tìm thấy dự án với ID: {project_id}")
        return EditorProject.load_from_file(path)

    def save_project(self, project: EditorProject) -> Path:
        """
        Lưu state hiện tại của EditorProject vào thư mục dự án.
        Cập nhật lại thời gian `updated_at`.
        """
        path = self._get_project_path(project.id)
        project.save_to_file(path)
        return path

    def delete_project(self, project_id: str) -> bool:
        """
        Xóa file dự án và cache dữ liệu liên quan.
        Không cho phép xóa dự án ví dụ mặc định (5f60564a-01bf-4280-8924-d96817b8541d).
        Trả về True nếu xóa thành công, False nếu không xóa được hoặc không tồn tại.
        """
        if project_id == DEFAULT_EXAMPLE_ID:
            print(f"[ProjectManager] Không thể xóa dự án ví dụ mặc định: {project_id}")
            return False

        path = self._get_project_path(project_id)
        if path.is_file():
            try:
                os.remove(path)
                return True
            except OSError as e:
                print(f"[ProjectManager] Không thể xóa dự án {project_id}: {e}")
                return False
        return False

    def duplicate_project(self, project_id: str, new_name: str = "") -> EditorProject:
        """
        Nhân bản một dự án hiện có thành dự án mới với ID mới.
        """
        orig = self.load_project(project_id)
        dup_id = str(uuid.uuid4())
        dup_name = new_name.strip() if new_name.strip() else f"{orig.name} (Copy)"
        now_iso = datetime.now().isoformat()

        # Tạo bản sao mới với ID và timestamp mới
        dup_project = EditorProject(
            id=dup_id,
            name=dup_name,
            created_at=now_iso,
            updated_at=now_iso,
            thumbnail_path=orig.thumbnail_path,
            video_info=copy.deepcopy(orig.video_info),
            clips=copy.deepcopy(orig.clips),
            style=copy.deepcopy(orig.style),
        )

        self.save_project(dup_project)
        return dup_project

    def rename_project(self, project_id: str, new_name: str) -> EditorProject:
        """
        Đổi tên một dự án hiện có.
        Không cho phép đổi tên dự án ví dụ mặc định (5f60564a-01bf-4280-8924-d96817b8541d).
        """
        project = self.load_project(project_id)
        if project_id == DEFAULT_EXAMPLE_ID:
            print(f"[ProjectManager] Không thể đổi tên dự án ví dụ mặc định: {project_id}")
            return project

        project.name = new_name.strip() or "Untitled Project"
        self.save_project(project)
        return project
