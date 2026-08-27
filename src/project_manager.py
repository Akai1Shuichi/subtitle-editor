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


class ProjectManager:
    """
    Service quản lý dự án (Project Manager).

    Chịu trách nhiệm quét, tạo mới, lưu, đọc, đổi tên, xóa và nhân bản các dự án
    trong thư mục lưu trữ (`data/projects/`).
    """

    def __init__(self, projects_dir: str | Path = "data/projects") -> None:
        self.projects_dir = Path(projects_dir)
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def _get_project_path(self, project_id: str) -> Path:
        """Trả về đường dẫn file dự án (.subproj) tương ứng với project_id."""
        return self.projects_dir / f"{project_id}.subproj"

    def list_projects(self) -> list[ProjectMetadata]:
        """
        Quét thư mục lưu trữ và trả về danh sách ProjectMetadata
        của tất cả các dự án, sắp xếp theo thời gian cập nhật mới nhất.
        """
        metadata_list: list[ProjectMetadata] = []

        for item in self.projects_dir.glob("*.subproj"):
            try:
                project = EditorProject.load_from_file(item)
                metadata_list.append(project.to_metadata())
            except Exception as e:
                # Bỏ qua file bị hỏng / không đọc được
                print(f"[ProjectManager] Lỗi đọc file dự án {item}: {e}")

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

        Raises
        ------
        FileNotFoundError: Nếu dự án không tồn tại.
        """
        path = self._get_project_path(project_id)
        if not path.is_file():
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
        Trả về True nếu xóa thành công, False nếu dự án không tồn tại.
        """
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
        """
        project = self.load_project(project_id)
        project.name = new_name.strip() or "Untitled Project"
        self.save_project(project)
        return project
