"""
word_timing.py
──────────────
Quy định format dữ liệu timing từng từ và logic load/save.

Cấu trúc JSON sidecar (.words.json) lưu cạnh file .srt:

{
  "version": 1,
  "source_srt": "my_video.srt",
  "lines": [
    {
      "index": 0,
      "start_ms": 1000,
      "end_ms": 3000,
      "words": [
        {"word": "AI",      "start_ms": 1000, "end_ms": 1300},
        {"word": "đang",    "start_ms": 1320, "end_ms": 1600},
        {"word": "thay",    "start_ms": 1620, "end_ms": 1900},
        {"word": "đổi",     "start_ms": 1920, "end_ms": 2200},
        {"word": "cách",    "start_ms": 2220, "end_ms": 2500},
        {"word": "chúng",   "start_ms": 2520, "end_ms": 2750},
        {"word": "ta",      "start_ms": 2770, "end_ms": 2900},
        {"word": "lập",     "start_ms": 2920, "end_ms": 3000},
        {"word": "trình",   "start_ms": 3020, "end_ms": 3200}
      ]
    }
  ]
}

Các field tùy chọn (có thể thêm về sau):
  - confidence: float (từ Whisper)
  - speaker:    str   (multi-speaker)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class WordTiming:
    """Timing của một từ đơn."""
    word: str
    start_ms: int       # milliseconds, tính từ đầu video
    end_ms: int         # milliseconds, tính từ đầu video

    def duration_ms(self) -> int:
        return max(0, self.end_ms - self.start_ms)

    def duration_cs(self) -> int:
        """Centiseconds – đơn vị dùng trong ASS karaoke tag \\kf."""
        return max(1, self.duration_ms() // 10)

    def __post_init__(self):
        if self.end_ms < self.start_ms:
            raise ValueError(
                f"WordTiming: end_ms ({self.end_ms}) < start_ms ({self.start_ms}) "
                f"cho từ '{self.word}'"
            )


@dataclass
class LineTiming:
    """Timing của một dòng subtitle, kèm danh sách từng từ."""
    index: int              # vị trí trong file SRT (0-based)
    start_ms: int           # thời điểm bắt đầu dòng
    end_ms: int             # thời điểm kết thúc dòng
    words: list[WordTiming] = field(default_factory=list)

    @property
    def has_word_timing(self) -> bool:
        return len(self.words) > 0

    def duration_ms(self) -> int:
        return max(0, self.end_ms - self.start_ms)


@dataclass
class TimingFile:
    """Container toàn bộ dữ liệu timing, ánh xạ 1-1 với file SRT."""
    source_srt: str
    lines: list[LineTiming] = field(default_factory=list)
    version: int = 1

    def get_line(self, index: int) -> Optional[LineTiming]:
        """Lấy LineTiming theo index SRT (0-based). None nếu chưa có."""
        for ln in self.lines:
            if ln.index == index:
                return ln
        return None

    def has_any_word_timing(self) -> bool:
        return any(ln.has_word_timing for ln in self.lines)


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def save_timing(timing: TimingFile, dest: str | Path) -> Path:
    """
    Lưu TimingFile ra file JSON.
    Thường đặt cạnh file SRT: video.words.json
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "version": timing.version,
        "source_srt": timing.source_srt,
        "lines": [
            {
                "index": ln.index,
                "start_ms": ln.start_ms,
                "end_ms": ln.end_ms,
                "words": [
                    {
                        "word": w.word,
                        "start_ms": w.start_ms,
                        "end_ms": w.end_ms,
                    }
                    for w in ln.words
                ],
            }
            for ln in timing.lines
        ],
    }

    dest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return dest.resolve()


def load_timing(path: str | Path) -> TimingFile:
    """
    Đọc file .words.json và trả về TimingFile.

    Raises
    ------
    FileNotFoundError – file không tồn tại
    ValueError        – JSON sai schema
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy timing file: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"File '{path.name}' không phải JSON hợp lệ: {exc}") from exc

    if data.get("version", 0) != 1:
        raise ValueError(
            f"Timing file version {data.get('version')} không được hỗ trợ. "
            "Chỉ hỗ trợ version 1."
        )

    lines = []
    for raw_line in data.get("lines", []):
        words = [
            WordTiming(
                word=w["word"],
                start_ms=int(w["start_ms"]),
                end_ms=int(w["end_ms"]),
            )
            for w in raw_line.get("words", [])
        ]
        lines.append(
            LineTiming(
                index=int(raw_line["index"]),
                start_ms=int(raw_line["start_ms"]),
                end_ms=int(raw_line["end_ms"]),
                words=words,
            )
        )

    return TimingFile(
        version=data.get("version", 1),
        source_srt=data.get("source_srt", ""),
        lines=lines,
    )


# ---------------------------------------------------------------------------
# Helper: tạo TimingFile stub từ SSAFile (chưa có word timing)
# ---------------------------------------------------------------------------

def timing_from_subs(subs, source_srt_name: str = "") -> TimingFile:
    """
    Tạo TimingFile rỗng (chưa có word timing) từ SSAFile.
    Dùng làm skeleton để người dùng điền timing thủ công.

    Parameters
    ----------
    subs            : pysubs2.SSAFile đã load từ SRT
    source_srt_name : tên file SRT gốc để lưu vào metadata
    """
    lines = []
    for i, event in enumerate(subs.events):
        if not event.text.strip():
            continue
        lines.append(
            LineTiming(
                index=i,
                start_ms=event.start,
                end_ms=event.end,
                words=[],  # chưa có timing → để trống
            )
        )
    return TimingFile(source_srt=source_srt_name, lines=lines)
