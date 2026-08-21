# Giải thích flow — Bước 3: Video playback và realtime preview

Mục tiêu của bước 3 là để video đang phát, timeline và subtitle overlay luôn
đọc cùng một thời điểm. Ứng dụng desktop PySide nên dùng `QMediaPlayer` thay
cho thẻ HTML `<video>`; vai trò playback và các event thời gian là tương đương.

## Nguồn dữ liệu chung

`EditorProject` là state trung tâm:

```text
EditorProject
├── video_info       thông tin video đã import
├── clips[]          SubtitleClip(id, text, start_ms, end_ms)
├── style            SubtitleStyle chung
└── word_timings     timing từng từ (nếu có sidecar .words.json)
```

Timeline, Inspector, realtime preview và export đều đọc từ `clips[]`; không
parse lại SRT sau khi import.

## 1. Import video

```text
Chọn/kéo video
  → MainWindow._on_video_selected(path)
  → probe_video(path) lấy resolution + duration
  → project.video_info = info
  → VideoPanel.load_video(path)
  → QMediaPlayer.setSource(...)
  → QVideoSink gửi từng QVideoFrame cho VideoCanvas
```

`VideoCanvas` tự vẽ frame vào vùng letterbox. Cách dùng `QVideoSink` thay vì
`QVideoWidget` cho phép subtitle được vẽ trong cùng một `paintEvent`, nên overlay
không bị video GPU che trên Linux/Wayland.

Khi media backend biết duration thật, `durationChanged(ms)` cập nhật lại thời
lượng hiển thị ở timeline. Nếu media/codec không phát được, `playback_error`
được chuyển lên `MainWindow` để báo lỗi.

## 2. Play, pause và seek

```text
Nút ▶ / ⏸ timeline
  → TimelinePlaceholder.play_pause_requested
  → VideoPanel.toggle_play_pause()
  → QMediaPlayer.play() hoặc pause()
  → playbackStateChanged
  → MainWindow._on_playback_state_changed()
  → đổi icon nút timeline

Click một clip timeline
  → clip_selected(id) + seek_requested(clip.start_ms)
  → VideoPanel.seek(ms)
  → QMediaPlayer.setPosition(ms)
```

Timeline hiện chỉ là placeholder dạng chip; click chip seek đến đầu clip. Thước
thời gian, playhead kéo được và drag/resize clip thuộc bước 4–5.

## 3. Đồng bộ thời gian và active subtitle

Khi player đổi vị trí, nó emit `positionChanged(ms)`:

```text
QMediaPlayer.positionChanged(ms)
  → VideoPanel.time_changed(ms)
  → MainWindow._on_time_changed(ms)
  → current_time_ms = ms
  → project.active_clip_at(ms)
  → VideoPanel.set_active_clip(active_clip, style, ms, ...)
  → VideoCanvas.update()
  → TimelinePlaceholder.set_current_time(ms, duration_ms)
```

`active_clip_at(ms)` chọn clip thỏa `start_ms <= ms < end_ms`. Nếu không có
clip active, canvas chỉ vẽ video frame.

## 4. Realtime subtitle overlay

`VideoCanvas._draw_subtitle()` dùng active clip, style và kích thước video gốc
để vẽ text lên đúng vùng letterbox. Preview hỗ trợ:

- Normal và Word Highlight.
- Font, màu chữ, màu highlight, viền, shadow, căn trái/giữa/phải và vị trí.
- Word timing từ `.words.json` nếu timing hợp lệ; nếu không có thì suy ra đều
  từ duration của subtitle.

Với Normal, ASS được đặt `WrapStyle=1` để quy tắc xuống dòng theo thứ tự từ
giống preview. Font realtime quy đổi 72 DPI (ASS/libass) sang 96 DPI (Qt), và
stroke/shadow scale theo kích thước hiển thị. Vì vậy preview và FFmpeg export
dùng cùng đơn vị style; anti-alias có thể vẫn khác khoảng 1–2 px do Qt và
libass là hai renderer khác nhau.

## 5. Khi người dùng sửa nội dung hoặc style

```text
Sửa text trong Inspector
  → clip_text_changed(id, text)
  → sửa trực tiếp project.clips[]
  → render lại chip timeline + refresh overlay

Đổi style trong Inspector
  → style_changed(style)
  → project.style = style
  → refresh overlay
```

Không có inline edit trên video preview: text chỉ sửa trong Inspector để giữ
interaction đơn giản và tránh hai nơi cùng chỉnh một dữ liệu.

## 6. Quan hệ với export

Nút `Export MP4` ở header gọi `clips_to_ssa(project.clips, project.style, ...)`
để tạo file ASS tạm, sau đó FFmpeg burn ASS vào video. Vì export dùng chính
`SubtitleClip[]`, `SubtitleStyle` và word timing như realtime preview, text,
timing và style đã chỉnh là dữ liệu được xuất ra.

```text
project.clips[] + project.style
        ├── realtime: VideoCanvas
        └── export: clips_to_ssa → ASS → FFmpeg → MP4
```

## Giới hạn hiện tại của bước 3

- Có play/pause, seek khi click clip và time display.
- Chưa có thước thời gian thật, click seek theo vị trí chuột, zoom, drag hay
  resize timing; các phần đó nằm ở bước 4–5.
- `＋ Add Subtitle` chỉ có một nút ở thanh Timeline; clip mới dài mặc định 2
  giây tại playhead và được chọn để sửa trong Inspector.
