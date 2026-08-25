# Subtitle Animation Presets — 6 Style Core

Tài liệu mô tả 6 style animation subtitle ưu tiên triển khai:

1. Highlight
2. Soft Pop
3. Punch
4. Rise
5. Marker
6. Pill

Mục tiêu chung:

- Phù hợp TikTok / Reels / YouTube Shorts.
- Animation gọn, hiện đại, không quá “template”.
- Ưu tiên readability.
- Không làm subtitle nhảy layout.
- Có thể preview realtime trong editor.
- Có thể mở rộng sang word-level timing sau này.

---

# 1. Highlight

## Mô tả

Highlight là style cơ bản nhất cho subtitle dạng short-form.

Toàn bộ câu subtitle được giữ nguyên vị trí trên màn hình.

Khi audio đang đọc đến từ nào, từ đó đổi sang màu highlight.

Ví dụ:

```text
Build something PEOPLE love
                ↑
             active word
```

Trong đó:

- từ chưa active: màu trắng;
- từ đang active: màu vàng hoặc màu highlight do người dùng chọn;
- layout không thay đổi;
- kích thước chữ không đổi.

---

## Animation

Không cần animation position hoặc scale.

Chỉ transition màu:

```text
Normal word
color: #FFFFFF

Active word
color: #FFD84D
```

Timing gợi ý:

```text
color transition: 120–180ms
```

Ví dụ CSS:

```css
.word {
  transition: color 160ms ease;
}

.word.active {
  color: #FFD84D;
}
```

---

## Ưu điểm

- Dễ đọc.
- Không gây mất tập trung.
- Phù hợp gần như mọi loại video.
- Dễ triển khai.
- Là nền tảng cho word-level subtitle.

---

## Phù hợp

- Talking head.
- Podcast.
- Tutorial.
- Education.
- Review.
- Video giải thích.

---

# 2. Soft Pop

## Mô tả

Soft Pop animate toàn bộ subtitle phrase khi phrase mới xuất hiện.

Khác với hiệu ứng bounce mạnh, Soft Pop chỉ scale nhẹ.

Flow:

```text
0.92
 ↓
1.04
 ↓
1.00
```

Kèm opacity:

```text
0 → 1
```

Ví dụ:

```text
THIS CHANGES EVERYTHING
```

Khi subtitle xuất hiện, cả cụm pop nhẹ về phía người xem.

---

## Animation

Gợi ý:

```text
Start:
scale: 0.92
opacity: 0

Overshoot:
scale: 1.04
opacity: 1

End:
scale: 1.00
opacity: 1
```

Timing:

```text
150–220ms
```

Easing phù hợp:

```text
cubic-bezier(.2, .8, .2, 1)
```

---

## Lưu ý

Không nên dùng:

```text
0.5 → 1.5 → 0.7 → 1.3 → 1
```

vì nhìn quá mạnh và giống template animation phổ thông.

Soft Pop chỉ nên có một overshoot nhỏ.

---

## Ưu điểm

- Hiện đại.
- Dễ dùng.
- Có cảm giác dynamic nhưng vẫn sạch.
- Không phụ thuộc word timing.

---

## Phù hợp

- Talking head.
- Review.
- TikTok.
- Reels.
- Shorts.
- Hook ngắn.

---

# 3. Punch

## Mô tả

Punch giữ nguyên toàn bộ phrase.

Chỉ từ đang được đọc mới scale lên nhẹ rồi trở lại bình thường.

Ví dụ:

```text
This is REALLY important
        ↑
      active
```

Animation của từ `REALLY`:

```text
1.00
 ↓
1.12
 ↓
1.00
```

Các từ khác đứng yên.

---

## Animation

Gợi ý:

```text
Start:
scale: 1

Peak:
scale: 1.10–1.14

End:
scale: 1
```

Timing:

```text
120–220ms
```

Có thể thêm:

```text
font-weight: tăng nhẹ
color: highlight nhẹ
```

nhưng không bắt buộc.

---

## Nguyên tắc quan trọng

Khi active word scale:

```text
KHÔNG được làm reflow layout
```

Tức là:

- từ bên cạnh không dịch chuyển;
- dòng subtitle không đổi chiều rộng;
- vị trí phrase không bị nhảy.

Nên dùng:

```css
display: inline-block;
transform: scale(...);
```

thay vì thay đổi font-size.

---

## Ưu điểm

- Nhấn mạnh lời nói rất tốt.
- Trông energetic hơn Highlight.
- Vẫn giữ được readability.
- Hợp content tốc độ nhanh.

---

## Phù hợp

- Education.
- Storytelling.
- Sales.
- Motivation.
- Fast talking.
- Hook.

---

# 4. Rise

## Mô tả

Rise animate cả phrase từ phía dưới đi lên khi subtitle mới xuất hiện.

Không bounce.

Không spring mạnh.

Ví dụ:

