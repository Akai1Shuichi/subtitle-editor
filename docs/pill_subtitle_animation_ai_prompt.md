# AI Coding Prompt — FIX Pill Subtitle Animation to Match HTML Behavior

## Mục tiêu

Sửa implementation **Pill Subtitle Animation** hiện tại vì đang có 2 lỗi:

1. **Pill bị lệch, không bao đúng quanh chữ.**
2. Pill chưa chạy theo đúng **word timing** như bản HTML demo.

Behavior mong muốn phải giống HTML:

```text
[ THIS ] is very important
     ↓ theo word timing
this [ IS ] very important
          ↓
this is [ VERY ] important
                   ↓
this is very [ IMPORTANT ]
```

Có **1 shared pill duy nhất**.

Pill phải:

- bao đúng word đang active;
- width thay đổi theo độ dài thật của word;
- position đúng theo layout của cả câu;
- di chuyển/rescale mượt giữa các word;
- active word được xác định từ `start_ms/end_ms`;
- không làm text reflow;
- không dùng ASS approximation.

---

# 1. Nguyên nhân lỗi hiện tại cần tránh

## Không dùng `textbbox()` sai cách

Pillow `textbbox()` trả về glyph/ink bounds có thể có offset do:

- baseline;
- ascender;
- descender;
- stroke;
- glyph overhang.

Ví dụ:

```python
bbox = draw.textbbox((0, 0), "Hello", font=font)
```

không có nghĩa:

```text
bbox[0] == vị trí x thực tế trên canvas
bbox[1] == vị trí y thực tế trên canvas
```

Nếu sau đó lấy:

```python
pill_x = word_x + bbox[0]
pill_y = word_y + bbox[1]
```

nhưng text lại được draw bằng anchor/baseline khác, Pill sẽ bị lệch.

---

# 2. Quy tắc quan trọng nhất

## Pill KHÔNG bao theo "ink bbox" của glyph

Pill phải bao theo **word layout box**, giống HTML inline element.

Tức là:

```text
word layout box
┌───────────────┐
│   IMPORTANT   │
└───────────────┘
```

không phải bbox sát từng pixel glyph:

```text
  IMPORTANT
  ↑       ↑
ink bounds
```

HTML Pill nhìn đẹp vì background bao một element box có:

- advance width của word;
- line-height cố định;
- padding x/y.

Python cần mô phỏng đúng cách này.

---

# 3. WordLayout phải lưu layout box

Dùng model:

```python
from dataclasses import dataclass


@dataclass
class WordLayout:
    index: int
    text: str

    # layout position inside subtitle surface
    x: float
    y: float

    # layout box, KHÔNG phải glyph ink bbox
    width: float
    height: float

    line_index: int

    # optional
    baseline_y: float | None = None
```

Pill sẽ lấy trực tiếp:

```python
word.x
word.y
word.width
word.height
```

Không được mỗi frame tự gọi `textbbox()` để tính lại Pill.

---

# 4. X coordinate — tính theo full-line layout

Ví dụ:

```text
Design for human attention
```

Không layout từng word độc lập rồi cộng:

```python
width("Design") + width(" ")
```

vì có thể lệch do kerning/shaping.

Phải tính vị trí theo prefix của cả line.

Ví dụ:

```python
prefix = "Design "
x_for = line_x + draw.textlength(prefix, font=font)
```

Nhưng để width của word cũng đúng theo context, ưu tiên:

```python
prefix_before = "Design "
prefix_after = "Design for"

start_advance = draw.textlength(
    prefix_before,
    font=font,
)

end_advance = draw.textlength(
    prefix_after,
    font=font,
)

word_x = line_x + start_advance
word_width = end_advance - start_advance
```

Với word đầu:

```python
prefix_before = ""
prefix_after = "Design"
```

Tương tự cho tất cả words.

---

# 5. Khoảng trắng giữa words

Nếu tokenization đang giữ word không có space:

```python
["Design", "for", "human", "attention"]
```

thì layout line phải tạo prefix từ **original text**, không tự đo từng word rời.

Ví dụ:

```python
line_text = "Design for human attention"
```

Cần biết character range của mỗi word:

```python
WordSpan(
    text="human",
    char_start=11,
    char_end=16,
)
```

Sau đó:

```python
prefix_before = line_text[:char_start]
prefix_after = line_text[:char_end]

x = line_x + draw.textlength(prefix_before, font=font)

width = (
    draw.textlength(prefix_after, font=font)
    - draw.textlength(prefix_before, font=font)
)
```

