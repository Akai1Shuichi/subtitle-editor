"""TikTok-style, word-by-word subtitle renderer for ASS/FFmpeg exports.

The renderer deliberately does *not* use ASS karaoke (``\\kf``): karaoke
paints a word from left to right, whereas this module swaps the active word
between white and yellow and gives only that word a short pop animation.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

import pysubs2
from pysubs2 import Alignment

from .word_timing import LineTiming, TimingFile, WordTiming

StyleMode = Literal["normal", "highlight", "soft_pop", "soft-pop", "punch", "rise", "pill", "rounded_box", "rounded-box"]


@dataclass(frozen=True)
class SubtitleSettings:
    """Visual settings in the actual ASS/video pixel coordinate system."""

    fontname: str = "Arial"
    fontsize: int = 54
    fontweight: int = 900
    text_color: tuple[int, int, int] = (255, 255, 255)
    highlight_color: tuple[int, int, int] = (255, 217, 0)
    stroke_color: tuple[int, int, int] = (0, 0, 0)
    stroke_width: float = 1.0
    shadow: float = 2.0
    position_y: int = 90  # top-origin percentage; equivalent to bottom: 10%
    max_words_per_group: int = 5
    alignment: Alignment = Alignment.BOTTOM_CENTER
    subtitle_width: int = 80  # % chiều rộng video mà subtitle chiếm (30–100)


@dataclass(frozen=True)
class SubtitleWord:
    text: str
    start_ms: int
    end_ms: int


@dataclass(frozen=True)
class SubtitleSegment:
    """A compact 2–5 word caption group, with individual word timings."""

    start_ms: int
    end_ms: int
    words: tuple[SubtitleWord, ...]


def _style_for(
    settings: SubtitleSettings,
    *,
    video_height: int,
    video_width: int = 1920,
    mode: StyleMode = "normal",
) -> pysubs2.SSAStyle:
    # ASS uses the video's PlayRes.  Do not downscale a configured 54px font
    # merely because the source is 720×1280: 54px must remain 54px there.
    alignment = settings.alignment
    if alignment in (Alignment.BOTTOM_LEFT, Alignment.BOTTOM_CENTER, Alignment.BOTTOM_RIGHT):
        margin_v = max(0, round((100 - settings.position_y) * video_height / 100))
    elif alignment in (Alignment.TOP_LEFT, Alignment.TOP_CENTER, Alignment.TOP_RIGHT):
        margin_v = max(0, round(settings.position_y * video_height / 100))
    else:
        # ASS không áp dụng MarginV cho middle alignment; realtime preview
        # cũng luôn căn chính giữa trong trường hợp này.
        margin_v = 0

    # Tính margin ngang từ subtitle_width (%)
    # margin_x = phần thừa mỗi bên = (100 - width_pct) / 2 % của video_width
    width_pct = max(10, min(100, settings.subtitle_width))
    margin_x = max(4, round((100 - width_pct) / 200 * video_width))

    if mode in ("rounded_box", "rounded-box"):
        txt_color = settings.text_color if settings.text_color != (255, 255, 255) else (17, 17, 17)
        bg_color = settings.highlight_color
        return pysubs2.SSAStyle(
            fontname=settings.fontname,
            fontsize=max(10, settings.fontsize),
            primarycolor=pysubs2.Color(*txt_color, 0),
            secondarycolor=pysubs2.Color(*bg_color, 0),
            outlinecolor=pysubs2.Color(*bg_color, 0),
            backcolor=pysubs2.Color(*bg_color, 0),
            bold=True,
            italic=False,
            scalex=100,
            scaley=100,
            spacing=0,
            borderstyle=3,
            outline=max(6, settings.stroke_width * 2.5),
            shadow=0,
            alignment=alignment,
            marginl=margin_x,
            marginr=margin_x,
            marginv=margin_v if video_height else 30,
            encoding=1,
        )

    return pysubs2.SSAStyle(
        fontname=settings.fontname,
        fontsize=max(10, settings.fontsize),
        primarycolor=pysubs2.Color(*settings.text_color, 0),
        secondarycolor=pysubs2.Color(*settings.highlight_color, 0),
        outlinecolor=pysubs2.Color(*settings.stroke_color, 0),
        backcolor=pysubs2.Color(*settings.stroke_color, 0),
        bold=True,
        italic=False,
        scalex=100,
        scaley=100,
        spacing=0,
        borderstyle=1,
        outline=max(1, settings.stroke_width),
        shadow=max(0, settings.shadow),
        alignment=alignment,
        marginl=margin_x,
        marginr=margin_x,
        marginv=margin_v if video_height else 30,
        encoding=1,
    )


class SubtitleRenderer:
    """Converts SRT events into compact, stable ASS word-highlight events."""

    def __init__(self, settings: SubtitleSettings, mode: StyleMode = "normal"):
        self.settings = settings
        self.mode = mode

    def build(
        self,
        subs: pysubs2.SSAFile,
        *,
        word_timings: Optional[TimingFile] = None,
        video_width: int = 0,
        video_height: int = 0,
    ) -> pysubs2.SSAFile:
        out = pysubs2.SSAFile()
        if video_width > 0 and video_height > 0:
            out.info["PlayResX"] = str(video_width)
            out.info["PlayResY"] = str(video_height)
        out.info["ScaledBorderAndShadow"] = "yes"
        # Preview canvas wraps words greedily from left to right.  ASS's
        # default smart wrapping rebalances lines, making Normal mode use
        # different line breaks from realtime preview.  WrapStyle 1 keeps
        # the same greedy behaviour; highlight mode already has explicit \N.
        out.info["WrapStyle"] = "1"
        out.styles["Default"] = _style_for(
            self.settings,
            video_height=video_height,
            video_width=video_width if video_width else 1920,
            mode=self.mode,
        )

        vh = video_height if video_height else 1080
        vw = video_width if video_width else 1920

        for index, event in enumerate(subs.events):
            if not event.text.strip():
                continue
            text = _strip_srt_tags(event.text)
            if self.mode == "normal":
                clean = copy.deepcopy(event)
                clean.style = "Default"
                clean.text = text
                out.events.append(clean)
                continue
            elif self.mode in ("soft_pop", "soft-pop"):
                clean = copy.deepcopy(event)
                clean.style = "Default"
                # Soft Pop animation: start 0.92 -> overshoot 1.04 (100ms) -> end 1.00 (180ms) + fade in 180ms
                anim_tag = r"{\fscx92\fscy92\fad(180,0)\t(0,100,\fscx104\fscy104)\t(100,180,\fscx100\fscy100)}"
                clean.text = anim_tag + text
                out.events.append(clean)
                continue
            elif self.mode in ("rounded_box", "rounded-box"):
                clean = copy.deepcopy(event)
                clean.style = "Default"
                clean.text = text
                out.events.append(clean)
                continue
            elif self.mode == "rise":
                clean = copy.deepcopy(event)
                clean.style = "Default"
                # Rise animation: move upwards from 16px below over 200ms + fade in 200ms
                margin_v = max(0, round((100 - self.settings.position_y) * vh / 100))
                align_val = int(self.settings.alignment)
                x = round(vw / 2)
                y_end = round(vh - margin_v) if align_val in (1, 2, 3) else (round(vh / 2) if align_val in (4, 5, 6) else margin_v)
                y_start = y_end + 16
                anim_tag = r"{\an%d\move(%d,%d,%d,%d,0,200)\fad(200,0)}" % (align_val, x, y_start, x, y_end)
                clean.text = anim_tag + text
                out.events.append(clean)
                continue

            timing = word_timings.get_line(index) if word_timings else None
            for segment in self._segments(event, text, timing):
                out.events.extend(self._segment_events(segment))
        return out

    def _segments(
        self, event: pysubs2.SSAEvent, text: str, timing: Optional[LineTiming]
    ) -> list[SubtitleSegment]:
        words = text.split()
        if not words:
            return []
        exact = timing and len(timing.words) == len(words) and timing.has_word_timing
        if exact:
            timed = [SubtitleWord(w, t.start_ms, t.end_ms) for w, t in zip(words, timing.words)]
        else:
            duration = max(1, event.end - event.start)
            timed = [
                SubtitleWord(word, event.start + round(i * duration / len(words)),
                             event.start + round((i + 1) * duration / len(words)))
                for i, word in enumerate(words)
            ]

        # Keep a long SRT sentence from becoming a third/fourth subtitle line.
        size = max(2, min(5, self.settings.max_words_per_group))
        return [
            SubtitleSegment(chunk[0].start_ms, chunk[-1].end_ms, tuple(chunk))
            for chunk in (timed[i:i + size] for i in range(0, len(timed), size))
        ]

    def _segment_events(self, segment: SubtitleSegment) -> list[pysubs2.SSAEvent]:
        events: list[pysubs2.SSAEvent] = []
        for active_index, active in enumerate(segment.words):
            end = (segment.words[active_index + 1].start_ms
                   if active_index + 1 < len(segment.words) else segment.end_ms)
            events.extend(self._word_events(segment, active_index, active.start_ms, max(active.start_ms + 1, end)))
        return events

    def _word_events(
        self, segment: SubtitleSegment, active_index: int, start: int, end: int
    ) -> list[pysubs2.SSAEvent]:
        if self.mode == "punch":
            active_dur = end - start
            peak = min(80, max(1, active_dur // 2))
            dur_anim = min(160, max(2, active_dur))
            anim_end = min(end, start + dur_anim)

            events: list[pysubs2.SSAEvent] = []

            if anim_end > start:
                # 1. Base line during animation (Layer 0): Active word hidden to prevent double-text underneath
                anim_base_text = self._render_words_punch_base_anim(segment.words, active_index)
                events.append(pysubs2.SSAEvent(
                    start=start,
                    end=anim_end,
                    style="Default",
                    text=anim_base_text,
                    layer=0,
                ))

                # 2. Scaling overlay during animation (Layer 1): Active word pops in scale
                overlay_text = self._render_words_punch_overlay(segment.words, active_index, peak, dur_anim)
                events.append(pysubs2.SSAEvent(
                    start=start,
                    end=anim_end,
                    style="Default",
                    text=overlay_text,
                    layer=1,
                ))

                # 3. Base line after animation finishes until word end (Layer 0): Active word static in highlight color
                if end > anim_end:
                    static_base_text = self._render_words_static(segment.words, active_index)
                    events.append(pysubs2.SSAEvent(
                        start=anim_end,
                        end=end,
                        style="Default",
                        text=static_base_text,
                        layer=0,
                    ))
            else:
                static_base_text = self._render_words_static(segment.words, active_index)
                events.append(pysubs2.SSAEvent(
                    start=start,
                    end=end,
                    style="Default",
                    text=static_base_text,
                    layer=0,
                ))

            return events

        return [pysubs2.SSAEvent(
            start=start,
            end=end,
            style="Default",
            text=self._render_words(segment.words, active_index, active_dur=end - start),
        )]

    def _highlight_ass_color(self) -> str:
        """Convert settings.highlight_color (R, G, B) to ASS inline colour tag format &HBBGGRR&."""
        r, g, b = self.settings.highlight_color
        return "&H%02X%02X%02X&" % (b, g, r)

    def _render_words_punch_base_anim(
        self, words: tuple[SubtitleWord, ...], active_index: int
    ) -> str:
        rendered: list[str] = []
        for index, word in enumerate(words):
            if index == active_index:
                rendered.append(r"{\1a&HFF&\2a&HFF&\3a&HFF&\4a&HFF&}%s{\r}" % word.text)
            else:
                rendered.append(word.text)
        return " ".join(rendered)

    def _render_words_static(
        self, words: tuple[SubtitleWord, ...], active_index: int
    ) -> str:
        rendered: list[str] = []
        highlight = self._highlight_ass_color()
        for index, word in enumerate(words):
            if index == active_index:
                rendered.append(r"{\1c%s}%s{\r}" % (highlight, word.text))
            else:
                rendered.append(word.text)
        return " ".join(rendered)

    def _render_words_punch_overlay(
        self, words: tuple[SubtitleWord, ...], active_index: int, peak: int, dur_anim: int
    ) -> str:
        rendered: list[str] = []
        highlight = self._highlight_ass_color()
        for index, word in enumerate(words):
            if index == active_index:
                rendered.append(
                    r"{\1c%s\t(0,%d,\fscx112\fscy112)\t(%d,%d,\fscx100\fscy100)}%s{\r}"
                    % (highlight, peak, peak, dur_anim, word.text)
                )
            else:
                rendered.append(r"{\1a&HFF&\2a&HFF&\3a&HFF&\4a&HFF&}%s{\r}" % word.text)
        return " ".join(rendered)

    def _render_words(
        self, words: tuple[SubtitleWord, ...], active_index: int, active_dur: int = 200
    ) -> str:
        rendered: list[str] = []
        highlight = self._highlight_ass_color()
        for index, word in enumerate(words):
            if index == active_index:
                rendered.append(
                    r"{\1c%s}%s{\r}" % (highlight, word.text)
                )
            else:
                rendered.append(word.text)
        return " ".join(rendered)



def build_ass(
    subs: pysubs2.SSAFile,
    mode: StyleMode = "normal",
    *,
    fontname: str = "Arial",
    fontsize: int = 54,
    text_color: tuple[int, int, int] = (255, 255, 255),
    highlight_color: tuple[int, int, int] = (255, 217, 0),
    alignment: int | Alignment = Alignment.BOTTOM_CENTER,
    margin_v: int = 30,
    word_timings: Optional[TimingFile] = None,
    video_width: int = 0,
    video_height: int = 0,
    position_y: int = 90,
    stroke_color: tuple[int, int, int] = (0, 0, 0),
    stroke_width: float = 1.0,
) -> pysubs2.SSAFile:
    """Build a reusable normal or word-pop-highlight ASS subtitle track.

    ``alignment`` and ``margin_v`` remain accepted for backward compatibility;
    TikTok-style captions always use centered, lower-screen placement.
    """
    settings = SubtitleSettings(
        fontname=fontname, fontsize=fontsize, text_color=text_color,
        highlight_color=highlight_color, stroke_color=stroke_color,
        stroke_width=stroke_width, position_y=position_y,
        alignment=Alignment(alignment) if isinstance(alignment, int) else alignment,
    )
    return SubtitleRenderer(settings, mode).build(
        subs, word_timings=word_timings, video_width=video_width, video_height=video_height
    )


def save_ass(ass: pysubs2.SSAFile, dest: str | Path) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    ass.save(str(dest))
    return dest.resolve()


def _strip_srt_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


# Kept as private compatibility helpers for existing integrations. They are no
# longer called by ``build_ass`` because the product intentionally has no
# karaoke-fill animation.
def _make_sentence_karaoke(event: pysubs2.SSAEvent) -> str:
    return _strip_srt_tags(event.text)


def _make_perword_karaoke(event: pysubs2.SSAEvent, line_timing: LineTiming) -> str:
    return _strip_srt_tags(event.text)