```text
Before:

          [empty]


Enter:

        Keep it simple
              ↑
        đi từ dưới lên
```

---

## Animation

Gợi ý:

```text
Start:
translateY: 12–18px
opacity: 0

End:
translateY: 0
opacity: 1
```

Có thể thêm blur rất nhẹ:

```text
blur: 1–3px → 0
```

Timing:

```text
160–260ms
```

---

## Exit

Có thể dùng:

```text
translateY: 0 → -6px
opacity: 1 → 0
```

Exit nên ngắn hơn entrance.

Ví dụ:

```text
120–180ms
```

---

## Ưu điểm

- Rất clean.
- Không làm người xem mệt.
- Có cảm giác UI/motion design chuyên nghiệp.
- Dễ kết hợp với nhiều font.

---

## Phù hợp

- Lifestyle.
- Podcast.
- Beauty.
- Tech.
- Storytelling.
- Clean aesthetic.

---

# 5. Marker

## Mô tả

Marker giữ nguyên text nhưng active word có một vùng highlight phía sau giống nét bút marker.

Ví dụ:

```text
Make every WORD matter
           ████
            ↑
         active
```

Highlight được animate từ trái sang phải.

---

## Animation

Text:

```text
color: white
```

Khi active:

```text
background highlight:
scaleX: 0 → 1

transform-origin:
left center
```

Sau khi background đã xuất hiện:

```text
text color:
white → dark
```

để tăng contrast.

---

## Timing

Gợi ý:

```text
Marker swipe:
180–350ms
```

Nếu word timing ngắn, animation nên được giới hạn để không chạy chậm hơn lời nói.

Ví dụ:

```text
duration = min(300ms, wordDuration * 0.65)
```

---

## Visual

Marker không cần là rectangle hoàn hảo.

Có thể hỗ trợ:

```text
- Rounded marker
- Hand-drawn marker
- Soft marker
- Sharp marker
```

Nhưng MVP chỉ nên có một kiểu đơn giản.

---

## Ưu điểm

- Rất rõ active word.
- Có personality hơn Highlight.
- Phù hợp education và key point.
- Có thể trở thành visual signature của editor.

---

## Phù hợp

- Tutorial.
- Education.
- Productivity.
- Listicle.
- Explain video.
- Key takeaway.

---

# 6. Pill

## Mô tả

Pill dùng một background bo tròn bao quanh active word.

Điểm quan trọng:

```text
Pill KHÔNG biến mất rồi tạo lại.
```

Nó di chuyển mượt từ active word hiện tại sang word tiếp theo.

Ví dụ:

```text
Design [ FOR ] human attention
```

Sau đó:

```text
Design for [ HUMAN ] attention
```

Background pill tween từ bounding box của `FOR` sang `HUMAN`.

---

## Animation

Cần animate:

```text
x
y
width
height
```

Ví dụ:

```text
Pill A:
x = 120
width = 54

↓

Pill B:
x = 183
width = 92
```

Transition:

```text
250–350ms
```

Easing:

```text
cubic-bezier(.22, .8, .2, 1)
```

---

## Active word

Khi pill nằm phía sau word:

```text
word color:
white → dark
```

Ví dụ:

```text
pill background: #FFD84D
active text: #08090B
```

Inactive word vẫn trắng.

---

## Implementation

Mỗi word cần đo bounding box:

```ts
{
  x,
  y,
  width,
  height
}
```

Khi `activeWordIndex` thay đổi:

```text
current pill bounds
        ↓
target word bounds
        ↓
tween
        ↓
new pill position
```

Không nên tạo một pill riêng cho từng word.

Nên có:

```text
1 shared pill
```

và animate nó di chuyển.

---

## Ưu điểm

- Trông premium hơn highlight đổi màu đơn thuần.
- Motion rất mượt.
- Dễ tạo cảm giác riêng cho sản phẩm.
- Rất phù hợp subtitle short-form hiện đại.

---

## Phù hợp

- Podcast clips.
- Tech.
- Startup.
- Education.
- Modern Reels.
- Premium short-form.

---

# Phân loại 6 Style

## Phrase-level Animation

Không cần word timing chi tiết:

```text
Soft Pop
Rise
```

Cả subtitle phrase được animate khi xuất hiện.

---

## Word-level Animation

Cần biết active word:

```text
Highlight
Punch
Marker
Pill
```

Flow:

```text
word timing
    ↓
activeWordIndex
    ↓
animation preset
    ↓
subtitle renderer
```

---

# Timing Guidelines

Nên giữ animation ngắn và nhẹ.

| Animation | Duration gợi ý |
|---|---:|
| Highlight | 120–180ms |
| Soft Pop | 150–220ms |
| Punch | 120–220ms |
| Rise | 160–260ms |
| Marker | 180–350ms |
| Pill | 250–350ms |

---

# Motion Guidelines

## Position

```text
8–20px
```

Không nên di chuyển subtitle quá xa.

---

## Scale

Thông thường:

