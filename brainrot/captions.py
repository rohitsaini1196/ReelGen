import re
from typing import List
from brainrot.align import WordTiming

# libass (via ffmpeg's static build) has no reliable color-emoji fallback - burning emoji in
# renders as a tofu box, not the glyph. Drop emoji-only tokens from captions rather than show that.
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "\U00002190-\U000021FF"
    "‍️"
    "]+",
    flags=re.UNICODE,
)

RESOLUTION = (1080, 1920)
FONT_NAME = "Montserrat"
FONT_SIZE = 90
BASE_COLOR = "&H00FFFFFF"       # white, ASS is &HAABBGGRR
HIGHLIGHT_COLOR = "&H0000E5FF"  # bright yellow-orange (BGR order)
OUTLINE_COLOR = "&H00000000"    # black outline
GROUP_SIZE = 4                  # words shown on screen together per caption group

ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {res_x}
PlayResY: {res_y}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},{primary},{secondary},{outline},&H64000000,1,0,0,0,100,100,0,0,1,6,0,2,60,60,220,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _ts(seconds: float) -> str:
    seconds = max(seconds, 0.0)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _group_words(words: List[WordTiming], group_size: int) -> List[List[WordTiming]]:
    return [words[i:i + group_size] for i in range(0, len(words), group_size)]


def _karaoke_line(group: List[WordTiming]) -> str:
    boundaries = [w.start for w in group] + [group[-1].end]
    parts = []
    for i, word in enumerate(group):
        dur_cs = max(round((boundaries[i + 1] - boundaries[i]) * 100), 1)
        parts.append(f"{{\\k{dur_cs}}}{word.word}")
    return " ".join(parts)


def build_ass(
    words: List[WordTiming],
    output_path: str,
    group_size: int = GROUP_SIZE,
    resolution=RESOLUTION,
    font: str = FONT_NAME,
    font_size: int = FONT_SIZE,
) -> str:
    if not words:
        raise ValueError("no words to caption")

    cleaned = []
    for w in words:
        text = _EMOJI_RE.sub("", w.word).strip()
        if text:
            cleaned.append(WordTiming(text, w.start, w.end))
    words = cleaned
    if not words:
        raise ValueError("no words left to caption after stripping emoji")

    header = ASS_HEADER.format(
        res_x=resolution[0],
        res_y=resolution[1],
        font=font,
        size=font_size,
        primary=HIGHLIGHT_COLOR,
        secondary=BASE_COLOR,
        outline=OUTLINE_COLOR,
    )

    lines = [header]
    for group in _group_words(words, group_size):
        start = _ts(group[0].start)
        end = _ts(group[-1].end)
        text = _karaoke_line(group)
        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n")

    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return output_path


if __name__ == "__main__":
    import sys
    import re

    src = sys.argv[1] if len(sys.argv) > 1 else "/tmp/align_out.txt"
    words = []
    with open(src) as f:
        for line in f:
            m = re.match(r"\s*([\d.]+)\s*-\s*([\d.]+)\s+(.+)", line)
            if m:
                words.append(WordTiming(m.group(3).strip(), float(m.group(1)), float(m.group(2))))

    out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/brainrot_captions.ass"
    build_ass(words, out)
    print(f"wrote {out}, {len(words)} words")
