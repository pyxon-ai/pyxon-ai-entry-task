"""Arabic text processing using CAMeL Tools."""

from typing import List, Optional, Dict
import warnings

# Suppress warnings from CAMeL Tools
warnings.filterwarnings('ignore')


class ArabicProcessor:
    """Process Arabic text with CAMeL Tools."""

    def __init__(self):
        """Initialize Arabic processors."""
        self.morphology = None
        self.tokenizer = None
        self.disambig = None
        self._load_tools()

    def _load_tools(self):
        """Load CAMeL Tools components."""
        try:
            from camel_tools.tokenizers.word import simple_word_tokenizer
            from camel_tools.morphology.database import MorphologyDB
            from camel_tools.morphology.analyzer import Analyzer
            
            # Initialize tokenizer
            self.tokenizer = simple_word_tokenizer
            
            # Initialize morphology database
            self.morphology_db = MorphologyDB.builtin_db()
            self.analyzer = Analyzer(self.morphology_db)
            
            # Initialize disambiguator
            from camel_tools.disambig.mle import MLEDisambiguator
            self.disambig = MLEDisambiguator(self.morphology_db)
            
            print("CAMeL Tools loaded successfully")
        except Exception as e:
            print(f"Warning: Failed to load CAMeL Tools: {e}")
            print("Arabic processing will be limited")
            self.tokenizer = None
            self.analyzer = None
            self.disambig = None

    def tokenize(self, text: str) -> List[str]:
        """Tokenize Arabic text."""
        if self.tokenizer:
            return self.tokenizer(text)
        else:
            # Fallback: simple whitespace tokenization
            return text.split()

    def analyze_morphology(self, word: str) -> List[Dict]:
        """
        Analyze the morphology of an Arabic word.
        
        Args:
            word: Arabic word to analyze
        
        Returns:
            List of possible analyses
        """
        if self.analyzer:
            analyses = self.analyzer.analyze(word)
            return [
                {
                    'word': word,
                    'lemma': a.lemma,
                    'pos': a.pos,
                    'root': a.root,
                    'features': a.features,
                }
                for a in analyses
            ]
        return []

    def disambiguate(self, tokens: List[str]) -> List[Dict]:
        """
        Disambiguate morphological analyses using context.
        
        Args:
            tokens: List of tokens
        
        Returns:
            List of disambiguated analyses
        """
        if self.disambig:
            analyses = self.disambig.disambiguate(tokens)
            return [
                {
                    'word': a.word,
                    'lemma': a.lemma,
                    'pos': a.pos,
                    'root': a.root,
                    'features': a.features,
                }
                for a in analyses
            ]
        return []

    def normalize(self, text: str) -> str:
        """
        Normalize Arabic text.
        
        Args:
            text: Arabic text to normalize
        
        Returns:
            Normalized text
        """
        from src.utils.text_utils import normalize_arabic_text
        return normalize_arabic_text(text)

    def remove_diacritics(self, text: str) -> str:
        """
        Remove diacritics from Arabic text.
        
        Args:
            text: Arabic text
        
        Returns:
            Text without diacritics
        """
        from src.utils.text_utils import remove_diacritics
        return remove_diacritics(text)

    def add_diacritics(self, text: str) -> str:
        """
        Add diacritics to Arabic text (if possible).
        
        Note: This requires Farasa or similar diacritizer.
        
        Args:
            text: Arabic text without diacritics
        
        Returns:
            Text with diacritics (if available)
        """
        try:
            # Try using Farasa for diacritization
            from farasa.segmenter import FarasaSegmenter
            from farasa.diacritizer import FarasaDiacritizer
            
            segmenter = FarasaSegmenter()
            diacritizer = FarasaDiacritizer()
            
            segmented = segmenter.segment(text)
            diacritized = diacritizer.diacritize(segmented)
            
            return diacritized
        except Exception as e:
            print(f"Warning: Diacritization failed: {e}")
            return text

    def extract_roots(self, text: str) -> List[str]:
        """
        Extract roots from Arabic words.
        
        Args:
            text: Arabic text
        
        Returns:
            List of roots
        """
        tokens = self.tokenize(text)
        roots = []
        
        for token in tokens:
            analyses = self.analyze_morphology(token)
            if analyses:
                root = analyses[0].get('root')
                if root:
                    roots.append(root)
        
        return roots

    def get_pos_tags(self, text: str) -> List[tuple]:
        """
        Get part-of-speech tags for Arabic text.
        
        Args:
            text: Arabic text
        
        Returns:
            List of (word, pos_tag) tuples
        """
        tokens = self.tokenize(text)
        analyses = self.disambiguate(tokens)
        
        return [(a['word'], a['pos']) for a in analyses]


# Global Arabic processor instance
arabic_processor = None


def get_arabic_processor() -> ArabicProcessor:
    """Get or create the global Arabic processor instance."""
    global arabic_processor
    if arabic_processor is None:
        arabic_processor = ArabicProcessor()
    return arabic_processor
