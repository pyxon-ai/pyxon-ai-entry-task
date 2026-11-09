"""Arabic text utilities.

Design principle: the *original* text (with harakat/tashkeel) is always kept
for storage and display, while a *normalized* form is used for indexing,
embedding and keyword matching. That makes retrieval diacritic-insensitive
without ever destroying the diacritics the author wrote.
"""
from __future__ import annotations

import re
import unicodedata

# --- Unicode ranges ---------------------------------------------------------
# Harakat / tashkeel: fathatan..sukun (U+064B-U+0652), plus superscript alef
# (U+0670), Quranic annotation marks (U+0610-U+061A, U+06D6-U+06ED) and the
# maddah/hamza combining marks (U+0653-U+065F).
DIACRITICS_RE = re.compile(
    "[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E8\u06EA-\u06ED]"
)
TATWEEL = "\u0640"
ARABIC_LETTER_RE = re.compile("[\u0621-\u063A\u0641-\u064A\u0671-\u06D3\u06FA-\u06FF]")
LATIN_LETTER_RE = re.compile("[A-Za-z]")

HARAKAT_NAMES = {
    "ً": "fathatan",
    "ٌ": "dammatan",
    "ٍ": "kasratan",
    "َ": "fatha",
    "ُ": "damma",
    "ِ": "kasra",
    "ّ": "shadda",
    "ْ": "sukun",
    "ٰ": "superscript alef",
}

_ALEF_VARIANTS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا"})
_ARABIC_INDIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

# Arabic punctuation that should act as sentence boundaries.
ARABIC_SENTENCE_END = "؟۔"


def strip_diacritics(text: str) -> str:
    """Remove harakat/tashkeel (and tatweel) but keep every letter."""
    return DIACRITICS_RE.sub("", text).replace(TATWEEL, "")


def fix_presentation_forms(text: str) -> str:
    """Convert Arabic presentation forms (U+FB50-U+FDFF, U+FE70-U+FEFF) to base letters.

    PDF text extraction frequently returns contextual glyph codepoints
    (e.g. U+FEEB "heh initial form") instead of logical letters. NFKC maps
    them back to the standard Arabic block so search and embeddings work.
    """
    if re.search("[\uFB50-\uFDFF\uFE70-\uFEFF]", text):
        return unicodedata.normalize("NFKC", text)
    return text


def normalize_arabic(text: str, *, keep_diacritics: bool = False) -> str:
    """Normalize Arabic for matching.

    - presentation forms -> base letters
    - remove tatweel (kashida) and, unless asked otherwise, diacritics
    - unify alef variants (أ إ آ ٱ -> ا), alef maqsura (ى -> ي),
      taa marbuta (ة -> ه) and hamza carriers (ؤ -> و, ئ -> ي)
    - Arabic-Indic digits -> ASCII digits
    """
    text = fix_presentation_forms(text)
    text = text.replace(TATWEEL, "")
    if not keep_diacritics:
        text = DIACRITICS_RE.sub("", text)
    text = text.translate(_ALEF_VARIANTS)
    text = text.replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    return text.translate(_ARABIC_INDIC_DIGITS)


def normalize_for_index(text: str) -> str:
    """Language-agnostic normalization used for every indexed string."""
    text = unicodedata.normalize("NFC", text)
    text = normalize_arabic(text)
    return re.sub(r"\s+", " ", text).strip().lower()


def arabic_ratio(text: str) -> float:
    """Share of letters that are Arabic (0..1)."""
    ar = len(ARABIC_LETTER_RE.findall(text))
    la = len(LATIN_LETTER_RE.findall(text))
    total = ar + la
    return ar / total if total else 0.0


def diacritic_density(text: str) -> float:
    """Diacritics per Arabic letter. ~0 = undiacritized, >0.5 = fully vocalized."""
    letters = len(ARABIC_LETTER_RE.findall(text))
    if not letters:
        return 0.0
    return len(DIACRITICS_RE.findall(text)) / letters


def detect_language(text: str) -> str:
    """Return 'ar', 'en' or 'mixed' from script ratios."""
    r = arabic_ratio(text)
    if r >= 0.7:
        return "ar"
    if r <= 0.3:
        return "en"
    return "mixed"


def text_direction(text: str) -> str:
    """Base paragraph direction from the first strong character (Unicode bidi rule P2)."""
    for ch in text:
        bidi = unicodedata.bidirectional(ch)
        if bidi in ("R", "AL"):
            return "rtl"
        if bidi == "L":
            return "ltr"
    return "ltr"


def diacritic_stats(text: str) -> dict:
    """Counts per haraka, useful for verifying nothing was lost in the pipeline."""
    counts = {name: 0 for name in HARAKAT_NAMES.values()}
    for ch in DIACRITICS_RE.findall(text):
        if ch in HARAKAT_NAMES:
            counts[HARAKAT_NAMES[ch]] += 1
    counts["total"] = sum(counts.values())
    return counts


# Common Arabic function words, used for keyword extraction and the graph.
ARABIC_STOPWORDS = {
    normalize_for_index(w)
    for w in """
    في من على إلى عن مع هذا هذه ذلك تلك التي الذي الذين اللذان هو هي هم هن أنا نحن أنت
    كان كانت يكون تكون كانوا قد لقد لا لم لن ما ماذا متى أين كيف كل بعض أي أو أم ثم بل
    حتى إذا إذ إن أن كما لكن لكي لأن عند عندما بين بعد قبل فوق تحت حول ضد خلال منذ غير
    سوى إلا هناك هنا وقد وفي ومن وعلى وهو وهي وكان وكانت فقد فإن وإن به بها له لها لهم
    منه منها عليه عليها فيه فيها إليه إليها ذات أيضا جدا يمكن التى الى انه انها اي
    """.split()
}
