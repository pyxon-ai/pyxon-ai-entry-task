import re
from typing import List, Dict

class DocumentAnalyzer:
    """
    Analyzes document text to determine its structure (headings, paragraphs)
    and identifies main topics using simple text heuristics.
    """

    def __init__(self):
        # A simple heuristic for headings: short lines, maybe ending without punctuation,
        # or starting with numbers (e.g., "1. Introduction").
        # Arabic text also follows similar structural patterns.
        self.heading_pattern = re.compile(r'^(?:[\\dA-Z]+\\.|[\\u0600-\\u06FF]+|[A-Z][a-zA-Z]+)[^\\.\\?!]{0,60}$', re.MULTILINE)

    def analyze(self, text: str) -> Dict:
        """
        Performs a structural analysis on the text.
        Returns a dictionary containing paragraphs, headings, and a recommended chunking strategy.
        """
        if not text or not text.strip():
            return {
                "paragraphs": [],
                "headings": [],
                "recommended_strategy": "fixed"
            }

        # Simple division by double newline for paragraphs
        paragraphs = [p.strip() for p in text.split('\\n\\n') if p.strip()]
        
        # Identify headings
        headings = self._extract_headings(text)
        
        # Heuristic to choose strategy
        # If the document has a good number of headings relative to its length, Use dynamic structure-aware chunking
        strategy = "fixed"
        if len(headings) > 0 and len(paragraphs) > len(headings):
            avg_paragraphs_per_heading = len(paragraphs) / len(headings)
            if 1 < avg_paragraphs_per_heading < 20: 
                strategy = "dynamic"
                
        # Main topics are often just the headings in a simplied model
        main_topics = headings

        return {
            "paragraphs": paragraphs,
            "headings": headings,
            "main_topics": main_topics,
            "recommended_strategy": strategy
        }

    def _extract_headings(self, text: str) -> List[str]:
        """
        Extracts potential headings using regex heuristics.
        """
        lines = text.split('\\n')
        headings = []
        for i, line in enumerate(lines):
            line = line.strip()
            # A heading is usually short, doesn't end with a period, and isn't empty.
            if len(line) > 2 and len(line) < 80:
                if not line.endswith(('.', '?', '!', '،', '؟')): # Includes Arabic punctuation
                    # Check if it looks distinct from surrounding text
                    # e.g., preceded and followed by empty lines or being very short
                    is_distinct = False
                    if i > 0 and i < len(lines) - 1:
                        if not lines[i-1].strip() and not lines[i+1].strip():
                            is_distinct = True
                    if self.heading_pattern.match(line) or is_distinct:
                        headings.append(line)
        return headings

if __name__ == "__main__":
    # Test cases including English and Arabic
    sample_text = """
1. Introduction
This is a test document.

2. Background
Here we discuss the background of the AI model.

الخلاصة
هذا نص تجريبي باللغة العربية للتحقق من العناوين.
"""
    analyzer = DocumentAnalyzer()
    print(analyzer.analyze(sample_text))
