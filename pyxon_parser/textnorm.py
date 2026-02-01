import re
import unicodedata

_DIACRITICS_RE = re.compile(r"[\u064B-\u0652\u0670\u06D6-\u06ED]")

_AR_LETTERS_RE = re.compile(r"[\u0600-\u06FF]")
_LAT_LETTERS_RE = re.compile(r"[A-Za-z]")

def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)

def strip_diacritics(text: str) -> str:
    return _DIACRITICS_RE.sub("", text)

def strip_tatweel(text: str) -> str:
    return text.replace("\u0640", "")

def normalize_for_keyword(text: str) -> str:
    t = nfc(text)
    t = strip_tatweel(t)
    t = strip_diacritics(t)
    t = t.lower()
    return t

def arabic_ratio(text: str) -> float:
    if not text:
        return 0.0
    ar = len(_AR_LETTERS_RE.findall(text))
    return ar / max(1, len(text))

def latin_ratio(text: str) -> float:
    if not text:
        return 0.0
    en = len(_LAT_LETTERS_RE.findall(text))
    return en / max(1, len(text))

def diacritics_ratio(text: str) -> float:
    if not text:
        return 0.0
    d = len(_DIACRITICS_RE.findall(text))
    return d / max(1, len(text))

def tokenize_ar_en(text: str) -> list[str]:
    t = normalize_for_keyword(text)
    tokens = re.findall(r"[a-z0-9]+|[\u0600-\u06FF]+", t, flags=re.IGNORECASE)
    return [x for x in tokens if x and x.strip()]
