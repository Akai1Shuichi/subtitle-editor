# Danh Sách Các Bước Triển Khai Chức Năng: Project List (Quản Lý Dự Án)

## Phase 1: Data Model & Storage Layer (Lớp Dữ Liệu & Lưu Trữ)
- [x] **Định nghĩa Data Structure cho Project Metadata (`ProjectMetadata`)**:
  - Các trường: `project_id`, `name`, `created_at`, `updated_at`, `video_path`, `thumbnail_path`, `duration_ms`, `clip_count`.
- [x] **Xây dựng Project Serialization / Deserialization**:
  - Hỗ trợ lưu `EditorProject` thành file dự án (định dạng `.subproj` hoặc JSON) chứa clips, style, thông tin video và cấu hình.
  - Hỗ trợ load file dự án khôi phục lại đầy đủ state cho `EditorProject`.
- [x] **Tạo Module `ProjectManager` (`src/project_manager.py`)**:
  - `list_projects()`: Quét và trả về danh sách tất cả các dự án trong thư mục lưu trữ (`data/projects/`).
  - `create_project(name, video_path, srt_path)`: Khởi tạo dự án mới và lưu trữ ban đầu.
  - `load_project(project_id)`: Đọc và load dữ liệu dự án.
  - `save_project(project)`: Lưu state hiện tại của dự án.
  - `delete_project(project_id)`: Xóa file dự án và cache dữ liệu liên quan.
  - `duplicate_project(project_id)`: Nhân bản dự án hiện có.
  - `rename_project(project_id, new_name)`: Đổi tên dự án.

## Phase 2: Project List UI Component (Giao Diện Danh Sách Dự Án)
- [x] **Thiết kế Component `ProjectCardWidget` (`src/ui/project_card.py`)**:
  - Hiển thị thumbnail video, tên dự án, thời lượng, số lượng clip, thời gian cập nhật lần cuối.
  - Các nút thao tác nhanh (Mở, Đổi tên, Nhân bản, Xóa).
- [x] **Thiết kế Component `ProjectListView` (`src/ui/project_list_view.py`)**:
  - Chế độ hiển thị dạng Grid (Cards) hoặc List (Bảng).
  - Thanh tìm kiếm (Search bar) lọc dự án theo tên.
  - Nút "Tạo Dự Án Mới" (`+ New Project`) kèm dialog chọn Video / Subtitle.
  - Hiển thị trạng thái trống (Empty state) khi chưa có dự án nào.
  - Cảnh báo và hỗ trợ liên kết lại (relink) khi file video gốc bị di chuyển/xóa.

## Phase 3: Integration & Navigation (Tích Hợp Luồng Ứng Dụng)
- [x] **Cập nhật `HeaderBar` & Menu (`src/ui/header_bar.py`)**:
  - Thêm nút "Projects" / "Danh sách dự án" trên Header Bar.
  - Thêm danh sách "Recent Projects" (Dự án gần đây) để mở nhanh.
- [x] **Quản lý chuyển đổi View trong `MainWindow` (`src/ui/main_window.py`)**:
  - Chuyển đổi linh hoạt giữa giao diện Dashboard Project List và Editor View.
  - Tự động lưu dự án hiện tại (Auto-save) khi chuyển sang dự án khác hoặc đóng app.
  - Nạp state dự án mới vào `EditorProject`, đồng bộ làm mới UI trên Video Panel, Timeline Widget, và Inspector.

## Phase 4: Unit Testing & Verification (Kiểm Thử)
- [x] **Viết Unit Tests (`tests/test_project_manager.py`)**:
  - Kiểm thử CRUD dự án: tạo mới, lưu, đọc, đổi tên, xóa, nhân bản.
  - Kiểm thử xử lý lỗi dữ liệu (file hỏng, thiếu asset video).
- [x] **Kiểm thử thủ công (Manual Verification)**:
  - Thao tác thực tế luồng tạo dự án mới -> chỉnh sửa -> tự động lưu -> chuyển dự án khác -> nạp lại state chính xác.
