# Giải thích khái niệm — Subtitle Editor

---

## 1. Word Timing là gì?

Hãy tưởng tượng một câu subtitle:

```
"AI đang thay đổi cách chúng ta lập trình"
start: 0.159s → end: 3.200s
```

Ở mode **Normal**, toàn bộ câu hiện cùng lúc từ 0.159s đến 3.200s — không biết từ nào đang được nói tại thời điểm nào.

Ở mode **Word Highlight**, cần biết **từng từ** xuất hiện lúc nào:

```
"AI"      → 0.159s → 0.459s   ← đang highlight
"đang"    → 0.539s → 0.680s
"thay"    → 0.719s → 0.819s
"đổi"     → 0.879s → 1.000s
...
```

**Word Timing = dữ liệu timestamp của từng từ** để biết lúc nào highlight từ nào.

---

### Cấu trúc trong code (3 lớp lồng nhau)

```
TimingFile               ← toàn bộ video
  └── LineTiming[]       ← một dòng subtitle
        └── WordTiming[] ← một từ đơn
```

```python
# WordTiming — một từ
WordTiming(word="AI", start_ms=159, end_ms=459)

# LineTiming — một dòng, chứa nhiều từ
LineTiming(
    index=0,           # dòng thứ mấy (0-based)
    start_ms=159,
    end_ms=3200,
    words=[
        WordTiming("AI",   159,  459),
        WordTiming("đang", 539,  680),
        WordTiming("thay", 719,  819),
        ...
    ]
)

# TimingFile — cả file video
TimingFile(
    source_srt="video.srt",
    lines=[LineTiming(...), LineTiming(...), ...]
)
```

---

### Có 2 nguồn tạo ra Word Timing

| Nguồn | Cách tính | Chính xác? |
|---|---|---|
| **Từ SRT** | Chia đều duration / số từ | ❌ Ước lượng |
| **Từ subtitle.json** | Timestamp thực từ speech recognition | ✅ Chính xác |

---

## 2. Factory `classmethod` là gì?

### Vấn đề cần giải quyết

`LineTiming` thường được tạo thế này:

```python
# Cách thông thường — phải tự xử lý hết
line = LineTiming(
    index=0,
    start_ms=159,
    end_ms=1079,
    words=[
        WordTiming(word="AI",   start_ms=159, end_ms=459),
        WordTiming(word="đang", start_ms=539, end_ms=680),
    ]
)
```

Nhưng dữ liệu từ `subtitle.json` lại có format khác hoàn toàn:

```python
# Dữ liệu thô từ JSON
json_words = [
    {"value": "AI",   "from": 0.159, "to": 0.459},  # giây, không phải ms!
    {"value": "đang", "from": 0.539, "to": 0.680},
]
```

Mỗi lần dùng phải **tự viết lại** đoạn convert: giây→ms, validate, clamp... rất dễ sai và lặp code.

---

### Factory classmethod giải quyết bằng cách

```python
@classmethod
def from_json_words(cls, index, start_ms, end_ms, json_words):
    # Logic convert + validate chỉ viết 1 lần tại đây
    ...
    return cls(index=index, start_ms=start_ms, end_ms=end_ms, words=word_timings)
```

Khi dùng:

```python
# Gọn, rõ ràng, không cần lo logic convert
line = LineTiming.from_json_words(
    index=0,
    start_ms=159,
    end_ms=1079,
    json_words=[{"value": "AI", "from": 0.159, "to": 0.459}, ...]
)
```

---

### Tại sao `classmethod` chứ không phải hàm thường?

```python
# Hàm thường — lơ lửng bên ngoài, không biết nó trả về gì từ cái tên
line_timing = parse_json_to_line_timing(json_words)

# classmethod — gắn liền với class, đọc tên biết ngay output là gì
line = LineTiming.from_json_words(...)
```

`cls` bên trong chính là `LineTiming` — nên `cls(...)` tương đương `LineTiming(...)`.

| | Hàm thường | `classmethod` |
|---|---|---|
| Gắn với class | ❌ | ✅ |
| Kế thừa hoạt động đúng | ❌ | ✅ |
| Rõ ràng output là gì | ❌ | ✅ |
| Dễ tìm trong IDE | ❌ | ✅ |

---

### Ví dụ factory classmethod có sẵn trong Python

Pattern này rất phổ biến, Python stdlib dùng khắp nơi:

```python
datetime.fromisoformat("2024-01-01")   # tạo datetime từ string ISO
Path.cwd()                             # tạo Path từ thư mục hiện tại
dict.fromkeys(["a", "b"], 0)          # tạo dict từ list keys
int.from_bytes(b"\xff", "big")        # tạo int từ bytes
```

---

### Tóm lại

> **Factory classmethod** = cách tạo object từ một định dạng dữ liệu khác,
> đóng gói toàn bộ logic convert vào trong chính class đó —
> thay vì rải rác khắp nơi.

> **Word Timing** = dữ liệu timestamp từng từ trong một dòng subtitle,
> dùng để biết lúc nào cần highlight từ nào khi phát video.
