# MVP2 — Subtitle Timeline Editor

## 1. Mục tiêu

MVP2 tập trung biến MVP1 từ một công cụ:

```text
Import Video + Import SRT + Style + Export
```

thành một **subtitle editor cơ bản có timeline và preview realtime**.

Mục tiêu chính:

- Import video.
- Import SRT.
- Hiển thị subtitle trên timeline.
- Kéo subtitle để chỉnh thời điểm xuất hiện.
- Resize subtitle để chỉnh thời lượng.
- Sửa nội dung subtitle trực tiếp.
- Thêm subtitle thủ công tại vị trí playhead.
- Preview video + subtitle realtime.
- Chỉnh style subtitle.
- Export MP4.

Không mở rộng thành full video editor.

---

## 2. Nguyên tắc MVP2

### 2.1 SRT chỉ là dữ liệu đầu vào

Sau khi import:

```text
SRT
 ↓
SubtitleClip[]
 ↓
Editor
```

Editor làm việc với `SubtitleClip[]`, không chỉnh trực tiếp file SRT.

---

### 2.2 Timeline là nơi chỉnh timing

Không cần nhập `start` / `end` khi tạo subtitle.

Người dùng chỉnh timing bằng:

- kéo cả subtitle clip;
- kéo mép trái;
- kéo mép phải.

```text
        kéo clip
           ↔

     ◀ resize        resize ▶
        ┌────────────────┐
        │ Subtitle text  │
        └────────────────┘
```

---

### 2.3 Preview và Export dùng cùng dữ liệu

```text
                 SubtitleClip[]
                       │
          ┌────────────┴────────────┐
          ↓                         ↓
   Realtime Preview              Export
                              ASS → FFmpeg
```

Không tạo một bộ timing riêng cho preview và một bộ timing riêng cho export.

---

# 3. Layout chính

