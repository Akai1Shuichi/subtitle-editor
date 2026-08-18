# Giải thích kiến trúc — Subtitle Video Editor

## 1. ASS Renderer core

*(nội dung cũ giữ nguyên ở dưới, phần này được thêm vào từ giải thích khi code)*

---

## 2. 4 UI States — Editor State Machine

Editor chỉ có **một màn hình duy nhất** nhưng thích ứng theo 4 trạng thái,
được suy ra từ 3 biến boolean: `has_video`, `has_clips`, `selected_clip`.

```
State 1: has_video=F  has_clips=F  selected=F  → drop zone
State 2: has_video=T  has_clips=F  selected=F  → video info + style
State 3: has_video=T  has_clips=T  selected=F  → clip chips + style
State 4: has_video=T  has_clips=T  selected=T  → text editor + style + Delete
```

---

### Trung tâm điều phối: `_update_ui_state()`

**File:** `src/ui/main_window.py` — `MainWindow._update_ui_state()`

Đây là hàm **duy nhất** cập nhật toàn bộ UI. Mọi thay đổi state đều kết thúc
bằng việc gọi hàm này:

```python
def _update_ui_state(self) -> None:
    has_video = self._project.has_video        # VideoInfo != None
    has_clips = self._project.has_clips        # len(clips) > 0
    selected_clip = self._project.clip_by_id(self._selected_clip_id)

    self._header_bar.set_has_video(has_video)
    self._header_bar.set_export_enabled(has_video and has_clips)

    if has_video:
        self._video_panel.set_video_info(...)  # chuyển drop zone → video info

    self._inspector.set_has_video(has_video)   # bật/tắt style section
    self._inspector.select_clip(selected_clip) # bật/tắt text editor

    self._timeline.set_clips(
        self._project.sorted_clips() if has_clips else [],
        selected_clip_id=self._selected_clip_id,
    )
```

---

### State 1 — Chưa có video

**Điều kiện:** `has_video = False`

**VideoPanel** → drop zone mặc định, không gọi `set_video_info()`:
```python
# main_window.py
if has_video:               # ← FALSE → bỏ qua
    self._video_panel.set_video_info(...)
```
`_DropZone` hiển thị icon 🎬 + "Kéo video vào đây" (`video_panel.py`).

**Inspector** → `set_has_video(False)` ẩn toàn bộ style controls:
```python
# inspector.py
def set_has_video(self, has_video: bool) -> None:
    self._add_btn.setEnabled(has_video)       # disabled
    self._style_section.setVisible(has_video) # HIDDEN
    self._style_divider.setVisible(has_video) # HIDDEN
```

---

### State 2 — Có video, chưa có subtitle

**Điều kiện:** `has_video = True`, `has_clips = False`

**VideoPanel** → `set_video_info()` → `_DropZone.set_loaded()` chuyển sang hiển thị
tên file + resolution + duration:
```python
# video_panel.py — _DropZone.set_loaded()
self._icon.setText("🎬")
self._title.setText(name)               # e.g. "video.mp4"
self._sub.setText("1920×1080  ·  00:40")
```

**Inspector** → style section hiện, text editor ẩn vì `select_clip(None)`:
```python
# inspector.py
self._add_btn.setEnabled(True)          # Add Subtitle bật
self._style_section.setVisible(True)    # style hiện

# select_clip(None):
self._clip_section.hide()               # text editor ẩn
self._delete_btn.hide()                 # Delete ẩn
```

**Timeline** → `set_clips([])` → hiển thị hint:
```python
# timeline_placeholder.py
if not sorted_clips:
    self._scroll.hide()
    self._hint.show()   # "Import SRT hoặc nhấn ＋ Add Subtitle"
    return
```

---

### State 3 — Có subtitle (chưa chọn clip)

**Điều kiện:** `has_video = True`, `has_clips = True`, `selected_clip = None`

**Timeline** → render các chip, không chip nào selected:
```python
# timeline_placeholder.py
self._hint.hide()
self._scroll.show()
for clip in sorted_clips:
    chip = _ClipChip(clip, selected=False)   # chip bình thường
    chip.clicked_id.connect(self._on_chip_clicked)
    self._chips_layout.insertWidget(...)
```

**Inspector** → style controls hiện, text editor vẫn ẩn vì `select_clip(None)`:
```python
# inspector.py
def select_clip(self, clip):
    if clip:
        ...           # State 4
    else:
        self._clip_section.hide()   # ← State 3: ẩn text editor
        self._delete_btn.hide()
```

---

### State 4 — Clip đang được chọn

**Trigger:** User click chip → `_ClipChip.mousePressEvent`
→ emit `clicked_id(clip_id)`
→ `TimelinePlaceholder._on_chip_clicked()`
→ emit `clip_selected(clip_id)`
→ `MainWindow._on_clip_selected()`:

```python
# main_window.py
def _on_clip_selected(self, clip_id: str) -> None:
    self._selected_clip_id = clip_id
    self._update_ui_state()   # ← trigger lại toàn bộ
```

**Inspector** → `select_clip(clip)` hiển thị đầy đủ:
```python
# inspector.py
def select_clip(self, clip):
    self._text_edit.setPlainText(clip.text)  # load text
    self._clip_section.show()               # text editor hiện
    self._delete_btn.show()                 # Delete hiện
```

**Chip** được highlight qua CSS property:
```python
# timeline_placeholder.py
chip = _ClipChip(clip, selected=(clip.id == selected_clip_id))
# → chip[selected="true"] → CSS border sáng hơn
```

**Bỏ chọn:** Click lại chip đang chọn → `clip_deselected()` → `_selected_clip_id = None`
→ `_update_ui_state()` → quay về State 3.

---

### Sơ đồ luồng tổng

```
User action
    │
    ├── import video   → _on_video_selected()  → project.video_info = info
    ├── import SRT     → _on_srt_loaded()      → project.clips = [...]
    ├── click chip     → _on_clip_selected()   → _selected_clip_id = id
    ├── click deselect → _on_clip_deselected() → _selected_clip_id = None
    └── add subtitle   → _on_add_subtitle()    → project.clips.append(new)
                                ↓
                    _update_ui_state()   ← MỌI thứ đều qua đây
                            │
                ┌───────────┼────────────────┐
                ↓           ↓                ↓
          has_video?    has_clips?       selected?
               │             │               │
        header + panel   timeline chips  inspector
        set_video_info   set_clips([])   select_clip(clip|None)
        set_has_video    set_has_video   set_has_video
```

> **Nguyên tắc quan trọng:** Không có `if state == 1 / 2 / 3 / 4` nào cả.
> State được **suy ra** từ 3 biến `has_video`, `has_clips`, `selected_clip`
> và mỗi widget tự quyết định hiển thị gì dựa trên input nhận được.
