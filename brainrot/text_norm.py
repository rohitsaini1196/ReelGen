import re
import unicodedata
from num2words import num2words

_CURRENCY = {"$": "dollar", "€": "euro", "£": "pound", "₹": "rupee"}
_CURRENCY_RE = re.compile(r"([$€£₹])\s?(\d+)(?:\.(\d+))?")
_NUMBER_RE = re.compile(r"\b\d+\b")
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "\U00002190-\U000021FF"
    "]+",
    flags=re.UNICODE,
)


def _currency_to_words(match: re.Match) -> str:
    symbol, whole, cents = match.group(1), match.group(2), match.group(3)
    unit = _CURRENCY.get(symbol, "dollar")
    whole_words = num2words(int(whole))
    whole_plural = "s" if int(whole) != 1 else ""
    out = f"{whole_words} {unit}{whole_plural}"
    if cents:
        cents_val = int(cents.ljust(2, "0")[:2])
        if cents_val:
            cents_words = num2words(cents_val)
            cents_plural = "s" if cents_val != 1 else ""
            out += f" and {cents_words} cent{cents_plural}"
    return out


def _number_to_words(match: re.Match) -> str:
    return num2words(int(match.group(0)))


def normalize_for_tts(text: str) -> str:
    """Safety-net normalization for TTS: assumes the LLM already wrote a mostly
    TTS-clean spoken_script, but catches anything it missed (stray digits,
    currency symbols, emoji) so the aligner never chokes downstream."""
    text = _EMOJI_RE.sub("", text)
    text = _CURRENCY_RE.sub(_currency_to_words, text)
    text = _NUMBER_RE.sub(_number_to_words, text)
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
