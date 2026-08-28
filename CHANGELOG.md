# 📜 Nhật Ký Thay Đổi (CHANGELOG)

Tất cả các thay đổi đáng chú ý của dự án **Subtitle Video Editor** sẽ được ghi nhận tại đây.

---

## [1.0.0] - 2026-08-28

### 🎉 Tính Năng Mới (Features)
- **Hệ thống Auto-Updater (Cập Nhật Tự Động)**:
  - Tích hợp GitHub Releases API kiểm tra phiên bản mới tự động.
  - Tự động nhận diện hệ điều hành người dùng (**Windows**, **macOS**, **Linux**) để tải file cài đặt phù hợp.
  - Hiển thị Dialog thông tin bản cập nhật, Release Notes và thanh tiến trình phần trăm %.
  - Tự động tắt ứng dụng hiện tại khi tiến hành mở file cài đặt ghi đè để tránh lỗi File Lock trên Windows.
  - Hỗ trợ phím tắt Debug (`Shift` / `Ctrl` + Click nút Cập nhật) để ép hiển thị giao diện test.
- **Import Phụ Đề Đa Nguồn**:
  - Hỗ trợ file phụ đề SubRip (`.srt`).
  - Hỗ trợ dự án CapCut JSON (`draft_content.json`).
  - Hỗ trợ VEED JSON / Word Timing JSON.
- **Hiệu ứng Karaoke (Word Highlight)**:
  - Hiển thị từ tô sáng theo thời gian thực (word-level timing).
- **Xuất Video MP4**:
  - Tích hợp FFmpeg render phụ đề ASS/SSA trực tiếp vào MP4.
- **CI/CD Workflows**:
  - Thiết lập GitHub Actions tự động kiểm thử (`pytest`), build PyInstaller và phát hành GitHub Release khi push tag `v*`.

---

## [0.9.0] - 2026-08-15

### 🚀 Khởi Tạo Dự Án (Initial Release)
- Xây dựng giao diện ứng dụng PySide6 MVP: Dashboard quản lý dự án, Editor chính.
- Player xem trước video và timeline hiển thị các clip phụ đề.
- Inspector tùy chỉnh style: font, màu chữ, kích thước, căn lề.
