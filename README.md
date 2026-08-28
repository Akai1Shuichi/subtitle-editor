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