MVP2 chỉ cần **một màn editor chính**.

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│ Subtitle Video Editor                                  [Import SRT] [Export MP4] │
├───────────────────────────────────────────────┬──────────────────────────────────┤
│                                               │ SUBTITLE                         │
│                                               │                                  │
│                                               │ [ + Add Subtitle ]               │
│                                               │                                  │
│                                               │ Text                             │
│                                               │ ┌──────────────────────────────┐ │
│                 VIDEO PREVIEW                 │ │ AI đang thay đổi            │ │
│                                               │ │ cách chúng ta lập trình     │ │
│                                               │ └──────────────────────────────┘ │
│                                               │                                  │
│              AI đang thay đổi                 │ ──────────────────────────────── │
│           cách chúng ta lập trình             │                                  │
│                                               │ STYLE                            │
│                                               │                                  │
│                                               │ ○ Normal                         │
│                                               │ ● Word Highlight                 │
│                                               │                                  │
│                                               │ Font       [Montserrat       ▼] │
│                                               │ Size       [48]                  │
│                                               │ Text       [#FFFFFF]             │
│                                               │ Highlight  [#FFD900]             │
│                                               │ Stroke     [4]                   │
│                                               │ Position   [Bottom           ▼] │
│                                               │                                  │
│                                               │                    [Delete]      │
├───────────────────────────────────────────────┴──────────────────────────────────┤
│ ▶  00:12.20 / 00:40.00                                      Zoom  [-] 100% [+] │
│                                                                                  │
│      00:00          00:05          00:10          00:15          00:20           │
│        │              │              │              │              │             │
│                                       ▼                                          │
│ VIDEO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                       │                                          │
│ SUB   ┌──────────────┐   ┌────────────┴─────┐   ┌────────────────────┐           │
│       │ AI đang...   │   │ cách chúng ta... │   │ lập trình...       │           │
│       └──────────────┘   └──────────────────┘   └────────────────────┘           │
│                                                                                  │
│                               [+ Add Subtitle]                                   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

# 4. Các khu vực chính

## 4.1 Video Preview

Dùng HTML `<video>` để phát video realtime.

Subtitle được render thành overlay trên video.

```text
┌───────────────────────────────┐
│                               │
│           VIDEO               │
│                               │
│       AI đang thay đổi        │
│    cách chúng ta lập trình    │
│                               │
└───────────────────────────────┘
```

Preview không chạy FFmpeg mỗi lần người dùng chỉnh subtitle.

---

## 4.2 Inspector

Inspector chỉ chứa các thuộc tính cần thiết.

### Khi chưa chọn subtitle

Hiển thị style chung:

```text
STYLE

○ Normal
● Word Highlight

Font
Size
Text Color
Highlight Color
Stroke
Position
```

### Khi chọn subtitle

Hiển thị:

```text
SUBTITLE

Text
┌────────────────────────────┐
│ AI đang thay đổi          │
│ cách chúng ta lập trình   │
└────────────────────────────┘

STYLE

○ Normal
● Word Highlight

Font
Size
Text Color
Highlight Color
Stroke
Position

[Delete]
```

Không cần input `Start` / `End`.

Timing được chỉnh trực tiếp trên timeline.

---

# 5. Timeline

Timeline là phần quan trọng nhất của MVP2.

```text
00:00        00:05        00:10        00:15
  │            │            │            │
                            ▼
VIDEO ━━━━━━━━━━━━━━━━━━━━━━│━━━━━━━━━━━━━━━━━━
                            │
SUB     ┌────────────┐      │ ┌───────────────┐
        │ Subtitle 1 │      │ │ Subtitle 2    │
        └────────────┘      │ └───────────────┘
```

## Timeline cần hỗ trợ

- Playhead.
- Click timeline để seek video.
- Play / Pause.
- Drag subtitle clip.
- Resize bên trái.
- Resize bên phải.
- Select subtitle.
- Zoom timeline.

---

# 6. Chỉnh timing subtitle

## 6.1 Kéo subtitle

```text
BEFORE

┌─────────────────┐
│ AI đang thay đổi│
└─────────────────┘


DRAG →

          ┌─────────────────┐
          │ AI đang thay đổi│
          └─────────────────┘
```

Thay đổi cả `startMs` và `endMs`.

---

## 6.2 Resize mép trái

```text
      ◀
      ┌──────────────────────┐
      │ Subtitle             │
      └──────────────────────┘
```

Thay đổi `startMs`.

---

## 6.3 Resize mép phải

```text
┌──────────────────────┐
│ Subtitle             │
└──────────────────────┘
                       ▶
```

Thay đổi `endMs`.

---

# 7. Sửa nội dung subtitle

Có 2 cách.

## Cách 1 — sửa trên Inspector

Click subtitle clip:

```text
┌───────────────────┐
│ AI đang thay đổi  │
└───────────────────┘
```

Inspector:

```text
Text

┌────────────────────────────┐
│ AI đang thay đổi          │
└────────────────────────────┘
```

Nhập text mới và preview cập nhật ngay.

---

## Cách 2 — sửa trực tiếp trên Preview

Double click subtitle trên video:

```text
AI đang thay đổi
```

chuyển sang trạng thái editable.

Sau khi Enter hoặc click ra ngoài thì lưu lại.

Đây là tính năng nên có nếu triển khai không quá phức tạp.

---

# 8. Add Subtitle

Khi người dùng click:

```text
+ Add Subtitle
```

subtitle mới được tạo tại vị trí playhead.

Ví dụ:

```text
Playhead = 12.4s
```

Editor tự tạo:

```text
start = 12.4s
end   = 14.4s
```

Duration mặc định có thể là `2 giây`.

Timeline:

```text
                  ▼ Playhead

──────────────────│────────────────────

                  ┌───────────────┐
                  │ New subtitle  │
                  └───────────────┘
```

Sau đó:

- người dùng sửa text;
- kéo clip để đổi vị trí;
- resize để đổi duration.

Không cần modal tạo subtitle.

Không cần nhập Start / End.

---

# 9. Realtime Preview

Flow:

```text
Video currentTime
       ↓
Tìm subtitle đang active
       ↓
Render subtitle overlay
       ↓
Preview
```

Ví dụ:

```text
currentTime = 12.3s

Subtitle A
10.0 → 11.5

Subtitle B
11.5 → 13.5

Subtitle C
13.5 → 15.0
```

Editor render `Subtitle B`.

---

# 10. Word Highlight

MVP2 vẫn giữ 2 style:

```text
Normal
Word Highlight
```

Word Highlight tiếp tục sử dụng timing được sinh từ subtitle duration.

```text
Subtitle
10.0 ───────────────────── 13.0

AI    đang    thay    đổi    cách...
```

MVP2 chưa cần làm Word Timing Editor riêng.

Việc chỉnh timing từng từ có thể để sang phiên bản sau.

---

# 11. Data Model

```ts
interface SubtitleClip {
  id: string;

  text: string;

  startMs: number;
  endMs: number;

  style?: SubtitleStyle;
}
```

```ts
interface SubtitleStyle {
  type: 'normal' | 'word-highlight';

  fontFamily: string;
  fontSize: number;

  textColor: string;
  highlightColor: string;

  strokeWidth: number;

  position: 'top' | 'center' | 'bottom';
}
```

Project:

```ts
interface EditorProject {
  videoPath: string;

  subtitles: SubtitleClip[];

  currentTimeMs: number;

  selectedSubtitleId?: string;
}
```

---

# 12. Single Source of Truth

Toàn bộ editor dùng chung:

```text
SubtitleClip[]
```

```text
                    SubtitleClip[]
                          │
          ┌───────────────┼───────────────┐
          ↓               ↓               ↓
      Timeline         Preview         Inspector
          │               │               │
          └───────────────┼───────────────┘
                          ↓
                     ASS Builder
                          ↓
                       FFmpeg
                          ↓
                         MP4
```

Không lưu timing ở nhiều nơi khác nhau.

---

# 13. Flow MVP2

```text
Import Video
     ↓
Main Editor
     ↓
Import SRT
     ↓
SubtitleClip[]
     ↓
Timeline
     ↓
┌─────────────────────────────┐
│ Drag / Resize / Edit Text   │
│ Add Subtitle / Delete       │
│ Change Style                │
└─────────────────────────────┘
     ↓
Realtime Preview
     ↓
Export MP4
```

---

# 14. Các trạng thái UI cần thiết

Không cần nhiều màn riêng.

Chỉ cần một editor với các trạng thái sau.

## State 1 — Chưa có video

```text
┌─────────────────────────────┐
│                             │
│       Drop video here       │
│                             │
│     hoặc click chọn file    │
│                             │
└─────────────────────────────┘
```

---

## State 2 — Có video, chưa có subtitle

```text
VIDEO PREVIEW


TIMELINE

VIDEO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUB

             [+ Add Subtitle]
```

---

## State 3 — Có subtitle

```text
VIDEO PREVIEW

AI đang thay đổi


TIMELINE

SUB
┌────────────┐ ┌──────────────┐ ┌──────────────┐
│ AI đang... │ │ thay đổi...  │ │ lập trình... │
└────────────┘ └──────────────┘ └──────────────┘
```

---

## State 4 — Subtitle đang được chọn

```text
TIMELINE

      SELECTED
         ↓

┌─────────────────────┐
│ AI đang thay đổi    │
└─────────────────────┘
```

Inspector hiển thị text + style của subtitle đang chọn.

---

# 15. Scope MVP2

## Bắt buộc

- [x] Import video.
- [x] Video preview realtime.
- [x] Import SRT.
- [x] Parse SRT thành subtitle clips.
- [x] Subtitle timeline.
- [x] Playhead.
- [x] Seek video từ timeline.
- [x] Play / Pause.
- [x] Select subtitle.
- [x] Drag subtitle.
- [x] Resize subtitle.
- [x] Add subtitle tại playhead.
- [x] Edit subtitle text.
- [x] Delete subtitle.
- [x] Timeline zoom.
- [x] Normal style.
- [x] Word Highlight style.
- [x] Font.
- [x] Font size.
- [x] Text color.
- [x] Highlight color.
- [x] Stroke.
- [x] Position.
- [x] Realtime style preview.
- [x] Export MP4.

---

# 16. Không làm trong MVP2

Để MVP2 đơn giản, chưa làm:

- Paste Subtitle.
- Modal nhập Start / End.
- Word Timing Editor.
- Audio waveform.
- Speech-to-text.
- Auto sync subtitle.
- Multiple subtitle tracks.
- Multiple video tracks.
- Image / sticker / B-roll.
- Transition.
- Music editor.
- Keyframe animation.
- Full video editor features.

---

# 17. Hướng phát triển sau MVP2

Sau khi timeline editor ổn định:

```text
MVP2
Timeline Subtitle Editor
       ↓
MVP2.1
Waveform + Keyboard Shortcuts
       ↓
MVP2.2
Speech-to-text + Word Timestamp
       ↓
MVP3
Animation Presets
```

Điểm quan trọng nhất của MVP2 là:

> Subtitle phải trở thành một object có thể chỉnh trực tiếp trên timeline, thay vì chỉ là dữ liệu được import từ SRT rồi đem đi export.
