# Kế Hoạch Thực Hiện: Thêm Tính Năng Import JSON (CapCut)

## 🎯 Mục Tiêu
Thêm tính năng **Import CapCut JSON**, bố trí nút bấm trước (bên trái) nút **Import JSON (Veed)** hiện tại trên thanh công cụ HeaderBar, trích xuất phụ đề và timing từ khối `"materials" -> "texts"` kết hợp với dữ liệu `tracks` trong các file JSON draft của CapCut (như `draft_content.json` và `draft_content_animated.json`).

---

## 📌 Các Bước Chính Thực Hiện

### Bước 1: Xây dựng Module Parser CapCut JSON (`src/capcut_json_parser.py`) [x]
- **Đọc & Validate**: Đọc file JSON từ CapCut, kiểm tra cấu trúc `materials` và `tracks`.
- **Trích xuất Text**: Duyệt danh sách `"materials" -> "texts"`. Đọc nội dung phụ đề từ field `content` (nếu là JSON string `{"text": "..."}`) hoặc fallback sang field `recognize_text`.
- **Ánh xạ Timing Timeline**:
  - Duyệt danh sách `tracks` có `type: "text"`.
  - Đọc `target_timerange` (đơn vị microsecond `us`), đổi sang millisecond `ms` (`us / 1000`).
  - Hỗ trợ 2 kiểu ánh xạ `material_id`:
    1. `material_id` trỏ trực tiếp đến `id` của text trong `materials.texts`.
    2. `material_id` trỏ tới `materials.text_templates` -> tra cứu `text_material_id` để tìm ra text tương ứng trong `materials.texts`.
- **Trích xuất Word-level Timing**: Đọc mảng `words` (`start_time`, `end_time`, `text`) từ từng đối tượng text trong `materials.texts` (chuyển sang thời gian tuyệt đối `start_ms + word_offset_ms`) để tạo `LineTiming` và `WordTiming`.
- **Trả về dữ liệu**: Trả về `(clips: list[SubtitleClip], timing: TimingFile)` tương thích với hệ thống hiện tại.

### Bước 2: Cập Nhật Thanh Header Bar (`src/ui/header_bar.py`) [x]
- Thêm nút mới `_import_capcut_json_btn` với nhãn `🎬 Import CapCut JSON`.
- Sắp xếp vị trí nút: Đặt nút **Import CapCut JSON** phía trước nút **Import JSON (Veed)** (`_import_json_btn`).
- Thêm Signal `import_capcut_json_requested = Signal()`.
- Cập nhật trạng thái `set_has_video` và `set_mode` để bật/tắt nút hợp lý.

### Bước 3: Tích Hợp Xử Lý Trong Main Window (`src/ui/main_window.py`) [x]
- Thêm handler `_on_import_capcut_json()` trong `MainWindow`.
- Mở `QFileDialog` để chọn file JSON CapCut.
- Gọi parser `capcut_json_parser.load_from_capcut_json(file_path)`.
- Cập nhật dữ liệu Project, load clips lên timeline và hiển thị notification/status bar.

### Bước 4: Kiểm Thử và Xác Nhận (Verification)
- Kiểm thử tự động với 2 file mẫu: `data/draft_content.json` và `data/draft_content_animated.json`.
- Kiểm thử giao diện GUI: Đảm bảo vị trí nút bấm chính xác và thao tác import diễn ra mượt mà.
