"""
src/json_subtitle_parser.py
────────────────────────────
Parser cho file subtitle.json (word-level timing từ speech recognition).

Format input:
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
  },
  ...
}

Public API
----------
load_from_json(path)  →  (clips: list[SubtitleClip], timing: TimingFile)
    Parse file JSON và trả về cả clips lẫn word timing trong một lần gọi.
    clips  : danh sách SubtitleClip sort theo start_ms, sẵn sàng gán vào project.
    timing : TimingFile với lines sort theo index, key bằng vị trí (0-based).
             Dùng timing.get_line(i) với i = vị trí clip trong sorted_clips().
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from .models import SubtitleClip
from .word_timing import TimingFile, LineTiming


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class JsonSubtitleError(Exception):
    """Base class cho mọi lỗi parse subtitle.json."""


class JsonSubtitleFormatError(JsonSubtitleError):
    """File JSON sai format hoặc thiếu trường bắt buộc."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sec_to_ms(seconds: float) -> int:
    """Chuyển giây (float) sang milliseconds (int), tối thiểu 0."""
    return max(0, round(seconds * 1000))


def _parse_entry(
    entry: dict,
    index: int,
    clip_id: str,
) -> tuple[SubtitleClip, LineTiming]:
    """
    Parse một entry JSON thành (SubtitleClip, LineTiming).

    Parameters
    ----------
    entry    : dict của một entry trong subtitle.json
    index    : vị trí (0-based) trong danh sách đã sort theo `from`
    clip_id  : UUID đã tạo sẵn cho clip này
    """
    start_ms = _sec_to_ms(entry.get("from", 0.0))
    end_ms   = _sec_to_ms(entry.get("to",   0.0))

    # Đảm bảo end_ms > start_ms (tránh clip zero-duration)
    if end_ms <= start_ms:
        end_ms = start_ms + 100   # fallback 100ms

    raw_words: list[dict] = entry.get("words", [])

    # Ghép text từ danh sách words
    text = " ".join(
        w.get("value", "").strip()
        for w in raw_words
        if w.get("value", "").strip()
    )
    if not text:
        text = "(no text)"

    clip = SubtitleClip(
        id=clip_id,
        text=text,
        start_ms=start_ms,
        end_ms=end_ms,
    )

    # Dùng factory method của LineTiming — logic parse words tập trung ở word_timing.py
    line = LineTiming.from_json_words(
        index=index,
        start_ms=start_ms,
        end_ms=end_ms,
        json_words=raw_words,
    )

    return clip, line


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_from_json(
    path: str | Path,
) -> tuple[list[SubtitleClip], TimingFile]:
    """
    Parse file subtitle.json và trả về (clips, timing).

    Parameters
    ----------
    path : đường dẫn đến file subtitle.json

    Returns
    -------
    clips  : list[SubtitleClip] — sort theo start_ms, sẵn sàng gán vào project.clips
    timing : TimingFile — index 0-based khớp với vị trí trong clips.
             Dùng timing.get_line(i) với i = vị trí clip trong project.sorted_clips()

    Raises
    ------
    FileNotFoundError      – file không tồn tại
    JsonSubtitleFormatError – JSON sai format
    JsonSubtitleError       – lỗi khác khi parse
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {path}")

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise JsonSubtitleError(f"Không đọc được file '{path.name}': {exc}") from exc

    try:
        data: dict = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise JsonSubtitleFormatError(
            f"File '{path.name}' không phải JSON hợp lệ: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise JsonSubtitleFormatError(
            f"File '{path.name}' phải là JSON object (dict), "
            f"nhận được {type(data).__name__}."
        )

    # Lấy tất cả entries và sort theo `from` (thời gian bắt đầu)
    entries: list[dict] = []
    for key, value in data.items():
        if not isinstance(value, dict):
            continue
        # Bỏ qua entry không có `from` hoặc `to`
        if "from" not in value or "to" not in value:
            continue
        entries.append(value)

    if not entries:
        raise JsonSubtitleFormatError(
            f"File '{path.name}' không có entry hợp lệ nào "
            "(cần có các object với trường 'from', 'to', 'words')."
        )

    # Sort theo `from` để đảm bảo thứ tự thời gian
    entries.sort(key=lambda e: float(e.get("from", 0)))

    # Parse từng entry
    clips: list[SubtitleClip] = []
    lines: list[LineTiming]   = []

    for index, entry in enumerate(entries):
        clip_id = str(uuid.uuid4())
        try:
            clip, line = _parse_entry(entry, index, clip_id)
        except Exception as exc:
            # Bỏ qua entry lỗi, tiếp tục parse các entry còn lại
            continue

        clips.append(clip)
        lines.append(line)

    if not clips:
        raise JsonSubtitleError(
            f"File '{path.name}' không parse được clip nào hợp lệ."
        )

    timing = TimingFile(
        source_srt=path.name,   # lưu tên file JSON làm source reference
        lines=lines,
        version=1,
    )

    return clips, timing
