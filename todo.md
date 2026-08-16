# Subtitle Video Editor — TODO MVP

## Mục tiêu MVP

- App Windows chạy hoàn toàn local.
- Nhập một video và một file phụ đề `.srt`.
- Chọn 2 kiểu subtitle: **Normal** và **Word Highlight**.
- Export ra `.mp4` có subtitle đã được render trực tiếp vào video.

> Stack: Python 3.11+, PySide6, FFmpeg, `pysubs2` (đọc/ghi subtitle ASS), PyInstaller.

## 0. Chuẩn bị dự án

- [ ] Tạo virtual environment Python.
- [ ] Cài dependencies: `PySide6`, `pysubs2`.
- [ ] Tải FFmpeg Windows và kiểm tra lệnh `ffmpeg -version` chạy được.
- [ ] Tạo cấu trúc thư mục:

```text
src/          # mã Python
assets/       # icon, font mẫu (nếu cần)
binaries/     # ffmpeg.exe, ffprobe.exe khi đóng gói
temp/         # file ASS tạm
output/       # video export mặc định
tests/        # test parser/generator
```

- [ ] Viết `README.md`: cách cài, chạy dev, export `.exe`.

## 1. Xử lý subtitle và render (làm trước UI đẹp)

- [ ] Đọc `.srt`, kiểm tra encoding UTF-8 và hiển thị lỗi dễ hiểu nếu file không hợp lệ.
- [ ] Chuyển các dòng subtitle sang `.ass`.
- [ ] Tạo style **Normal**: text trắng, viền tối, shadow nhẹ, vị trí bottom.
- [ ] Tạo lệnh FFmpeg burn file `.ass` vào video và xuất `.mp4`.
- [ ] Kiểm tra export với video dọc và video ngang.
- [ ] Lấy duration/resolution video bằng `ffprobe`.
- [ ] Parse tiến trình FFmpeg để trả về phần trăm export.
- [ ] Xử lý lỗi: thiếu FFmpeg, video không đọc được, hết dung lượng, người dùng hủy export.

## 2. Word Highlight / Karaoke

- [ ] Quy định format dữ liệu timing cho từng từ.
- [ ] Làm bản đơn giản từ SRT: cả câu trắng, khi câu active thì đổi màu hoặc fill theo thời lượng câu.
- [ ] Sinh hiệu ứng bằng ASS karaoke tags (`\\k` / `\\kf`) khi có timing từng từ.
- [ ] Thêm dữ liệu timing từng từ thủ công trong editor (giai đoạn sau MVP cơ bản).

> Lưu ý: SRT chỉ có thời gian của **cả câu**, không có thời gian từng từ. Vì vậy highlight chạy chính xác theo từng từ cần người dùng chỉnh timing hoặc một bước AI/transcription về sau.

## 3. UI PySide6

- [ ] Tạo cửa sổ chính theo layout trong `ui.md`.
- [ ] Nút chọn video; hiển thị tên file, resolution và thời lượng.
- [ ] Nút chọn/import SRT; hiển thị số dòng subtitle.
- [ ] Radio chọn `Normal` / `Word Highlight`.
- [ ] Form style: font, cỡ chữ, text color, highlight color, vị trí.
- [ ] Nút chọn thư mục/tên file output.
- [ ] Nút Export: disable khi thiếu video hoặc subtitle.
- [ ] Progress bar, thời gian đã chạy, nút Cancel.
- [ ] Thông báo Export thành công và nút mở thư mục output.

## 4. Cấu hình project local

- [ ] Lưu cấu hình thành `.json`: paths, style, mode, output path.
- [ ] Mở lại project và khôi phục form.
- [ ] Không copy video vào app; chỉ lưu đường dẫn local để tránh project nặng.

## 5. Kiểm thử MVP

- [ ] Test SRT tiếng Việt có dấu, emoji và ký tự đặc biệt.
- [ ] Test video ngang 16:9, dọc 9:16 và 1:1.
- [ ] Test video 1–5 phút; kiểm tra progress và file output.
- [ ] Test font không tồn tại: fallback font rõ ràng.
- [ ] Test đường dẫn Windows có khoảng trắng và tiếng Việt.
- [ ] Test hủy export, rồi export lại không bị file tạm lỗi.

## 6. Đóng gói Windows

- [ ] Bundle `ffmpeg.exe` + `ffprobe.exe` vào app.
- [ ] Đóng gói với PyInstaller thành `.exe` / installer.
- [ ] Chạy thử trên một máy Windows chưa cài Python/FFmpeg.
- [ ] Ghi version, icon app và hướng dẫn cài đặt.

## Không làm trong MVP đầu tiên

- [ ] AI tự tạo phụ đề / Whisper.
- [ ] Timeline video đầy đủ, kéo thả subtitle theo từng frame.
- [ ] Nhiều track subtitle, template marketplace, cloud sync.
- [ ] macOS installer và code signing.

## Tiêu chí hoàn thành MVP

- [ ] Người dùng chọn video + SRT, chọn một trong hai style, bấm Export.
- [ ] App xuất MP4 thành công trên Windows mà không cần cài thêm FFmpeg/Python.
- [ ] Video output hiển thị đúng tiếng Việt và style đã chọn.