```text
0.92–1.14
```

Không nên scale quá lớn.

---

## Blur

Nếu dùng:

```text
1–8px
```

Không nên blur mạnh với subtitle vì làm giảm readability.

---

# Nguyên tắc chung

## Nên

- Giữ layout ổn định.
- Animation bám timing speech.
- Chỉ animate thứ cần thiết.
- Ưu tiên readability.
- Giữ motion ngắn.
- Dùng easing mềm.
- Active word phải nhìn ra ngay.

---

## Không nên

- Bounce liên tục.
- Rotate ngẫu nhiên.
- Scale quá mạnh.
- Animate tất cả từ cùng lúc.
- Làm text reflow khi active word scale.
- Di chuyển subtitle quá xa.
- Dùng animation dài hơn thời gian subtitle xuất hiện.

---

# Suggested Preset Model

Có thể lưu animation preset như sau:

```ts
type SubtitleAnimationType =
  | 'highlight'
  | 'soft-pop'
  | 'punch'
  | 'rise'
  | 'marker'
  | 'pill';
```

Ví dụ:

```ts
interface SubtitleAnimation {
  type: SubtitleAnimationType;

  duration?: number;

  intensity?: number;

  highlightColor?: string;
}
```

---

# Suggested UI

```text
ANIMATION

○ None
● Highlight
○ Soft Pop
○ Punch
○ Rise
○ Marker
○ Pill
```

Có thể hiển thị thumbnail preview nhỏ bên cạnh từng preset.

---

# Recommended Implementation Order

Nên triển khai theo thứ tự:

```text
1. Highlight
2. Soft Pop
3. Rise
4. Punch
5. Marker
6. Pill
```

Lý do:

- Highlight đơn giản nhất.
- Soft Pop / Rise chỉ cần phrase timing.
- Punch thêm word-level transform.
- Marker thêm background animation.
- Pill phức tạp nhất vì phải đo bounding box và tween vị trí + kích thước.

---

# Kết luận

6 animation core:

```text
Highlight
Soft Pop
Punch
Rise
Marker
Pill
```

đủ để tạo bộ subtitle animation ban đầu vừa đa dạng vừa không quá nhiều.

Mục tiêu không phải có thật nhiều preset, mà là:

> Mỗi preset phải có mục đích rõ ràng, motion mượt, dễ đọc và đủ đẹp để dùng thật trong TikTok / Reels / Shorts.


7. Rounded Box / Caption Card

Subtitle nằm trong một khối background bo góc:

╭────────────────────────────────╮
│  tương Lai không phải là AI   │
│     thay thế lập trình viên    │
╰────────────────────────────────╯

Đặc điểm visual:

Background: vàng sáng.
Text: đen.
Border radius lớn.
Text căn giữa.
Có padding quanh text.
Cho phép xuống 2 dòng.
Không cần stroke text.
Box tự co giãn theo nội dung nhưng có max-width.

Gợi ý:

background: #FFD900;
color: #111111;

border-radius: 16px;
padding: 10px 16px;

font-weight: 500–600;
text-align: center;
line-height: 1.1;

max-width: 85%;
Cách hiển thị

Style này không có entrance animation và exit animation.

Subtitle chỉ xuất hiện đúng tại startMs:

currentTime < startMs

[ không hiển thị ]

Đến thời gian subtitle:

currentTime >= startMs
&&
currentTime < endMs

╭────────────────────────────╮
│     Nội dung subtitle      │
╰────────────────────────────╯

Khi hết thời gian:

currentTime >= endMs

[ biến mất ngay ]

Tức là:

Phrase 1
10.0s ─────────── 12.5s

          ↓

10.0s
╭──────────────────────╮
│ Subtitle phrase 1    │
╰──────────────────────╯

12.5s
[ disappear ]

Phrase tiếp theo:

12.5s

╭──────────────────────╮
│ Subtitle phrase 2    │
╰──────────────────────╯

Không có:

❌ fade
❌ scale
❌ slide
❌ bounce
❌ transition giữa 2 phrase

Chỉ:

SHOW → HOLD → HIDE
Khi chuyển giữa các subtitle

Ví dụ:

Subtitle A
0s → 2s

Subtitle B
2s → 4s

Tại 1.99s:

╭──────────────────────╮
│ Subtitle A           │
╰──────────────────────╯

Tại 2.00s:

╭──────────────────────╮
│ Subtitle B           │
╰──────────────────────╯

Box A được thay trực tiếp bằng Box B, không animate quá trình chuyển đổi.

Animation level

Thực tế style này nên coi là:

Animation: None
Display style: Rounded Box
Level: Phrase-level

Tức nó thiên về subtitle visual style hơn là animation.

Nếu đưa vào model của editor thì nên tách:

style: {
  type: 'rounded-box',
  backgroundColor: '#FFD900',
  textColor: '#111111',
  borderRadius: 16,
}

animation: {
  type: 'none'
}