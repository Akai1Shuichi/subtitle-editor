# Giải thích lõi tạo và animate subtitle

## Tổng quan luồng dữ liệu

```
File .srt
   │
   ▼  subtitle_parser.py
pysubs2.SSAFile (danh sách SRT events)
   │
   ├── (nếu có)  word_timing.py → TimingFile  (timing từng từ)
   │
   ▼  ass_builder.py  ←── SubtitleSettings (font, màu, vị trí)
pysubs2.SSAFile (ASS events đã render)
   │
   ▼  exporter.py
FFmpeg burn subtitle → MP4 output
```

---

## 1. Đọc SRT — `subtitle_parser.py`

### `load_srt(path)`

Đọc file `.srt` bằng `pysubs2`, trả về `SSAFile` — danh sách các **SRT event**, mỗi event gồm:
- `start` / `end` (milliseconds)
- `text` (nội dung câu)

```python
subs = pysubs2.SSAFile.from_string(text, format_="srt")
```

File đọc theo encoding `utf-8-sig` (tự bỏ BOM nếu có). Ném lỗi rõ ràng nếu không phải UTF-8 hoặc SRT rỗng.

---

## 2. Timing từng từ — `word_timing.py`

### Cấu trúc dữ liệu

| Class | Ý nghĩa |
|---|---|
| `WordTiming` | Timing của **một từ**: `word`, `start_ms`, `end_ms` |
| `LineTiming` | Timing của **một dòng subtitle** + danh sách `WordTiming` |
| `TimingFile` | Toàn bộ timing, tương ứng 1-1 với một file SRT |

### File sidecar `.words.json`

Lưu cạnh file `.srt`, ví dụ `video.words.json`:

```json
{
  "version": 1,
  "source_srt": "video.srt",
  "lines": [
    {
      "index": 0,
      "start_ms": 1000,
      "end_ms": 3000,
      "words": [
        {"word": "AI",   "start_ms": 1000, "end_ms": 1300},
        {"word": "đang", "start_ms": 1320, "end_ms": 1600}
      ]
    }
  ]
}
```

Nếu **không có** file này, `ass_builder.py` tự chia đều thời gian cho từng từ (xem phần 3).

---

## 3. Lõi tạo và animate subtitle — `ass_builder.py`

Đây là **file trung tâm** của toàn bộ hệ thống.

### 3.1 Quyết định thiết kế quan trọng: KHÔNG dùng ASS karaoke `\kf`

> ASS karaoke (`\kf`) vẽ một dải màu từ trái sang phải qua từng từ.  
> Module này **không dùng** kỹ thuật đó vì lý do:
> - `\kf` gây ra **layout shift** (chữ bị dịch chuyển khi scale)
> - Thay vào đó: **chuyển màu toàn bộ từ** (trắng → vàng) và giữ vị trí caption ổn định tuyệt đối

### 3.2 `SubtitleSettings` — cấu hình giao diện

```python
@dataclass(frozen=True)
class SubtitleSettings:
    fontname: str = "Arial Black"
    fontsize: int = 54
    text_color: tuple = (255, 255, 255)       # trắng
    highlight_color: tuple = (255, 217, 0)    # vàng
    stroke_color: tuple = (0, 0, 0)           # viền đen
    stroke_width: float = 4.0
    shadow: float = 2.0
    position_y: int = 82    # % từ trên xuống (= bottom 18%)
    max_words_per_group: int = 5
    alignment: Alignment = Alignment.BOTTOM_CENTER
```

### 3.3 `_style_for()` — tạo ASS Style

Chuyển `SubtitleSettings` → `pysubs2.SSAStyle`, chuẩn hóa các giá trị pixel theo `video_height`:

```python
marginv = round((100 - settings.position_y) * video_height / 100)
```

Ví dụ: `position_y=82`, `video_height=1280` → `marginv = 230px` từ đáy.

---

### 3.4 `SubtitleRenderer.build()` — điểm vào chính

```python
def build(self, subs, *, word_timings=None, video_width=0, video_height=0) -> SSAFile
```

