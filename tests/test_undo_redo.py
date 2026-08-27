"""
tests/test_undo_redo.py
────────────────────────
Kiểm thử tính năng Undo / Redo (State Snapshot).
"""

import sys
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import EditorProject, SubtitleClip, SubtitleStyle, UndoManager
from src.ui.main_window import MainWindow

app = QApplication.instance() or QApplication(sys.argv)


class TestUndoRedo(unittest.TestCase):
    def test_undo_manager_basic_push_and_undo(self):
        manager = UndoManager(max_depth=50)
        c1 = SubtitleClip(id="c1", text="Sub 1", start_ms=0, end_ms=2000)
        s1 = SubtitleStyle(fontsize=40)

        # Lưu trạng thái ban đầu (clips rỗng, style 40px)
        manager.push_checkpoint([], s1, None)

        # Thêm clip c1
        current_clips = [c1]
        current_style = SubtitleStyle(fontsize=40)

        # Thực hiện Undo -> khôi phục trạng thái ban đầu (clips rỗng)
        restored = manager.undo(current_clips, current_style, "c1")
        self.assertIsNotNone(restored)
        self.assertEqual(len(restored.clips), 0)
        self.assertIsNone(restored.selected_clip_id)

        # Thực hiện Redo -> khôi phục c1
        redo_res = manager.redo([], s1, None)
        self.assertIsNotNone(redo_res)
        self.assertEqual(len(redo_res.clips), 1)
        self.assertEqual(redo_res.clips[0].id, "c1")
        self.assertEqual(redo_res.selected_clip_id, "c1")

    def test_editor_project_undo_redo(self):
        project = EditorProject()
        c1 = SubtitleClip(id="c1", text="First", start_ms=0, end_ms=2000)

        # Trạng thái 0: project rỗng
        project.save_checkpoint(None)

        # Trạng thái 1: thêm c1
        project.clips.append(c1)
        project.save_checkpoint("c1")

        # Trạng thái 2: đổi text
        c1.text = "Second"

        # Undo 1 lần -> c1 text quay lại "First"
        project.undo("c1")
        self.assertEqual(project.clips[0].text, "First")

        # Undo lần nữa -> clips quay lại rỗng
        project.undo("c1")
        self.assertEqual(len(project.clips), 0)

        # Redo 1 lần -> c1 có lại với text "First"
        project.redo(None)
        self.assertEqual(len(project.clips), 1)
        self.assertEqual(project.clips[0].text, "First")

    def test_main_window_undo_redo_shortcuts(self):
        win = MainWindow()
        c1 = SubtitleClip(id="c1", text="Initial Sub", start_ms=1000, end_ms=3000)

        # Import clip c1
        win._save_checkpoint()
        win._project.clips.append(c1)
        win._selected_clip_id = "c1"
        win._update_ui_state()

        self.assertEqual(len(win._project.clips), 1)

        # Xóa clip
        win._on_clip_delete_requested("c1")
        self.assertEqual(len(win._project.clips), 0)

        # Kích hoạt Undo qua shortcut slot
        win._on_undo_triggered()
        self.assertEqual(len(win._project.clips), 1)
        self.assertEqual(win._selected_clip_id, "c1")

        # Kích hoạt Redo qua shortcut slot
        win._on_redo_triggered()
        self.assertEqual(len(win._project.clips), 0)


if __name__ == "__main__":
    unittest.main()
