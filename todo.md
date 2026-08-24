# TODO — MVP2: Subtitle Timeline Editor

## 1. Khảo sát nền tảng và chuẩn bị kiến trúc

- [x] Rà soát các chức năng MVP1 đang có: import video/SRT, preview, style và export MP4.
- [x] Chuẩn hoá model `SubtitleClip`, `SubtitleStyle` và `EditorProject`.
- [x] Thiết kế state trung tâm để `SubtitleClip[]` là single source of truth cho timeline, inspector, preview và export.
- [x] Bảo đảm SRT chỉ được parse khi import, sau đó editor làm việc hoàn toàn trên `SubtitleClip[]`.

## 2. Xây dựng màn hình Editor và các trạng thái cơ bản

- [x] Tạo layout editor chính: video preview, inspector và timeline.
- [x] Hoàn thiện các trạng thái: chưa có video; có video/chưa có subtitle; có subtitle; đang chọn subtitle.
- [x] Kết nối import video và import SRT vào màn hình editor.
- [x] Parse SRT thành danh sách `SubtitleClip` với `id`, `text`, `startMs`, `endMs`.

## 3. Video playback và realtime preview

- [x] Dùng thẻ HTML `<video>` cho phát video realtime.
- [x] Đồng bộ `currentTimeMs` và trạng thái play/pause với video.
- [x] Tìm subtitle active theo thời điểm hiện tại và render overlay trên video.
- [x] Áp dụng style subtitle realtime trong preview (normal/word highlight, font, màu, stroke, vị trí).
- [x] Hỗ trợ sửa text trực tiếp trên preview khi khả thi (double-click, Enter/click-outside để lưu).



## 4. Triển khai timeline subtitle

- [x] Render thước thời gian, video track, subtitle track và playhead.
- [x] Click timeline để seek video.
- [x] Đồng bộ playhead khi video đang phát hoặc khi người dùng seek.
- [x] Cho phép chọn subtitle clip từ timeline và hiển thị trạng thái selected.
- [x] Thêm zoom timeline và quy đổi nhất quán giữa pixel với milliseconds.

## 5. Chỉnh timing trực tiếp trên timeline

- [x] Kéo toàn bộ clip để cập nhật đồng thời `startMs` và `endMs`.
- [x] Kéo mép trái để resize và cập nhật `startMs`.
- [x] Kéo mép phải để resize và cập nhật `endMs`.
- [x] Thêm các ràng buộc hợp lệ: không âm, không vượt video duration và luôn có `endMs > startMs`.
- [x] Kiểm tra preview, inspector và export cùng phản ánh timing mới ngay lập tức.

## 6. Inspector và thao tác subtitle

- [ ] Hiển thị style chung khi chưa chọn subtitle.
- [ ] Hiển thị textarea text và nút Delete khi đã chọn subtitle.
- [ ] Cập nhật text subtitle từ inspector và phản ánh realtime trên timeline/preview.
- [ ] Thêm subtitle tại playhead với thời lượng mặc định 2 giây, tự chọn clip mới để người dùng sửa nội dung.
- [ ] Xoá subtitle đang chọn và dọn trạng thái selection an toàn.

## 7. Hoàn thiện style subtitle

- [ ] Hỗ trợ Normal và Word Highlight; word timing được suy ra từ duration subtitle.
- [ ] Hoàn thiện các control: font family, font size, text color, highlight color, stroke width và position.
- [ ] Xác định rõ cách kế thừa/ghi đè style giữa style chung và `clip.style` (nếu có).
- [ ] Kiểm tra style hiển thị đồng nhất trên preview và khi export.

## 8. Cập nhật export MP4

- [ ] Dùng chính `SubtitleClip[]` đã chỉnh sửa để tạo ASS.
- [ ] Chuyển Normal và Word Highlight sang ASS/FFmpeg tương ứng.
- [ ] Giữ timing, text và style của export khớp với realtime preview.
- [ ] Hiển thị lỗi/trạng thái export rõ ràng và kiểm tra file MP4 đầu ra.

## 9. Kiểm thử và hoàn thiện MVP

- [ ] Test flow đầy đủ: import video → import SRT → chỉnh timeline/text/style → preview → export.
- [ ] Test các tình huống biên: clip đầu/cuối video, resize cực ngắn, clip chồng nhau, SRT rỗng/lỗi và video chưa sẵn sàng.
- [ ] Kiểm tra zoom, seek, play/pause và drag/resize không bị lệch thời gian.
- [ ] Rà soát UI responsive, thông báo lỗi và khả năng thao tác bằng chuột cơ bản.
- [ ] Không triển khai các mục ngoài scope: waveform, word-timing editor, speech-to-text, nhiều track, B-roll, transitions, music hoặc keyframes.
