# Giải Thích Chi Tiết Các Bước Đã Thực Hiện

Tài liệu này giải thích chi tiết cơ chế hoạt động và cách triển khai các tính năng đã thực hiện trong **Subtitle Video Editor** dựa theo kế hoạch trong [todo.md](file:///c:/Users/User/Documents/Tool/subtitle-editor/todo.md).

---

## 🚀 Tổng Quan Các Tính Năng Đã Thực Hiện

1. **Kiểm Tra Biên Khi Thêm Phụ Đề Mới (`+ Add Subtitle`)**: Đảm bảo không bao giờ đè lên các khối phụ đề cũ.
2. **Xóa Phụ Đề Bằng Phím `Delete` / `Backspace`**: Cho phép xóa nhanh khối phụ đề đang chọn khi bấm phím tắt.
3. **Hệ Thống Undo / Redo (`Ctrl + Z` / `Ctrl + Y` / `Ctrl + Shift + Z`)**: Cho phép khôi phục hoặc làm lại các thao tác chỉnh sửa phụ đề theo cơ chế **State Snapshot siêu nhẹ**.

---

## 📄 Giải Thích Chi Tiết Theo Các Bước Trong `todo.md`

### 1. Thêm `UndoManager` Quản Lý Snapshot Dữ Liệu (`src/models.py`)
- **Khái niệm**: Thay vì dùng Command Pattern phức tạp, ta dùng **State Snapshot**. Trạng thái của một project về cơ bản gồm 3 thông tin chính:
  - `clips`: Danh sách phụ đề `list[SubtitleClip]`.
  - `style`: Cấu hình kiểu dáng `SubtitleStyle`.
  - `selected_clip_id`: ID của clip đang được chọn.
- **Cấu trúc `ProjectSnapshot`**:
  ```python
  @dataclass
  class ProjectSnapshot:
      clips: list[SubtitleClip]
      style: SubtitleStyle
      selected_clip_id: Optional[str] = None
  ```
- **Cơ chế hoạt động của `UndoManager`**:
  - Quản lý 2 ngăn xếp `_undo_stack` và `_redo_stack`.
  - Khi thực hiện một thao tác chỉnh sửa, gọi `push_checkpoint()`. Trạng thái hiện tại được nhân bản bằng `copy.deepcopy()` và đẩy vào `_undo_stack` (tối đa 50 bước). Đồng thời xóa sạch `_redo_stack`.
  - Khi gọi `undo()`: Đẩy trạng thái hiện tại vào `_redo_stack`, sau đó lấy trạng thái cuối từ `_undo_stack` ra khôi phục.
  - Khi gọi `redo()`: Đẩy trạng thái hiện tại vào `_undo_stack`, sau đó lấy trạng thái cuối từ `_redo_stack` ra khôi phục.

---

### 2. Kiểm Tra Ranh Giới & Thêm Phụ Đề Mới (`find_available_clip_range`)
- **Vấn đề cũ**: Trước đây khi bấm `+ Add Subtitle`, phụ đề mới được chèn cố định 2 giây bắt đầu từ vị trí con trỏ playhead `current_time_ms`, dẫn đến việc bị đè chèn lên các clip phụ đề đã có bên cạnh.
- **Giải pháp (`EditorProject.find_available_clip_range`)**:
  - Quét toàn bộ timeline để tìm các khoảng trống khả dụng (Gaps) giữa các clip hoặc ở đầu/cuối video.
  - Nếu playhead đang nằm trong khoảng trống, phụ đề mới bắt đầu ngay tại playhead và tự động **cắt gọn độ dài** vừa khít với khoảng trống (nếu khoảng trống nhỏ hơn 2 giây, tối thiểu 200ms).
  - Nếu playhead đang đè trên một clip cũ, hệ thống tự động tìm khoảng trống khả dụng **ngay sau** clip đó để chèn.
  - Tự động di chuyển playhead tới vị trí clip mới để xem trước.

---

### 3. Tích Hợp `save_checkpoint` Vào Các Thao Tác Trong `MainWindow` (`src/ui/main_window.py`)
Mọi thao tác làm thay đổi dữ liệu đều tự động gọi `_save_checkpoint()` trước khi cập nhật dữ liệu:

1. **Thêm phụ đề (`_on_add_subtitle_requested`)**: Lưu checkpoint trước khi append clip mới.
2. **Xóa phụ đề (`_on_clip_delete_requested`)**: Lưu checkpoint trước khi xóa clip khỏi danh sách.
3. **Kéo thả / Resize clip trên Timeline (`drag_started`)**:
   - Khi người dùng bấm chuột bắt đầu kéo clip trên canvas, `_TimelineCanvas` phát ra tín hiệu `drag_started`.
   - `MainWindow` nhận tín hiệu và lưu checkpoint ngay lúc bắt đầu kéo, giúp việc Undo khôi phục chính xác vị trí clip trước khi kéo.
4. **Sửa chữ trong Inspector (`_on_clip_text_changed`)**:
   - Sử dụng `QTimer` loại **Debounce 500ms**.
   - Khi người dùng bắt đầu gõ ký tự đầu tiên, checkpoint được lưu lại. Trong lúc gõ liên tục, timer được đếm lại để không lưu từng phím gõ đơn lẻ. Sau 500ms dừng gõ, đợt chỉnh sửa hoàn tất.
5. **Đổi Style / Preset (`_on_style_changed`)**: Lưu checkpoint trước khi áp dụng style mới.
6. **Import file phụ đề mới (`_on_srt_loaded`, `_on_json_loaded`, `_on_capcut_json_loaded`)**: Lưu checkpoint trước khi nạp dữ liệu từ file mới.

---

### 4. Xử Lý Phím Tắt & Vùng Focus Thông Minh (`MainWindow`)
- **Phím `Delete` / `Backspace`**:
  - Bắt sự kiện phím trong `keyPressEvent()`.
  - Kiểm tra xem focus hiện tại có nằm trong các ô gõ văn bản (`QLineEdit`, `QPlainTextEdit`, `QTextEdit`) hay không.
  - Nếu **không** gõ văn bản và có clip đang chọn -> Thực hiện xóa clip.
- **Phím `Ctrl + Z` (Undo) & `Ctrl + Y` / `Ctrl + Shift + Z` (Redo)**:
  - Khởi tạo qua `QShortcut`.
  - Khi kích hoạt, kiểm tra nếu focus không ở ô gõ chữ thì gọi `_project.undo()` / `_project.redo()`.
  - Sau khi khôi phục dữ liệu `clips` và `style`, gọi `_inspector.apply_style()` và `_update_ui_state()` để render lại toàn bộ giao diện (Timeline, Inspector, Video Overlay).

---

### 5. Kiểm Thử Unit Test (`tests/test_undo_redo.py` & `tests/test_timeline_widget.py`)
- Viết các bài test cho luồng Undo/Redo:
  1. `test_undo_manager_basic_push_and_undo`: Kiểm tra độc lập class `UndoManager`.
  2. `test_editor_project_undo_redo`: Kiểm tra việc khôi phục dữ liệu trên `EditorProject`.
  3. `test_main_window_undo_redo_shortcuts`: Kiểm tra luồng tích hợp phím tắt trên giao diện ứng dụng.
- Kết quả kiểm thử: **78/78 tests passed (100% thành công)**.
