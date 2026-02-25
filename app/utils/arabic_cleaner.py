import re
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:
    arabic_reshaper = None
    get_display = None

def fix_arabic_text_direction(text: str) -> str:
    """
    Fix visual ordering issues in Arabic text extracted from PDFs.
    Uses arabic-reshaper to fix ligatures and python-bidi for direction.
    """
    if not text or not arabic_reshaper:
        return text
    
    # Smart Detection: Check if text actually needs fixing
    # If text contains isolated forms that usually appear when text is broken (visual storage)
    # or if it looks reversed. This is a heuristic.
    # We can check for specific common disconnected letters often found in broken PDFs
    needs_fixing = False
    
    # Smart Detection: Check if text uses "Presentation Forms" (Visual Encoding)
    # This is the definitive sign that the PDF assumes the renderer handles no shaping.
    # Ranges: Arabic Presentation Forms-A (FB50–FDFF) and B (FE70–FEFF)
    if re.search(r'[\uFB50-\uFDFF\uFE70-\uFEFF]', text):
         needs_fixing = True
    
    # Also check for widely separated isolated letters if no presentation forms found
    # (Heuristic: high ratio of isolated Alif/Lam relative to text length)
    # But usually, the presentation forms check is enough for the "scrambled" cases.
    
    if not needs_fixing:
        return text

    try:
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except Exception:
        return text

def normalize_arabic_text(text: str) -> str:
    """
    Standardize Arabic text for consistent processing.
    """
    if not text:
        return ""

    # 1. Fix Visual Encoding Issues (Important for some PDFs)
    # Re-enabling this as per user request to handle broken PDF glyph orders
    text = fix_arabic_text_direction(text) 

    # 2. Basic Normalization
    # Remove extensive whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    # Remove Tatweel (Kashida)
    text = re.sub(r'ـ', '', text)

    # Normalize Alef forms
    text = re.sub(r'[أإآ]', 'ا', text) 
    
    # Normalize Yeh
    text = re.sub(r'ى', 'ي', text)
    
    # Normalize digits (Indic to Arabic)
    text = text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    
    return text

def remove_diacritics(text: str) -> str:
    """
    Remove Arabic diacritics (Fatha, Damma, Kasra, etc.).
    Useful for normalized comparison or search indexing.
    """
    arabic_diacritics = re.compile("""
                             ّ    | # Shadda
                             َ    | # Fatha
                             ً    | # Tanwin Fath
                             ُ    | # Damma
                             ٌ    | # Tanwin Damm
                             ِ    | # Kasra
                             ٍ    | # Tanwin Kasr
                             ْ    | # Sukun
                             ـ     # Tatweel
                         """, re.VERBOSE)
    return re.sub(arabic_diacritics, '', text)

def calculate_diacritics_ratio(text: str) -> float:
    """
    Calculate the ratio of diacritics to Arabic letters.
    """
    if not text:
        return 0.0
        
    diacritics = re.findall(r'[\u064B-\u0652]', text)
    letters = re.findall(r'[\u0600-\u06FF]', text)
    
    if not letters:
        return 0.0
        
    return len(diacritics) / len(letters)