Đây là cách ưu tiên.

---

# 6. Y coordinate — dùng line box cố định

Không lấy y từ glyph bbox cho từng word.

Mỗi line phải có:

```python
line_y
line_height
```

Ví dụ:

```python
line_height = int(font_size * 1.18)
```

hoặc lấy từ font metrics:

```python
ascent, descent = font.getmetrics()

line_height = ascent + descent
```

Có thể cộng line gap:

```python
line_height = ascent + descent + line_gap
```

Mỗi word cùng line:

```python
word.y = line_y
word.height = line_height
```

Như HTML:

```text
word box có cùng chiều cao trên một dòng.
```

Đây là điểm quan trọng để Pill không nhảy lên/xuống theo chữ như:

```text
AI
good
gyp
```

do descender khác nhau.

---

# 7. Text drawing phải dùng cùng anchor

Chọn một anchor duy nhất và dùng xuyên suốt.

Ưu tiên đơn giản:

```python
anchor="lt"
```

Ví dụ:

```python
draw.text(
    (line_x, line_y),
    line_text,
    font=font,
    anchor="lt",
    ...
)
```

Mọi computation phải coi:

```text
line_x, line_y = top-left của line layout box
```

Không mix:

```text
text measure theo top-left
nhưng render theo baseline
```

hoặc ngược lại.

---

# 8. Stroke phải được tính nhất quán

Nếu subtitle có:

```python
stroke_width = 4
```

thì text rendering có stroke.

Nhưng Pill layout box không cần bám sát stroke pixel-by-pixel.

Có thể cộng một khoảng an toàn:

```python
visual_pad = max(1, stroke_width * 0.35)
```

Pill:

```python
pill_x = word.x - padding_x - visual_pad
pill_y = word.y - padding_y - visual_pad

pill_width = (
    word.width
    + padding_x * 2
    + visual_pad * 2
)

pill_height = (
    word.height
    + padding_y * 2
    + visual_pad * 2
)
```

Không lấy `textbbox(... stroke_width=...)` làm Pill box chính.

---

# 9. Vertical alignment của text trong Pill

Nếu dùng line box cao hơn glyph thật, text phải được draw ở đúng line position.

Pill nằm quanh `line box + padding`.

Ví dụ:

```text
┌──────────────────┐
│   IMPORTANT      │
└──────────────────┘
```

Không chỉnh `word_y` khác nhau theo từng glyph.

Nếu cần fine tune visual:

```python
pill_vertical_offset = config.pill_vertical_offset
```

mặc định:

```python
0
```

Chỉ dùng offset nhỏ nếu font cụ thể cần.

Không hard-code offset theo từng word.

---

# 10. Word timing behavior — phải giống HTML

Mỗi word:

```python
SubtitleWord(
    text="human",
    start_ms=1200,
    end_ms=1550,
)
```

Active word:

```python
word.start_ms <= time_ms < word.end_ms
```

Ví dụ:

```text
Design      0–400 ms
for       400–650 ms
human     650–1100 ms
attention 1100–1700 ms
```

Behavior:

```text
0–399ms
[ DESIGN ] for human attention

400–649ms
Design [ FOR ] human attention

650–1099ms
Design for [ HUMAN ] attention

1100–1699ms
Design for human [ ATTENTION ]
```

Đây là nguồn sự thật.

Không tự chia đều duration theo số word nếu đã có word timing thật.

---

# 11. Shared Pill — giống HTML

Chỉ có:

```text
1 shared pill
```

Không render:

```text
word1 background
word2 background
word3 background
word4 background
```

rồi toggle visibility.

Thay vào đó:

```python
pill_rect = interpolate(
    previous_word_rect,
    current_word_rect,
    progress,
)
```

---

# 12. Target rect phải là word layout box

Function:

```python
def word_to_pill_rect(
    word: WordLayout,
    config: PillAnimationConfig,
) -> Rect:

    return Rect(
        x=word.x - config.padding_x,
        y=word.y - config.padding_y,
        width=word.width + config.padding_x * 2,
        height=word.height + config.padding_y * 2,
    )
```

Nếu có visual pad/stroke thì cộng nhất quán tại đây.

Không đo lại glyph tại function này.

---

# 13. Tween giống CSS

Khi word mới bắt đầu:

