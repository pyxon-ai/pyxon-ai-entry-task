import re
import nltk
from typing import List, Dict

class IntelligentChunker:
    """
    Chunks document text using either fixed-size or dynamic (structure-aware) strategies.
    Ensures that sentences are not split mid-way whenever possible.
    """

    def __init__(self, default_chunk_size: int = 1000, default_overlap_sentences: int = 2):
        # We increase default chunk size to 1000 to give the mpnet model more context
        self.chunk_size = default_chunk_size
        self.overlap_sentences = default_overlap_sentences
        
        # Download NLTK punkt and punkt_tab tokenizers for sentence splitting if not already present
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('tokenizers/punkt_tab/english')
        except LookupError:
            nltk.download('punkt', quiet=True)
            nltk.download('punkt_tab', quiet=True)
            
    def fixed_chunking(self, text: str, chunk_size: int = None, overlap_sentences: int = None) -> List[str]:
        """
        Semantic Fixed-size chunking.
        Splits text into guaranteed full sentences, grouping them until reaching the approx chunk size.
        Overlap is handled by repeating the last N sentences in the next chunk.
        """
        size = chunk_size or self.chunk_size
        overlap = overlap_sentences if overlap_sentences is not None else self.overlap_sentences
        
        # Clean text
        text = text.replace('\\n', ' ')
        text = re.sub(r'\\s+', ' ', text).strip()
        
        if not text:
            return []
            
        sentences = nltk.tokenize.sent_tokenize(text)
        
        chunks = []
        current_chunk_sentences = []
        current_length = 0
        
        i = 0
        while i < len(sentences):
            sentence = sentences[i]
            
            # If a single sentence is larger than our chunk size limit, we just have to take it.
            if len(sentence) > size and not current_chunk_sentences:
                chunks.append(sentence)
                i += 1
                continue
                
            # Will adding this sentence push us over the limit?
            if current_length + len(sentence) > size and current_chunk_sentences:
                # Save the current chunk
                chunks.append(" ".join(current_chunk_sentences))
                
                # Step back `overlap` sentences to start the next chunk logically
                if i >= overlap:
                    i = i - overlap + 1
                else:
                    i += 1
                    
                current_chunk_sentences = []
                current_length = 0
            else:
                # Add sentence to current chunk
                current_chunk_sentences.append(sentence)
                current_length += len(sentence) + 1 # +1 for the space
                i += 1
                
        # Add any remaining sentences as the final chunk
        if current_chunk_sentences:
            chunks.append(" ".join(current_chunk_sentences))
            
        return chunks

    def chunk(self, text: str, analysis: Dict = None, strategy: str = "auto") -> List[str]:
        """
        Chunks the text. If strategy is 'auto', it looks at the analysis to decide.
        """
        effective_strategy = strategy
        if strategy == "auto" and analysis:
            effective_strategy = analysis.get("recommended_strategy", "fixed")
        elif strategy == "auto":
            effective_strategy = "fixed"

        if effective_strategy == "dynamic" and analysis:
            return self.dynamic_chunking(analysis)
        else:
            return self.fixed_chunking(text)
    def dynamic_chunking(self, analysis: Dict) -> List[str]:
        """
        Chunks based on document structure (paragraphs/headings).
        Avoids splitting mid-topic.
        """
        paragraphs = analysis.get("paragraphs", [])
        headings = analysis.get("headings", [])
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            # If the paragraph is a heading, it might be a new topic
            is_heading = para in headings
            
            if is_heading and current_chunk:
                # We hit a new topic boundary, finalize the current chunk
                chunks.append("\\n\\n".join(current_chunk))
                current_chunk = [para]
                current_length = len(para)
            else:
                if current_length + len(para) > self.chunk_size and current_chunk:
                    # Exceeding size, but we try not to split mid-paragraph if possible
                    chunks.append("\\n\\n".join(current_chunk))
                    current_chunk = [para]
                    current_length = len(para)
                else:
                    current_chunk.append(para)
                    current_length += len(para)
                    
        if current_chunk:
            chunks.append("\\n\\n".join(current_chunk))
            
        return chunks

if __name__ == "__main__":
    chunker = IntelligentChunker()
    text = "This is sentence one. This is sentence two? And this is three! الخلاصة هنا."
    print("Fixed Chunks:", chunker.fixed_chunking(text, chunk_size=30))
