import re
from langdetect import detect, DetectorFactory

DetectorFactory.seed = 0


class ContentAnalyzer:
    def analyze(self, text: str) -> dict:
        paragraphs = [p for p in text.split("\n") if p.strip()]
        paragraph_lengths = [len(p) for p in paragraphs]

        avg_paragraph_length = (
            sum(paragraph_lengths) / len(paragraph_lengths)
            if paragraph_lengths else 0
        )

        # Heuristic: detect headings (very simple but effective)
        headings = [
            p for p in paragraphs
            if len(p) < 100 and re.match(r"^[A-Zأ-ي].*", p)
        ]

        try:
            language = detect(text[:1000])
        except Exception:
            language = "unknown"

        return {
            "num_paragraphs": len(paragraphs),
            "avg_paragraph_length": avg_paragraph_length,
            "num_headings": len(headings),
            "language": language,
            "text_length": len(text)
        }