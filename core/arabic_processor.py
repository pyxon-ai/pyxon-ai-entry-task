"""
Arabic Text Processor with RTL support and diacritics preservation
Adapted from extract.py with improvements
"""
import re
from typing import Optional, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class ArabicTextProcessor:
    """
    Handles Arabic text processing including:
    - RTL text correction
    - Diacritics (Harakat) preservation
    - Normalization for search and retrieval
    - Named entity handling
    """
    
    def __init__(self, preserve_diacritics: bool = True):
        """
        Initialize Arabic text processor
        
        Args:
            preserve_diacritics: Whether to preserve harakat in original text
        """
        self.preserve_diacritics = preserve_diacritics
        self.arabic_pattern = re.compile(r'[\u0600-\u06FF]')
        self.harakat_pattern = re.compile(r'[\u064B-\u065F]')
        
    def fix_rtl_extraction(self, text: str) -> str:
        """
        Fix RTL (Right-to-Left) text that was extracted incorrectly
        from PDF files (visual order to logical order)
        
        This is adapted from the fix_arabic_sentence function in extract.py
        
        Args:
            text: Raw extracted text potentially in visual RTL order
            
        Returns:
            Text in correct logical order
        """
        if not text:
            return ""
            
        lines = text.split('\n')
        fixed_lines = []
        
        for line in lines:
            if self.arabic_pattern.search(line):
                # Reverse characters in each word, then reverse word order
                # This fixes text extracted in Visual RTL format
                words = line.split()
                
                # Reverse characters in Arabic words only
                fixed_words = [
                    w[::-1] if self.arabic_pattern.search(w) else w 
                    for w in words
                ]
                
                # Reverse word order in the line
                fixed_lines.append(" ".join(fixed_words[::-1]))
            else:
                fixed_lines.append(line)
        
        # Merge lines preserving top-to-bottom order
        return " ".join(fixed_lines)
    
    def fix_common_pdf_errors(self, text: str) -> str:
        """
        Fix common PDF extraction errors specific to Arabic
        
        This includes:
        - Extra Alef characters
        - Reversed lam-alef combinations
        - Known words from the corpus
        
        Adapted from fix_pdf_arabic in extract.py
        
        Args:
            text: Text with potential PDF extraction errors
            
        Returns:
            Corrected text
        """
        if not text:
            return text
        
        # Common fixes dictionary
        fixes = {
            # Remove extra Alef
            r'اال': 'ال',
            r'األ': 'أل',
            r'اإل': 'إل',
            r'طال': 'طلال',
            
            # Fix reversed lam-alef
            r'\bأل': 'الأ',
            r'\bإل': 'الإ',
            r'وأل': 'والأ',
            r'وإل': 'والإ',
            
            # Specific known words
            r'\bالنتماء\b': 'الانتماء',
            r'\bالإعادة\b': 'لإعادة',
            r'\bطالل\b': 'طلال',
        }
        
        for pattern, replacement in fixes.items():
            text = re.sub(pattern, replacement, text)
        
        return text
    
    def normalize_for_search(self, text: str) -> str:
        """
        Normalize Arabic text for search-friendly indexing
        
        This version removes diacritics and normalizes Alef and Hamza variants
        while preserving the core meaning
        
        Args:
            text: Original Arabic text
            
        Returns:
            Normalized text optimized for search
        """
        if not text:
            return text
        
        normalized = text
        
        # Remove diacritics (Harakat)
        normalized = self.harakat_pattern.sub('', normalized)
        
        # Normalize Alef variants to standard Alef
        alef_variants = ['أ', 'إ', 'آ', 'ٱ']
        for variant in alef_variants:
            normalized = normalized.replace(variant, 'ا')
        
        # Normalize Taa Marbuta
        normalized = normalized.replace('ة', 'ه')
        
        # Remove Tatweel (elongation character)
        normalized = normalized.replace('ـ', '')
        
        # Normalize Hamza variants
        normalized = normalized.replace('ؤ', 'و')
        normalized = normalized.replace('ئ', 'ي')
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def create_dual_versions(self, text: str, apply_rtl_fix: bool = True) -> Tuple[str, str]:
        """
        Create both retrieval-friendly (with diacritics) and 
        search-friendly (normalized) versions of the text
        
        Args:
            text: Original Arabic text
            apply_rtl_fix: Whether to apply RTL correction (set to True for PDF)
            
        Returns:
            Tuple of (retrieval_version, search_version)
        """
        # First fix RTL and PDF errors (only if requested)
        retrieval_version = text
        if apply_rtl_fix:
            retrieval_version = self.fix_rtl_extraction(retrieval_version)
            retrieval_version = self.fix_common_pdf_errors(retrieval_version)
        
        # Create search version
        search_version = self.normalize_for_search(retrieval_version)
        
        return retrieval_version, search_version
    
    def extract_arabic_entities(self, text: str) -> list:
        """
        Extract potential Arabic named entities (proper nouns)
        
        This is a basic implementation that identifies:
        - Capitalized Arabic phrases (if mixed with English)
        - Common entity patterns
        
        Args:
            text: Text to extract entities from
            
        Returns:
            List of potential entity strings
        """
        entities = []
        
        # Pattern for detecting potential organization names
        # Usually contain "ال" prefix or end with common suffixes
        org_pattern = re.compile(
            r'(?:شركة|مؤسسة|جمعية|مركز|معهد|هيئة|وزارة)\s+[\u0600-\u06FF\s]{3,50}'
        )
        
        entities.extend(org_pattern.findall(text))
        
        # Pattern for detecting location names
        location_pattern = re.compile(
            r'(?:مدينة|محافظة|منطقة|حي)\s+[\u0600-\u06FF\s]{3,30}'
        )
        
        entities.extend(location_pattern.findall(text))
        
        return list(set(entities))  # Remove duplicates
    
    def is_arabic_text(self, text: str, threshold: float = 0.5) -> bool:
        """
        Determine if text is predominantly Arabic
        
        Args:
            text: Text to check
            threshold: Minimum ratio of Arabic characters (0-1)
            
        Returns:
            True if text is predominantly Arabic
        """
        if not text:
            return False
        
        # Remove whitespace for calculation
        text_no_space = text.replace(' ', '').replace('\n', '')
        
        if len(text_no_space) == 0:
            return False
        
        arabic_chars = len(self.arabic_pattern.findall(text))
        ratio = arabic_chars / len(text_no_space)
        
        return ratio >= threshold
    
    def clean_whitespace(self, text: str) -> str:
        """
        Clean excessive whitespace while preserving structure
        
        Args:
            text: Text with potential whitespace issues
            
        Returns:
            Cleaned text
        """
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        
        # Replace multiple newlines with maximum two
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove trailing/leading whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        
        return '\n'.join(lines)
    
    def process_text(self, text: str, mode: str = 'dual', apply_rtl_fix: bool = True) -> Dict[str, str]:
        """
        Main processing method that applies all necessary transformations
        
        Args:
            text: Raw text to process
            mode: Processing mode - 'dual', 'retrieval', or 'search'
            apply_rtl_fix: Whether to apply RTL correction
            
        Returns:
            Dictionary with processed text version(s)
        """
        if mode == 'dual':
            retrieval, search = self.create_dual_versions(text, apply_rtl_fix=apply_rtl_fix)
            retrieval = self.clean_whitespace(retrieval)
            search = self.clean_whitespace(search)
            
            return {
                'retrieval': retrieval,
                'search': search,
                'entities': self.extract_arabic_entities(retrieval),
                'is_arabic': self.is_arabic_text(retrieval)
            }
        
        elif mode == 'retrieval':
            retrieval = text
            if apply_rtl_fix:
                retrieval = self.fix_rtl_extraction(retrieval)
                retrieval = self.fix_common_pdf_errors(retrieval)
            retrieval = self.clean_whitespace(retrieval)
            
            return {
                'retrieval': retrieval,
                'is_arabic': self.is_arabic_text(retrieval)
            }
        
        elif mode == 'search':
            retrieval = text
            if apply_rtl_fix:
                retrieval = self.fix_rtl_extraction(retrieval)
                retrieval = self.fix_common_pdf_errors(retrieval)
            
            search = self.normalize_for_search(retrieval)
            search = self.clean_whitespace(search)
            
            return {
                'search': search,
                'is_arabic': self.is_arabic_text(search)
            }
        
        else:
            raise ValueError(f"Invalid mode: {mode}. Use 'dual', 'retrieval', or 'search'")


# Convenience functions for quick usage
def process_arabic_text(text: str, preserve_diacritics: bool = True) -> Dict[str, str]:
    """
    Convenience function to process Arabic text
    
    Args:
        text: Text to process
        preserve_diacritics: Whether to preserve harakat
        
    Returns:
        Dictionary with processed versions
    """
    processor = ArabicTextProcessor(preserve_diacritics=preserve_diacritics)
    return processor.process_text(text, mode='dual')
