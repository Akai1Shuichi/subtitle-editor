# Hướng Dẫn Chạy, Test, Build & Push GitHub CI/CD

Tài liệu hướng dẫn các lệnh cài đặt, khởi chạy, kiểm thử, đóng gói ứng dụng **Subtitle Editor** và quy trình đẩy code lên GitHub CI/CD cho cả **Windows, macOS & Linux**.

---

## 1. Cài Đặt Môi Trường (Setup Environment)

Tạo môi trường ảo Python và cài đặt tất cả các thư viện cần thiết:

```bash
# 1. Tạo môi trường ảo (nếu chưa có)
python -m venv .venv

# 2. Kích hoạt môi trường ảo
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (CMD):
.venv\Scripts\activate.bat
# macOS / Linux:
source .venv/bin/activate

# 3. Cài đặt các thư viện phụ thuộc
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
```

---

## 2. Chạy Ứng Dụng Trực Tiếp (Run Application)

Khởi chạy giao diện chính của ứng dụng:

```bash
# Trong môi trường đã activate:
python run.py

# Hoặc chạy trực tiếp qua python venv (Windows):
.venv\Scripts\python.exe run.py
```

---

## 3. Kiểm Thử Đơn Vị (Run Unit Tests)

Chạy bộ test suite với `pytest`:

```bash
# Trong môi trường đã activate:
pytest

# Hoặc chạy trực tiếp qua venv (Windows):
.venv\Scripts\python.exe -m pytest
```

---

## 4. Build Đóng Gói Ứng Dụng (Build Executable Local)

Đóng gói ứng dụng thành file thực thi độc lập bằng PyInstaller:

```bash
# Build bằng file cấu hình spec:
pyinstaller --noconfirm subtitle_editor.spec
```

*File sau khi build thành công sẽ nằm trong thư mục `dist/`:*
- Windows: `dist/subtitle_editor v1.0.exe`
- macOS: `dist/subtitle_editor v1.0`
- Linux (Ubuntu): `dist/subtitle_editor v1.0`

---

## 5. Đẩy Code Lên GitHub & CI/CD Automated Build

Hệ thống CI/CD được cấu hình bằng **GitHub Actions** (`.github/workflows/build.yml`).

### A. Đẩy Code Phát Triển (Trigger CI Build & Test)
Khi push code lên branch `develop` hoặc `main`, GitHub Actions sẽ tự động kiểm tra code và build ứng dụng trên **Windows, macOS và Ubuntu Linux**:

```bash
git add .
git commit -m "feat: update feature XYZ"
git push origin develop
```

### B. Tạo Release Tự Động Với Tag (Trigger GitHub Release)
Khi hoàn tất phiên bản và muốn tạo bản Release chính thức trên GitHub (tự động đính kèm các file zip cài đặt):

```bash
# 1. Tạo Tag mới (ví dụ v1.0.0)
git tag -a v1.0.0 -m "Release Subtitle Editor v1.0.0"

# 2. Push Tag lên GitHub
git push origin v1.0.0
```

GitHub Actions sẽ tự động:
1. Chạy unit tests trên cả 3 hệ điều hành.
2. Build ứng dụng trên Windows, macOS & Ubuntu Linux.
3. Đóng gói 3 file artifact zip:
   - `SubtitleVideoEditor-Windows.zip`
   - `SubtitleVideoEditor-macOS.zip`
   - `SubtitleVideoEditor-Linux.zip`
4. Đăng tải trực tiếp lên mục **Releases** của GitHub repository.