```python
current_index = active_word_index
previous_index = current_index - 1
```

Nếu cùng line:

```python
current_word.line_index == previous_word.line_index
```

thì tween:

```python
transition_progress = (
    time_ms - current_word.start_ms
) / config.transition_ms
```

Clamp:

```python
transition_progress = max(
    0.0,
    min(1.0, transition_progress)
)
```

Easing:

```python
def ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3
```

Sau đó:

```python
eased = ease_out_cubic(transition_progress)

pill.x = lerp(previous_rect.x, current_rect.x, eased)
pill.y = lerp(previous_rect.y, current_rect.y, eased)

pill.width = lerp(
    previous_rect.width,
    current_rect.width,
    eased,
)

pill.height = lerp(
    previous_rect.height,
    current_rect.height,
    eased,
)
```

---

# 14. Transition duration phải tôn trọng word duration

Không để:

```text
word chỉ dài 120ms
nhưng transition Pill dài 260ms
```

Dùng effective duration:

```python
word_duration_ms = (
    current_word.end_ms
    - current_word.start_ms
)

effective_transition_ms = min(
    config.transition_ms,
    max(60, word_duration_ms * 0.55),
)
```

Ví dụ:

```text
word duration = 500ms
transition ≈ 260ms

word duration = 180ms
transition ≈ 99ms
```

Như vậy Pill bám timing tốt hơn.

---

# 15. Nếu timing words có khoảng gap

Ví dụ:

```text
word A end = 1000ms
word B start = 1120ms
```

Trong gap:

```text
1000–1119ms
```

Mặc định:

```text
giữ Pill ở word A
```

để tránh blink.

Khi word B bắt đầu:

```text
tween A → B
```

Không hide/show liên tục giữa các gap nhỏ.

Có thể config:

```python
hold_last_word_during_gap = True
```

---

# 16. Word đầu tiên

Word đầu không có previous target.

Behavior:

```text
pill xuất hiện ngay đúng word box
```

hoặc fade/scale rất nhẹ.

Ưu tiên MVP:

```python
pill_rect = first_word_rect
```

Không tween từ `(0, 0)`.

---

# 17. Đổi line

Nếu:

```python
previous.line_index != current.line_index
```

KHÔNG:

```text
lerp x/y từ cuối dòng 1 xuống đầu dòng 2
```

MVP behavior:

```python
pill_rect = current_rect
```

Có thể fade 60–100ms nếu muốn polish.

Nhưng ưu tiên đúng position trước.

---

# 18. Multi-line layout

Phải layout theo line trước.

Ví dụ:

```text
This subtitle is long
enough to wrap nicely
```

Mỗi line:

```python
LineLayout(
    text=...,
    x=...,
    y=...,
    width=...,
    height=...,
)
```

Words trong line lấy:

```text
x từ prefix trong line đó
y = line.y
height = line.height
```

Không đo prefix xuyên qua newline.

---

# 19. Center alignment

Nếu subtitle center:

```python
line_x = (
    surface_width
    - line_width
) / 2
```

Mỗi word x phải dựa trên đúng `line_x`.

Không center cả phrase một lần rồi dùng chung nếu mỗi line width khác nhau.

Ví dụ:

```text
     This is long
       second
```

line 1 và line 2 phải center độc lập.

---

# 20. Pill radius

Đúng kiểu Pill:

```python
radius = pill_rect.height / 2
```

hoặc:

```python
radius = min(
    config.radius,
    pill_rect.height / 2,
)
```

Nếu muốn đúng capsule HTML:

```python
radius_mode = "pill"
```

mặc định nên dùng:

```text
pill
```

---

# 21. Rendering order

Tại mỗi frame:

```text
1. transparent surface
2. calculate active clip
3. get cached SubtitleLayout
4. calculate current Pill rect
5. draw Pill
6. draw full phrase/inactive text
7. redraw active word with active_text_color
```

Pill luôn draw trước text.

---

# 22. Draw full line, không draw từng word nếu không cần

Để text layout chính xác nhất:

```python
draw.text(
    (line.x, line.y),
    line.text,
    ...
)
```

render cả line một lần.

Không render từng word riêng để tạo câu vì dễ phát sinh spacing khác.

Sau đó chỉ redraw active word lên trên nếu cần đổi màu.

---

# 23. Redraw active word đúng vị trí

Active word phải dùng đúng position từ `WordLayout`.

Ví dụ:

