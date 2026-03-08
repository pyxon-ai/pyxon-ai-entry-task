import os
import sys
import argparse

# Force standard output to use UTF-8 instead of Windows default (cp1252)
# This prevents UnicodeEncodeError when printing Arabic text to the console.
sys.stdout.reconfigure(encoding='utf-8')
from src.parser import DocumentParser
from src.analyzer import DocumentAnalyzer
from src.chunker import IntelligentChunker
from src.storage import StorageManager
from src.benchmark import BenchmarkSuite

def process_document(file_path: str, strategy: str = "auto"):
    """
    End-to-end pipeline: Parse -> Analyze -> Chunk -> Store
    """
    print(f"\\nProcessing document: {file_path}")
    
    # 1. Parse
    parser = DocumentParser()
    text = parser.parse(file_path)
    print(f"Extracted {len(text)} characters of text.")
    
    # 2. Analyze
    analyzer = DocumentAnalyzer()
    analysis = analyzer.analyze(text)
    print(f"Found {len(analysis['paragraphs'])} paragraphs and {len(analysis['headings'])} headings.")
    print(f"Recommended Strategy: {analysis['recommended_strategy']}")
    
    # 3. Chunk
    chunker = IntelligentChunker()
    chunks = chunker.chunk(text, analysis=analysis, strategy=strategy)
    effective_strategy = analysis['recommended_strategy'] if strategy == "auto" else strategy
    print(f"Created {len(chunks)} chunks using '{effective_strategy}' strategy.")
    
    # 4. Store
    filename = os.path.basename(file_path)
    storage = StorageManager()
    doc_id = storage.store_document(filename, chunks, effective_strategy)
    print(f"Stored document with ID: {doc_id}")
    
    return doc_id, filename, chunks

def run_benchmark(query: str, expected_filename: str = None, filter_filename: str = None):
    """Runs the benchmark suite on a query."""
    storage = StorageManager()
    suite = BenchmarkSuite(storage)
    
    if expected_filename:
        print(f"\\n--- Benchmark Results ---")
        score = suite.evaluate_retrieval(query, expected_filename, top_k=3)
        print(f"Retrieval Recall@3 for '{query}' (Expected File: {expected_filename}): {score * 100:.2f}%")
        
    results = storage.search(query, top_k=3, filter_filename=filter_filename)
    chunks = [res['text'] for res in results]
    quality_score = suite.evaluate_chunk_quality(chunks)
    print(f"Quality Score for retrieved chunks (No mid-sentence splits): {quality_score * 100:.2f}%")
    
    # Actually print the results for the user to see!
    print(f"\\n--- Top {len(chunks)} Retrieved Passages ---")
    for i, chunk in enumerate(chunks, 1):
        print(f"\\n[Result {i}]\\n{chunk}")
        print("-" * 40)
    
def main():
    parser = argparse.ArgumentParser(description="AI Document Parser - A Student Project")
    parser.add_argument("--file", type=str, help="Path to a PDF, DOCX, or TXT file to process", required=False)
    parser.add_argument("--strategy", type=str, choices=["auto", "fixed", "dynamic"], default="auto", help="Chunking strategy to use")
    parser.add_argument("--query", type=str, help="Query to test retrieval", required=False)
    parser.add_argument("--expected_file", type=str, help="Expected filename for the query test", required=False)
    parser.add_argument("--filter_file", type=str, help="Restrict search to a specific file", required=False)
    
    args = parser.parse_args()
    
    if args.file:
        process_document(args.file, args.strategy)
        
    if args.query:
        run_benchmark(args.query, expected_filename=args.expected_file, filter_filename=args.filter_file)
        
    if not args.file and not args.query:
        print("No arguments provided. Generating a sample text file to demonstrate...")
        sample_file = "sample_doc.txt"
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write("""1. Introduction
This is a sample document created automatically to demonstrate the system. It contains simple English text and some Arabic text to prove UTF-8 compatibility.

2. Arabic Support
اللغة العربية تعمل بشكل ممتاز   . شكراً جزيلاً.

3. Conclusion
We have implemented chunking, storage, and retrieval.
""")
        
        doc_id, filename, chunks = process_document(sample_file)
        run_benchmark("اللغة العربية", filename)
        print("\\nDone! Check the 'data' folder for SQLite and ChromaDB files.")

if __name__ == "__main__":
    main()
