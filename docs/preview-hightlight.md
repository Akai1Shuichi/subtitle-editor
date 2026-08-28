# Prompt redesign Subtitle Animation Preview Card

Hãy redesign **Subtitle Animation Preview Card** hiện tại theo phong cách hiện đại, premium, giống visual của `subtitle_animation_demo.html`.

## Mục tiêu

Card phải trông giống một **mini video preview thực tế** dùng để preview subtitle animation trong TikTok / Reels / Shorts, không giống placeholder UI.

**Không thay đổi logic animation subtitle hiện tại.**
Chỉ chỉnh **layout + visual design + CSS của preview card/stage**.

---

## 1. Kích thước preview

Không để preview quá cao như hiện tại.

Thiết kế card theo dạng landscape:

```text
┌────────────────────────────────────┐
│                                    │
│          VIDEO PREVIEW             │
│                                    │
│       phụ đề miễn phí              │
│                                    │
└────────────────────────────────────┘
```

Gợi ý:

```css
aspect-ratio: 16 / 9;
min-height: 220px;
max-height: 300px;
```

Desktop có thể khoảng:

```text
500–600px width
250–300px height
```

Responsive trên mobile.

---

## 2. Background

Bỏ background đen phẳng hiện tại.

Dùng background dark cinematic với nhiều layer nhẹ:

```css
background:
  linear-gradient(
    rgba(0, 0, 0, 0.18),
    rgba(0, 0, 0, 0.48)
  ),
  radial-gradient(
    circle at 50% 15%,
    rgba(255,255,255,0.10),
    transparent 38%
  ),
  linear-gradient(
    135deg,
    #283342,
    #111821 45%,
    #202834
  );
```

Mục tiêu là tạo cảm giác có chiều sâu như một frame video thật.

Không dùng màu quá sáng.

---

## 3. Bỏ hình tròn lớn phía sau

Hiện tại có một circle rất lớn phía sau card:

```text
      ◯◯◯◯◯
   ◯           ◯
  ◯   CARD      ◯
   ◯           ◯
      ◯◯◯◯◯
```

Hãy **xóa hoàn toàn circle lớn này**.

Nó làm preview giống UI mockup hơn là video.

---

## 4. Thêm subject silhouette nhẹ

Thay circle bằng một subject/person silhouette rất nhẹ ở giữa background để tạo cảm giác đang preview subtitle trên video talking-head.

Ví dụ:

```css
.preview-person {
  position: absolute;

  width: 120px;
  height: 165px;

  top: 35px;
  left: 50%;
  transform: translateX(-50%);

  border-radius: 50% 50% 38% 38%;

  background:
    linear-gradient(
      180deg,
      rgba(255,255,255,.12),
      rgba(255,255,255,.025)
    );

  box-shadow:
    0 20px 60px rgba(0,0,0,.3);
}
```

Thêm phần đầu:

```css
.preview-person::after {
  content: "";

  position: absolute;

  width: 75px;
  height: 75px;

  border-radius: 50%;

  left: 50%;
  transform: translateX(-50%);

  top: -18px;

  background: rgba(255,255,255,.10);
}
```

Silhouette phải **rất subtle**, không được tranh attention với subtitle.

---

## 5. Subtitle position

Không đặt subtitle đúng giữa màn hình như hiện tại.

Đưa subtitle xuống khu vực **lower third**, tương tự subtitle trong video thật:

```css
.subtitle-preview {
  position: absolute;

  left: 24px;
  right: 24px;

  bottom: 28px;

  text-align: center;
}
```

Ví dụ:

```text
┌──────────────────────────────────────┐
│                                      │
│                 ○                    │
│                /|\                   │
│                / \                   │
│                                      │
│                                      │
│          phụ đề miễn phí             │
│                                      │
└──────────────────────────────────────┘
```

---

## 6. Typography subtitle

Subtitle cần có cảm giác TikTok / Shorts hiện đại.

Gợi ý:

```css
font-family:
  Inter,
  ui-sans-serif,
  system-ui,
  sans-serif;

font-size: 30px;

font-weight: 900;

line-height: 1.1;

letter-spacing: -0.03em;
```

Text:

```text
normal word:
#FFFFFF

active word:
#FFD84D
```

Stroke/shadow:

```css
text-shadow:
  0 2px 0 rgba(0,0,0,.95),
  2px 0 0 rgba(0,0,0,.9),
  -2px 0 0 rgba(0,0,0,.9),
  0 -2px 0 rgba(0,0,0,.9),
  0 7px 18px rgba(0,0,0,.4);
```

Không làm stroke quá dày.

---

## 7. Card container

Card ngoài cần premium hơn.

```css
border-radius: 20px;

overflow: hidden;

border:
  1px solid rgba(255,255,255,.08);

background:
  rgba(255,255,255,.02);

box-shadow:
  0 20px 50px rgba(0,0,0,.35);
```

Không dùng border sáng mạnh.

---

## 8. Subtle grid overlay

Có thể thêm cross/grid cực nhẹ để preview có chiều sâu:

```css
.preview-stage::before {
  content: "";

  position: absolute;
  inset: 0;

  background:
    linear-gradient(
      90deg,
      transparent 49.8%,
      rgba(255,255,255,.035) 50%,
      transparent 50.2%
    ),
    linear-gradient(
      transparent 49.8%,
      rgba(255,255,255,.03) 50%,
      transparent 50.2%
    );

  pointer-events: none;
}
```

Grid này phải gần như không nhận ra ngay.

---

## 9. Highlight animation

Giữ nguyên logic animation hiện tại.

Ví dụ:

```text
phụ đề miễn phí
^^^
active word
```

Active word:

```css
color: #FFD84D;
```

Transition:

```css
transition: color 160ms ease;
```

**Không thay đổi timing hoặc logic active word đang có.**

---

## 10. Không làm

Không thêm:

```text
❌ giant circle background
❌ glassmorphism quá mạnh
❌ neon glow
❌ gradient màu mè
❌ border sáng
❌ animation cho background
❌ floating shapes
❌ subtitle nằm chính giữa màn hình
❌ preview cao giống mobile 9:16
```

Preview card này chỉ là **thumbnail/demo animation**, không phải canvas video chính.

---

## Visual target

Kết quả mong muốn gần như:

```text
╭──────────────────────────────────────────╮
│                                          │
│                 ○                        │
│                /|\                       │
│                / \                       │
│                                          │
│                                          │
│                                          │
│          phụ đề miễn phí                 │
│          ^^^^^^                          │
│          highlight                       │
│                                          │
╰──────────────────────────────────────────╯
```

Background:

```text
dark navy / charcoal
+
subtle radial lighting
+
subtle human silhouette
+
slight vignette
```

Subtitle phải là element nổi bật nhất.

---

## Yêu cầu cuối

* Giữ nguyên component hiện tại nếu có thể.
* Giữ nguyên subtitle animation logic.
* Chỉ refactor HTML/CSS cần thiết cho preview.
* Responsive.
* Không thêm dependency mới.
* Không dùng image asset bên ngoài.
* Không tạo ảnh.
* Chỉ dùng HTML/CSS và element hiện tại.
* Nếu project đang dùng Tailwind thì chuyển toàn bộ các style trên sang Tailwind tương ứng.
* Nếu đang dùng SCSS/CSS thì viết clean SCSS/CSS.
* Trả lại code hoàn chỉnh của component sau khi sửa.