Duyệt từng SRT event:
- **Nếu mode = `"normal"`**: copy thẳng event sang ASS, không có highlight.
- **Nếu mode = `"highlight"`**: qua pipeline phân đoạn + render theo từng từ.

---

### 3.5 `_segments()` — chia câu thành nhóm từ nhỏ

Mỗi SRT event (một câu dài) được chia thành các **segment** 2–5 từ. Lý do: tránh caption tràn quá nhiều dòng.

**Bước 1 — Gán timing cho từng từ:**

```python
# Nếu có word timing chính xác:
timed = [SubtitleWord(w, t.start_ms, t.end_ms) for w, t in zip(words, timing.words)]

# Nếu KHÔNG có → chia đều thời gian:
timed = [
    SubtitleWord(word,
        start = event.start + round(i * duration / len(words)),
        end   = event.start + round((i+1) * duration / len(words))
    )
    for i, word in enumerate(words)
]
```

**Bước 2 — Nhóm thành chunk:**

```python
size = max(2, min(5, settings.max_words_per_group))
chunks = [timed[i:i+size] for i in range(0, len(timed), size)]
```

Mỗi chunk là một `SubtitleSegment(start_ms, end_ms, words)`.

---

### 3.6 `_segment_events()` — tạo ASS events từ một segment

```
Segment: ["AI", "đang", "thay", "đổi", "cách"]
          ├──── window khi "AI" active ────┤
                ├──── window khi "đang" active ────┤
                       ...
```

Với mỗi từ `active` trong segment:
- `start` = `active.start_ms`
- `end` = `next_word.start_ms` (hoặc `segment.end_ms` nếu là từ cuối)

→ Tạo **một ASS event** cho mỗi "window" thời gian đó.

```python
end = (segment.words[active_index + 1].start_ms
       if active_index + 1 < len(segment.words)
       else segment.end_ms)
```

---

### 3.7 `_render_words()` — đây là nơi "animate" xảy ra ✨

Đây là hàm tạo ra **hiệu ứng highlight từng từ** (TikTok-style).

```python
def _render_words(self, words, active_index) -> str:
```

**Nguyên tắc quan trọng:**  
> **Luôn hiển thị đầy đủ tất cả các từ trong segment**, không build up từng từ một.  
> Lý do: nếu caption mọc dần từng từ → chiều rộng caption thay đổi → text bị "nhảy" trên màn hình.

**Logic render:**

```
words = ["AI", "đang", "thay", "đổi"]
active_index = 1  (từ "đang" đang được highlight)

Kết quả text ASS:
  "AI {\1c&H00D9FF&}đang{\r} thay\Nđổi"
         ↑ đổi màu vàng  ↑ reset về màu mặc định
```

Cụ thể:
```python
for index, word in enumerate(words):
    if index == active_index:
        rendered.append(r"{\1c&H00D9FF&}%s{\r}" % word.text)  # highlight vàng
    else:
        rendered.append(word.text)                              # giữ màu trắng
    if index + 1 == split_at:
        rendered.append(r"\N")   # xuống dòng tại điểm giữa để cân bằng 2 dòng
```

**Màu vàng trong ASS:** `\1c&H00D9FF&` là màu `(255, 217, 0)` viết dưới dạng BGR hex của ASS.

**Line-break tự động:**  
Khi segment có nhiều hơn 1 từ, tự xuống dòng tại điểm giữa:
```python
split_at = max(1, (len(words) + 1) // 2)
```

Ví dụ: 4 từ → xuống dòng sau từ thứ 2. Kết quả: 2 dòng đều nhau.

---

### 3.8 Kết quả cuối: từng ASS event trong output

Giả sử SRT event: `"AI đang thay đổi cách"` từ 1000ms đến 3000ms, 5 từ:

