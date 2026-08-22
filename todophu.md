# TODO PHỤ — Tính năng chọn nguồn subtitle cho Word Highlight mode

> Bổ sung sau **Bước 3** (Video playback & realtime preview) trong `todo.md`.
> Khi người dùng chọn mode **Word Highlight**, sẽ có 2 nguồn để import subtitle thay vì chỉ 1.

---

## Mô tả tính năng

Hiện tại khi import SRT ở mode Word Highlight, hệ thống tự chia segment và tính word timing bằng cách chia đều duration theo số từ (không chính xác).

Tính năng mới cho phép người dùng chọn **1 trong 2 nguồn**:

| Nguồn | Cách hoạt động | Độ chính xác |
|---|---|---|
| **SRT** | Tự chia segment theo số từ, phân bổ timing đều theo duration | Trung bình |
| **subtitle.json** | Dùng timestamp thực từng từ ghi âm bởi speech recognition | Cao — đúng theo tốc độ giọng nói |

---

## Cấu trúc file `subtitle.json`

```json
{
  "<uuid>": {
    "words": [
      { "value": "AI",   "from": 0.159, "to": 0.459 },
      { "value": "đang", "from": 0.539, "to": 0.680 }
    ],
    "from": 0.159,
    "to":   1.079,
    "styles": [],
    "itemStyles": null
  }
}
```

- Key: UUID (không liên quan đến SRT clip id — map theo timing)
- `from` / `to`: giây (float), thời điểm bắt đầu/kết thúc cả đoạn
- `words[].from` / `words[].to`: timing chính xác từng từ (giây)
- `styles`: bỏ qua (editor dùng style riêng)

---

## Các bước triển khai

### 1. Cập nhật UI — Thêm lựa chọn nguồn subtitle khi ở Word Highlight mode

- [x] Trong `header_bar.py`: khi mode = `highlight`, hiển thị 2 nút/radio:
  - `📄 Import từ SRT` (hành vi cũ)
  - `🎯 Import từ JSON (word timing)` (hành vi mới)
- [x] Khi mode = `normal`, nút JSON bị disable — không thay đổi luồng normal.
- [x] Nút JSON chỉ active khi có video VÀ mode là `highlight`. Có tooltip giải thích.
- [x] `main_window.py`: wire `import_json_requested` → `_on_json_loaded` (placeholder cho bước 2).
- [x] `main_window.py`: `_on_style_changed` gọi `header_bar.set_highlight_mode()` mỗi khi mode thay đổi.

---

### 2. Tạo parser mới — `json_subtitle_parser.py`

File: `src/json_subtitle_parser.py`

- [ ] Viết hàm `load_subtitle_json(path) -> list[SubtitleClip]`:
  - Đọc và parse file JSON
  - Mỗi entry: `from`/`to` (giây) × 1000 → `start_ms`/`end_ms`
  - Ghép `words[].value` thành `text` (join dấu cách)
  - Tạo `SubtitleClip` với `id = uuid4()`
  - Sort theo `start_ms`
- [ ] Viết hàm `load_word_timing_from_json(path, clips) -> TimingFile`:
  - Map từng entry JSON → clip tương ứng bằng timing overlap
  - Với mỗi entry: tạo `LineTiming` từ `words[]` (từng từ có `start_ms`, `end_ms`)
  - Trả về `TimingFile` (dict `clip.id` → `LineTiming`)
- [ ] Xử lý lỗi: file không tồn tại, JSON sai format, `words` rỗng

---

### 3. Xử lý map JSON entries → SubtitleClip (vấn đề cốt lõi)

> JSON dùng UUID riêng, không khớp với clip id. Cần chiến lược map theo timing.

- [ ] **Chiến lược**: sau khi `load_subtitle_json()` tạo clips với id mới,
  `load_word_timing_from_json()` nhận danh sách clips đó và map entry JSON → clip
  bằng cách so `from`/`to` với `start_ms`/`end_ms` (overlap hoặc nearest).
- [ ] Không cần file SRT kèm theo — JSON đủ thông tin để tạo clips độc lập.
- [ ] Gán `TimingFile` vào `EditorProject.word_timings` ngay sau import.

---

### 4. Cập nhật `main_window.py` — xử lý luồng import JSON

- [ ] Thêm slot `_on_import_json()`:
  - Mở `QFileDialog` lọc `*.json`
  - Gọi `load_subtitle_json()` → nhận `clips`
  - Gọi `load_word_timing_from_json(clips)` → nhận `TimingFile`
  - Gán vào `self._project.clips` và `self._project.word_timings`
  - Cập nhật UI: timeline, inspector, preview
- [ ] Hiển thị thông báo lỗi nếu parse thất bại

---

### 5. Cập nhật `word_timing.py` — đảm bảo tương thích

- [ ] Kiểm tra `TimingFile` và `LineTiming` đủ để chứa timing từ JSON.
- [ ] Nếu cần: thêm factory `LineTiming.from_json_words(words: list[dict])` để tạo
  `LineTiming` trực tiếp từ mảng `words` của JSON.

---

### 6. Kiểm thử

- [ ] Import `subtitle.json` → clips hiển thị đúng text và timing trên timeline.
- [ ] Preview word highlight: từng từ highlight đúng tốc độ giọng nói.
- [ ] So sánh export ASS nguồn SRT vs nguồn JSON — JSON phải chính xác hơn.
- [ ] Edge case: entry `words` rỗng, `from` = `to`, JSON không hợp lệ.
- [ ] Đảm bảo mode `normal` + import SRT vẫn hoạt động bình thường sau khi thêm tính năng.
