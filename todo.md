# Kế Hoạch Triển Khai Undo / Redo (Snapshot Siêu Nhẹ)

## 🎯 Mục tiêu
Triển khai tính năng Undo (`Ctrl + Z`) và Redo (`Ctrl + Y` / `Ctrl + Shift + Z`) theo phương pháp **State Snapshot siêu nhẹ** (~50 dòng code):
Lưu lại bản sao `copy.deepcopy((clips, style, selected_clip_id))` mỗi khi người dùng thay đổi trạng thái project.

---

## 📌 Các bước thực hiện

- [x] **1. Cập nhật `todo.md` theo hướng Snapshot siêu nhẹ**
- [x] **2. Thêm `UndoManager` đơn giản vào `src/models.py`**
  - [x] Quản lý 2 stack: `_undo_stack` và `_redo_stack`.
  - [x] Hàm `push_checkpoint(clips, style, selected_clip_id)`: Lưu bản sao trạng thái hiện tại (tối đa 50 bước) và xóa `_redo_stack`.
  - [x] Hàm `undo(current_clips, current_style, current_selected_id)`: Trả về trạng thái trước đó.
  - [x] Hàm `redo(current_clips, current_style, current_selected_id)`: Trả về trạng thái đã undo.
- [x] **3. Tích hợp `save_checkpoint` trước các hành động trong `MainWindow`**
  - [x] Thêm clip phụ đề mới (`_on_add_subtitle_requested`).
  - [x] Xóa clip phụ đề (`_on_clip_delete_requested`).
  - [x] Kéo thả / Đổi mốc thời gian clip (`drag_started`).
  - [x] Sửa chữ trong Inspector (với timer Debounce 500ms).
  - [x] Đổi style / preset phụ đề (`_on_style_changed`).
  - [x] Import file phụ đề mới (SRT / JSON / CapCut).
- [x] **4. Đăng ký phím tắt `Ctrl + Z` và `Ctrl + Y` / `Ctrl + Shift + Z`**
  - [x] Tạo `QShortcut` cho Undo (`Ctrl + Z`) và Redo (`Ctrl + Y` / `Ctrl + Shift + Z`).
  - [x] Kiểm tra nếu focus không nằm trong ô gõ text (`QPlainTextEdit`) thì gọi `undo()` / `redo()` toàn cục và cập nhật lại UI (`_update_ui_state`).
- [x] **5. Viết Unit Test kiểm thử**
  - [x] Kiểm tra các kịch bản Undo / Redo xem trạng thái clips và style được khôi phục chính xác (78/78 tests passed).
