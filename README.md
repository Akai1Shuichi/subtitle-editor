# 🎬 Subtitle Video Editor

**Subtitle Video Editor** là ứng dụng Desktop mạnh mẽ, hiện đại được xây dựng bằng **Python** và **PySide6 (Qt6)** chuyên dùng để chỉnh sửa, thêm phụ đề video, làm hiệu ứng karaoke tô sáng từ (**Word Timing / Karaoke Highlight**), nạp phụ đề từ nhiều nguồn và xuất video MP4 sắc nét trực tiếp bằng **FFmpeg**.

---

## ✨ Tính Năng Nổi Bật

### 1. 📥 Nhập Video & Phụ Đề Đa Dạng
- **Video**: Hỗ trợ đầy đủ các định dạng video phổ biến: `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`, `.m4v`.
- **Phụ Đề SRT**: Import và export định dạng SubRip Subtitle (`.srt`).
- **CapCut JSON**: Import trực tiếp file dự án CapCut (`draft_content.json`).
- **VEED / Word Timing JSON**: Import file json chứa timing chi tiết tới từng từ (word-level timestamps).

### 2. 🎤 Karaoke & Word Highlight Effect
- Hiệu ứng tô sáng chữ/từ tự động theo thời gian thực (word-level highlight) như các ứng dụng chỉnh sửa chuyên nghiệp.
- Xem trước trực quan ngay trên trình phát video.

### 3. 🎨 Chỉnh Sửa Định Dạng & Vị Trí Phụ Đề
- Đổi màu chữ, màu chữ tô sáng (highlight color), font chữ, kích thước (font size).
- Tùy chỉnh viền chữ (outline), bóng (shadow), căn lề (left/center/right) và vị trí hiển thị (top/center/bottom).
- Hỗ trợ lưu và chọn các bộ mẫu style thiết lập sẵn (Preset Selector).

### 4. ⏱️ Timeline Chỉnh Sửa Trực Quan
- Dải thanh thời gian (Timeline Widget) hiển thị trực tiếp vị trí các clip phụ đề.
- Kéo thả chỉnh sửa thời gian bắt đầu (start time) và kết thúc (end time) mượt mà.
- Hỗ trợ Undo / Redo thao tác chỉnh sửa.

### 5. 🚀 Xuất Video MP4 Siêu Tốc
- Tích hợp trực tiếp engine **FFmpeg** để render phụ đề ASS/SSA vào video gốc với tốc độ cao và chất lượng sắc nét.

### 6. 🔄 Tự Động Cập Nhật Qua GitHub Releases API (Auto-Updater)
- **Tự động kiểm tra**: Phát hiện ngầm khi có bản phát hành mới trên GitHub.
- **Nhận diện OS**: Tự động lọc và tải đúng file cài đặt tương ứng với Hệ Điều Hành hiện tại (**Windows**, **macOS**, **Linux**).
- **Ghi đè an toàn**: Hỗ trợ tự động thoát app sau khi tải xong để tiến hành cài đặt mà không bị lỗi khóa file (file locking).
- **Chế độ Debug**: Giữ phím `Shift` hoặc `Ctrl` khi click nút **"🔄 Cập nhật"** để test giao diện Cập Nhật.

---

## 🛠️ Yêu Cầu Hệ Thống & Cài Đặt

### 1. Môi Trường
- **Python**: `>= 3.10` (Khuyên dùng Python 3.11)
- **FFmpeg**: Đã được cài đặt và thêm vào PATH hệ thống (hoặc đặt trong thư mục `binaries/`).

### 2. Cài Đặt Thư Mục Dự Án
```bash
# Clone repository
git clone https://github.com/Akai1Shuichi/subtitle-editor.git
cd subtitle-editor

# Tạo và kích hoạt môi trường ảo (Virtualenv)
python -m venv .venv
# Trên Windows:
.venv\Scripts\activate
# Trên macOS/Linux:
source .venv/bin/activate

# Cài đặt thư viện phụ thuộc
pip install -r requirements.txt
```

---

## 🚀 Khởi Chạy Ứng Dụng

Chạy ứng dụng từ terminal:
```bash
python -m src.main
```
hoặc:
```bash
python run.py
```

---

## 📦 Đóng Gói Ứng Dụng (Build Executable)

Ứng dụng sử dụng **PyInstaller** để đóng gói thành file thực thi độc lập:

```bash
pyinstaller --noconfirm subtitle_editor.spec
```
File thực thi sau khi build nằm trong thư mục `dist/`.

---

## 🤖 CI/CD Tự Động Phát Hành Qua GitHub Actions

Dự án đã thiết lập quy trình CI/CD tự động trong `.github/workflows/build.yml`:
- Khi tạo và push tag mới (ví dụ: `git tag v1.0.0 && git push origin v1.0.0`), GitHub Actions sẽ:
  1. Chạy tự động bộ unit tests (`pytest`).
  2. Build file thực thi độc lập trên 3 hệ điều hành: **Windows (`.exe` / `.zip`)**, **macOS (`.zip`)**, **Linux (`.zip`)**.
  3. Tự động khởi tạo Release trên GitHub và đính kèm danh sách file cài đặt.