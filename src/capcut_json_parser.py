"""
src/capcut_json_parser.py
──────────────────────────
Parser cho file draft_content.json từ CapCut (Desktop / Mobile).

Format input CapCut JSON:
- "materials": {"texts": [...], "text_templates": [...]}
- "tracks": [{"type": "text", "segments": [...]}]

Public API
----------
load_from_capcut_json(path)  →  (clips: list[SubtitleClip], timing: TimingFile)
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from .models import SubtitleClip
from .word_timing import TimingFile, LineTiming, WordTiming


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class CapCutJsonSubtitleError(Exception):
    """Base class cho mọi lỗi parse CapCut draft JSON."""


class CapCutJsonFormatError(CapCutJsonSubtitleError):
    """File CapCut JSON sai format hoặc thiếu các trường bắt buộc."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_from_capcut_json(
    path: str | Path,
) -> tuple[list[SubtitleClip], TimingFile]:
    """
    Parse file draft_content.json của CapCut và trả về (clips, timing).

    Parameters
    ----------
    path : đường dẫn đến file CapCut JSON draft

    Returns
    -------
    clips  : list[SubtitleClip] — sort theo start_ms, sẵn sàng gán vào project.clips
    timing : TimingFile — index 0-based khớp với vị trí trong clips.

    Raises
    ------
    FileNotFoundError       – file không tồn tại
    CapCutJsonFormatError   – JSON không khớp định dạng CapCut draft
    CapCutJsonSubtitleError – lỗi khác khi đọc file
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {path}")

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CapCutJsonSubtitleError(f"Không đọc được file '{path.name}': {exc}") from exc

    try:
        data: dict = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise CapCutJsonFormatError(
            f"File '{path.name}' không phải JSON hợp lệ: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise CapCutJsonFormatError(
            f"File '{path.name}' phải là JSON object (dict), nhận được {type(data).__name__}."
        )

    materials = data.get("materials")
    if not isinstance(materials, dict) or "texts" not in materials:
        raise CapCutJsonFormatError(
            f"File '{path.name}' không chứa khối 'materials' -> 'texts' của CapCut."
        )

    texts_list: list[dict] = [
        t for t in materials.get("texts", []) if isinstance(t, dict)
    ]
    if not texts_list:
        raise CapCutJsonFormatError(
            f"File '{path.name}' có 'materials.texts' nhưng mảng rỗng."
        )

    texts_map = {t["id"]: t for t in texts_list if "id" in t}

    # Ánh xạ từ text_template ID sang text_material_id (cho dạng animated / text templates)
    templates_list: list[dict] = [
        tmpl for tmpl in materials.get("text_templates", []) if isinstance(tmpl, dict)
    ]
    template_to_text: dict[str, str] = {}
    for tmpl in templates_list:
        tmpl_id = tmpl.get("id")
        res = tmpl.get("text_info_resources", [])
        if tmpl_id and isinstance(res, list) and len(res) > 0:
            text_mat_id = res[0].get("text_material_id")
            if text_mat_id:
                template_to_text[tmpl_id] = text_mat_id

    # Đọc timing từ các tracks type == "text"
    text_timing: dict[str, tuple[int, int]] = {}
    tracks = data.get("tracks", [])
    if isinstance(tracks, list):
        for tr in tracks:
            if not isinstance(tr, dict) or tr.get("type") != "text":
                continue
            segments = tr.get("segments", [])
            if not isinstance(segments, list):
                continue
            for seg in segments:
                if not isinstance(seg, dict):
                    continue
                trange = seg.get("target_timerange")
                if not isinstance(trange, dict):
                    continue

                raw_start = trange.get("start", 0)
                raw_dur = trange.get("duration", 0)
                start_ms = round(raw_start / 1000)
                dur_ms = round(raw_dur / 1000)

                mat_id = seg.get("material_id")
                target_text_id = None
                if mat_id in texts_map:
                    target_text_id = mat_id
                elif mat_id in template_to_text:
                    target_text_id = template_to_text[mat_id]

                if target_text_id:
                    text_timing[target_text_id] = (start_ms, dur_ms)

    entries: list[dict] = []
    for t_item in texts_list:
        t_id = t_item.get("id")
        if not t_id:
            continue

        # Lấy text content
        text_val = ""
        c_str = t_item.get("content", "")
        if c_str:
            try:
                c_obj = json.loads(c_str)
                if isinstance(c_obj, dict):
                    text_val = str(c_obj.get("text", "")).strip()
            except json.JSONDecodeError:
                pass
        if not text_val:
            text_val = str(t_item.get("recognize_text", "")).strip()
        if not text_val:
            text_val = "(no text)"

        # Timing
        if t_id in text_timing:
            start_ms, dur_ms = text_timing[t_id]
            end_ms = start_ms + max(100, dur_ms)
        else:
            # Fallback nếu không tìm thấy trong tracks
            start_ms = 0
            end_ms = 1000

        # Word timing
        words_data = t_item.get("words")
        json_words = []
        if isinstance(words_data, dict):
            w_texts = words_data.get("text", [])
            w_starts = words_data.get("start_time", [])
            w_ends = words_data.get("end_time", [])
            if (
                isinstance(w_texts, list)
                and isinstance(w_starts, list)
                and isinstance(w_ends, list)
            ):
                for w, s, e in zip(w_texts, w_starts, w_ends):
                    json_words.append({
                        "text": w,
                        "start_offset_ms": s,
                        "end_offset_ms": e,
                    })

        entries.append({
            "text_id": t_id,
            "text": text_val,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "words": json_words,
        })

    # Sort theo thời gian bắt đầu
    entries.sort(key=lambda e: (e["start_ms"], e["end_ms"]))

    clips: list[SubtitleClip] = []
    lines: list[LineTiming] = []

    for index, entry in enumerate(entries):
        clip_id = str(uuid.uuid4())
        c_start = entry["start_ms"]
        c_end = entry["end_ms"]

        clip = SubtitleClip(
            id=clip_id,
            text=entry["text"],
            start_ms=c_start,
            end_ms=c_end,
        )
        clips.append(clip)

        # Build word timings cho LineTiming
        word_timings: list[WordTiming] = []
        for w_info in entry["words"]:
            w_token = str(w_info["text"]).strip()
            if not w_token:
                continue
            w_start = c_start + int(w_info["start_offset_ms"])
            w_end = c_start + int(w_info["end_offset_ms"])

            # Clamp word timing trong clip range
            w_start = max(c_start, min(w_start, c_end))
            w_end = max(w_start + 1, min(max(w_end, w_start + 1), c_end))
            word_timings.append(WordTiming(
                word=w_token,
                start_ms=w_start,
                end_ms=w_end,
            ))

        line = LineTiming(
            index=index,
            start_ms=c_start,
            end_ms=c_end,
            words=word_timings,
        )
        lines.append(line)

    if not clips:
        raise CapCutJsonSubtitleError(
            f"File '{path.name}' không parse được clip nào hợp lệ."
        )

    timing = TimingFile(
        source_srt=path.name,
        lines=lines,
        version=1,
    )

    return clips, timing