| Event | Thời gian | Nội dung ASS text (tóm tắt) |
|---|---|---|
| 1 | 1000 → 1400ms | **`AI`** đang\Nthay đổi cách |
| 2 | 1400 → 1800ms | AI **`đang`**\Nthay đổi cách |
| 3 | 1800 → 2200ms | AI đang\N**`thay`** đổi cách |
| 4 | 2200 → 2600ms | AI đang\Nthay **`đổi`** cách |
| 5 | 2600 → 3000ms | AI đang\Nthay đổi **`cách`** |

Mỗi event có text đầy đủ, chỉ khác nhau từ nào được bọc tag màu vàng → **caption không nhảy, chỉ màu thay đổi**.

---

## 4. Burn subtitle vào video — `exporter.py`

### `export_video()`

Gọi FFmpeg với filter `ass=`:

```python
cmd = [
    ffmpeg, "-y",
    "-i", str(video_info.path),
    "-vf", f"ass='{ass_escaped}'",   # ← burn subtitle vào frame
    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
    "-c:a", "aac", "-b:a", "192k",
    "-movflags", "+faststart",
    str(output_path),
]
```

### Tracking tiến trình

FFmpeg in ra stderr các dòng như:
```
frame=  120 fps=30 time=00:00:04.00 bitrate=...
```

Module parse `time=HH:MM:SS.xx` → tính phần trăm:
```python
pct = min(secs / duration * 100, 99.9)
on_progress(pct)
```

### Hủy export

Nếu `cancel_event.is_set()` → `proc.kill()` + xóa file output dở dang.

### `generate_preview_clip()`

Giống `export_video` nhưng:
- Chỉ render `duration=5` giây đầu
- Dùng `-preset ultrafast` để nhanh nhất
- Lưu vào `temp/preview.mp4`

---

## 5. Thông tin video — `video_info.py`

### `probe_video(path)`

Chạy `ffprobe -print_format json -show_streams -show_format` → parse JSON → lấy:
- `width`, `height` từ video stream
- `fps` từ `r_frame_rate` (dạng `"30000/1001"` → tính thành float)
- `duration` từ `format.duration` (ưu tiên hơn stream.duration vì chính xác hơn)

---

## 6. Sơ đồ luồng xử lý chi tiết

```
load_srt("video.srt")
     │
     │  SSAFile [event0, event1, ...]
     ▼
SubtitleRenderer.build(subs, word_timings=..., video_width=..., video_height=...)
     │
     │  Với mỗi event:
     │
     ├── mode="normal"  → copy thẳng event → out.events
     │
     └── mode="highlight"
              │
              ▼ _segments(event, text, timing)
              │
              │  Gán timing từng từ (exact hoặc linear interpolation)
              │  Nhóm thành chunks 2–5 từ
              │
              ▼ _segment_events(segment)
              │
              │  Với mỗi từ active trong segment:
              │    tính [start, end] window
              │
              ▼ _word_events(segment, active_index, start, end)
              │
              ▼ _render_words(words, active_index)
              │
              │  Build ASS text:
              │    từ highlight → bọc {\1c&H00D9FF&}...{\r}
              │    các từ còn lại → text thường
              │    điểm giữa → chèn \N (xuống dòng)
              │
              └── SSAEvent(start, end, text=rendered_text)
                       ↓
              out.events.append(event)

out (SSAFile ASS) → save_ass() → video.ass
                              → export_video() → FFmpeg → video_out.mp4
```

---

## 7. Tóm tắt kỹ thuật cốt lõi

| Vấn đề | Giải pháp |
|---|---|
| Highlight từng từ | Tạo **N ASS event riêng biệt** cho mỗi từ, mỗi event có tag màu cho 1 từ |
| Tránh caption nhảy | Luôn render **đủ tất cả từ** trong segment, chỉ đổi màu |
| Tránh layout shift | **Không dùng `\kf` karaoke** (vốn có side effect scale glyph) |
| Không có word timing | Chia đều `(end - start) / N` cho N từ |
| Xuống dòng cân đối | Tự chèn `\N` tại điểm giữa segment |
| Vị trí Y linh hoạt | `marginv = (100 - position_y%) × video_height` |