```python
draw.text(
    (word.x, word.y),
    word.text,
    font=font,
    anchor="lt",
    fill=active_text_color,
    ...
)
```

Nếu active word redraw bị lệch do kerning/context, có 2 hướng:

### Preferred
Render line thành mask/token spans từ layout engine và composite active color theo word region.

### MVP
Dùng exact `word.x` từ prefix measurement và cùng `anchor="lt"`.

Không tự center active word trong Pill.

---

# 24. Nếu cần chính xác hơn nữa: text mask

Nếu redraw từng word vẫn có sai lệch font shaping, tạo text mask của **full line** một lần.

Ví dụ:

```text
full line alpha mask
```

Sau đó Pill active text color được composite chỉ trong active word layout region.

Như vậy:

```text
glyph positions 100% giống full-line render
```

MVP có thể chưa cần nếu prefix layout đã đúng.

---

# 25. Auto contrast

Giữ:

```python
active_text_color = "auto"
```

Ví dụ:

```text
#FFD84D → #111111
#2563EB → #FFFFFF
```

Không liên quan đến geometry.

Fix geometry trước rồi mới style.

---

# 26. Debug mode bắt buộc

Thêm debug mode để tìm lỗi lệch.

Config:

```python
debug_layout = False
```

Khi `True`, render:

### Word layout box
outline đỏ:

```text
RED = word layout box
```

### Pill rect
outline xanh:

```text
GREEN = Pill rect
```

### Line box
outline xanh dương:

```text
BLUE = line box
```

### Anchor / baseline
có thể vẽ small point/cross.

Mục tiêu khi debug:

```text
Pill rect phải nằm chính xác quanh WordLayout box.
```

Nếu RED đúng nhưng GREEN sai:
→ lỗi Pill geometry.

Nếu RED đã lệch chữ:
→ lỗi text layout / anchor.

---

# 27. Test bắt buộc

## Test A — width

Text:

```text
I WWW iii IMPORTANT
```

Pill width phải thay đổi rõ ràng.

---

## Test B — vertical alignment

Text:

```text
AI gyp HELLO
```

Pill y/height không được nhảy theo descender `gyp`.

---

## Test C — tiếng Việt

```text
Điều này thực sự quan trọng
```

Pill phải bao đúng:

```text
[ thực sự ]
```

và dấu tiếng Việt không bị clip.

---

## Test D — word timing

Timing:

```text
Điều      0–300
này     300–550
thực    550–800
sự      800–950
quan    950–1200
trọng  1200–1600
```

Screenshot/render frame tại:

```text
100ms
400ms
700ms
900ms
1100ms
1400ms
```

Pill phải nằm đúng word tương ứng.

---

# 28. Definition of Done

Feature chỉ được coi hoàn thành khi:

- [ ] Pill bao quanh đúng word.
- [ ] Không lệch X.
- [ ] Không lệch Y.
- [ ] Width Pill đúng độ dài word.
- [ ] Height Pill ổn định trên cùng line.
- [ ] Pill dùng word timing thật.
- [ ] Pill giữ đúng word trong toàn bộ timing interval.
- [ ] Pill tween mượt khi chuyển sang word tiếp theo.
- [ ] Tween duration tự giới hạn theo word duration.
- [ ] Pill không teleport giữa word cùng dòng.
- [ ] Pill không tween chéo giữa 2 dòng.
- [ ] Text không reflow.
- [ ] Tiếng Việt không bị clip.
- [ ] Pill không phụ thuộc glyph ink bbox.
- [ ] Có debug layout boxes.
- [ ] Không tạo PNG từng frame.
- [ ] Layout được cache.

---

# 29. Kiến trúc cuối cùng mong muốn

```text
SubtitleClip
    ↓
WordTiming[]
    ↓
TextLayoutEngine
    ↓
LineLayout[]
    ↓
WordLayout[]
    ↓
PillAnimation(time_ms)
    ↓
shared Pill Rect
    ↓
Pillow RGBA renderer
    ↓
FFmpeg
```

---

# 30. Quy tắc cốt lõi

Hãy nhớ:

> Text được layout trước. Pill chỉ follow layout.

Không làm:

```text
Pill tự đo text
→ rồi đoán vị trí.
```

Phải làm:

```text
Text layout
→ WordLayout chính xác
→ Pill lấy trực tiếp WordLayout
→ tween theo word timing.
```

Đây là cách để Python Pill hoạt động giống bản HTML/CSS.
