# Highlight Animation (Word Highlight Subtitle)

## 1. Highlight Animation là gì?
**Highlight Animation** (chế độ Word Highlight / Phụ đề phong cách TikTok/Shorts) là hiệu ứng phụ đề tự động đổi màu từng từ (**active word**) theo thời gian thực (word timing) khi thoại trong video đang phát, giúp người xem tập trung và dễ theo dõi nội dung.

---

## 2. So sánh Highlight Animation vs Normal Animation

| Tiêu chí | Normal Mode | Highlight Animation |
| :--- | :--- | :--- |
| **Cách hiển thị** | Toàn bộ câu hiển thị đồng nhất 1 màu cố định (ví dụ: màu trắng). | Từ đang nói đổi sang màu nổi bật (ví dụ: màu vàng), các từ còn lại giữ màu mặc định. |
| **Đồng bộ thời gian** | Theo khoảng thời gian chung của cả dòng phụ đề (Start MS - End MS). | Đồng bộ chi tiết theo thời điểm phát của từng từ (Word-level timing). |
| **Ứng dụng** | Phim ảnh, tài liệu, video bài giảng truyền thống. | Video ngắn (TikTok, Reels, Youtube Shorts), vlogging, marketing. |

---

## 3. Nguyên lý hoạt động kỹ thuật (Ngắn gọn)
1. **Gộp cụm từ (Grouping):** Chia dòng phụ đề dài thành từng cụm ngắn (thường 2–5 từ) để vừa mắt người xem.
2. **Cố định vị trí khung chữ (Layout Stability):** Giữ nguyên cả cụm từ trên màn hình để tránh hiện tượng nhảy chữ (text reflow) hay giật khung hình.
3. **Chuyển màu từ đang đọc (Dynamic Color Swapping):** Chỉ thay đổi mã màu inline (thẻ màu `\1c` trong ASS) tại đúng từ đang phát tương ứng với timeline.
