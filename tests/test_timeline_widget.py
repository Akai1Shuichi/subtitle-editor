"""
tests/test_timeline_widget.py
───────────────────────────────
Unit tests cho src/ui/timeline_widget.py (TimelineWidget).
"""

import sys
import unittest
from PySide6.QtWidgets import QApplication

from src.models import SubtitleClip
from src.ui.timeline_widget import TimelineWidget, _TimelineCanvas

app = QApplication.instance() or QApplication(sys.argv)


class TestTimelineWidget(unittest.TestCase):
    def setUp(self):
        self.widget = TimelineWidget()

    def test_set_clips_and_selection(self):
        c1 = SubtitleClip(id="c1", text="Sub 1", start_ms=1000, end_ms=3000)
        c2 = SubtitleClip(id="c2", text="Sub 2", start_ms=4000, end_ms=6000)

        self.widget.set_has_video(True)
        self.widget.set_clips([c1, c2], selected_clip_id="c1")
        self.widget.set_current_time(2000, 10000)

        self.assertEqual(len(self.widget._clips), 2)
        self.assertEqual(self.widget._selected_clip_id, "c1")

    def test_zoom(self):
        initial_px = self.widget._px_per_sec
        self.widget._zoom_in()
        self.assertGreater(self.widget._px_per_sec, initial_px)

        self.widget._zoom_out()
        self.assertEqual(self.widget._px_per_sec, initial_px)

    def test_canvas_conversions(self):
        canvas = _TimelineCanvas()
        canvas.set_data([], None, 0, 10000, 50.0)

        # 1 sec (1000ms) = 50px
        self.assertEqual(canvas.ms_to_px(1000), 50.0)
        self.assertEqual(canvas.px_to_ms(50.0), 1000)

    def test_adjacent_clip_boundary_constraint(self):
        c1 = SubtitleClip(id="c1", text="Sub 1", start_ms=1000, end_ms=2000)
        c2 = SubtitleClip(id="c2", text="Sub 2", start_ms=3000, end_ms=4000)
        c3 = SubtitleClip(id="c3", text="Sub 3", start_ms=5000, end_ms=6000)

        canvas = _TimelineCanvas()
        canvas.set_data([c1, c2, c3], "c2", 0, 10000, 50.0)

        # Giả lập drag mode RESIZE_LEFT cho c2 kéo về phía trước (âm 2000ms -> muốn về 1000ms)
        canvas._drag_mode = canvas.MODE_RESIZE_LEFT
        canvas._drag_clip_id = "c2"
        canvas._drag_start_x = 150  # 3000ms = 150px
        canvas._drag_orig_start_ms = 3000
        canvas._drag_orig_end_ms = 4000

        received_timings = []
        canvas.clip_timing_changed.connect(lambda cid, s, e: received_timings.append((cid, s, e)))

        # Kéo chuột sang trái 100px (-2000ms, thử kéo tới 1000ms - thời điểm c1 đang ở [1000-2000ms])
        from PySide6.QtCore import Qt, QPoint
        from PySide6.QtGui import QMouseEvent
        event = QMouseEvent(QMouseEvent.MouseMove, QPoint(50, 50), Qt.NoButton, Qt.NoButton, Qt.NoModifier)
        canvas.mouseMoveEvent(event)

        self.assertTrue(len(received_timings) > 0)
        cid, new_start, new_end = received_timings[-1]
        self.assertEqual(cid, "c2")
        # c2 không được lấn sang clip c1 (c1.end_ms = 2000ms)
        self.assertGreaterEqual(new_start, 2000)

    def test_find_available_clip_range_empty(self):
        from src.models import EditorProject
        project = EditorProject()
        res = project.find_available_clip_range(current_time_ms=1000, video_duration_ms=10000)
        self.assertEqual(res, (1000, 3000))

    def test_find_available_clip_range_inside_clip(self):
        from src.models import EditorProject, SubtitleClip
        project = EditorProject()
        c1 = SubtitleClip(id="c1", text="Sub 1", start_ms=1000, end_ms=3000)
        c2 = SubtitleClip(id="c2", text="Sub 2", start_ms=4000, end_ms=6000)
        project.clips = [c1, c2]

        # Playhead ở 2000ms (nằm trong c1 [1000-3000ms]) -> phải tìm gap gần nhất sau đó là [3000, 4000]
        res = project.find_available_clip_range(current_time_ms=2000, video_duration_ms=10000)
        self.assertEqual(res, (3000, 4000))

    def test_find_available_clip_range_small_gap(self):
        from src.models import EditorProject, SubtitleClip
        project = EditorProject()
        c1 = SubtitleClip(id="c1", text="Sub 1", start_ms=0, end_ms=2000)
        c2 = SubtitleClip(id="c2", text="Sub 2", start_ms=2500, end_ms=5000)
        project.clips = [c1, c2]

        # Playhead ở 2100ms (nằm trong gap 2000ms-2500ms, độ dài 500ms < desired 2000ms)
        # Clip mới phải tự động thu gọn vừa với khoảng trống (2100ms-2500ms)
        res = project.find_available_clip_range(current_time_ms=2100, video_duration_ms=10000)
        self.assertEqual(res, (2100, 2500))

    def test_find_available_clip_range_full_timeline(self):
        from src.models import EditorProject, SubtitleClip
        project = EditorProject()
        c1 = SubtitleClip(id="c1", text="Sub 1", start_ms=0, end_ms=10000)
        project.clips = [c1]

        # Timeline đầy -> trả về None
    def test_delete_key_shortcut(self):
        from src.ui.main_window import MainWindow
        from PySide6.QtGui import QKeyEvent
        from PySide6.QtCore import Qt

        win = MainWindow()
        c1 = SubtitleClip(id="c1", text="Sub 1", start_ms=1000, end_ms=3000)
        win._project.clips = [c1]
        win._selected_clip_id = "c1"

        # Giả lập nhấn phím Delete khi không gõ text
        event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Delete, Qt.NoModifier)
        win.keyPressEvent(event)

        # Clip c1 phải được xóa thành công khỏi project
        self.assertEqual(len(win._project.clips), 0)
        self.assertIsNone(win._selected_clip_id)


if __name__ == "__main__":
    unittest.main()

