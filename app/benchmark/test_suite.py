import time
import os
import psutil
import sys

# Add the project root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.main import DocumentProcessor

def benchmark_processor(file_path: str):
    """
    Benchmark the document processing pipeline.
    Tests: Processing Time, Memory Consumption, and Chunk Efficiency.
    """
    if not os.path.exists(file_path):
        print(f"File {file_path} not found for benchmarking.")
        return

    processor = DocumentProcessor()
    
    # Measure Memory before
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / (1024 * 1024)
    
    start_time = time.time()
    
    # Process
    doc_id, _ = processor.process_file(file_path)
    
    end_time = time.time()
    mem_after = process.memory_info().rss / (1024 * 1024)
    
    duration = end_time - start_time
    mem_used = mem_after - mem_before

    # Get chunks from SQL DB to analyze
    # Assuming valid SQL schema with heading
    chunks = processor.sql_db.get_chunks(doc_id) 
    
    # Check if headings are preserved
    if chunks:
        print("\n--- Chunk Sample ---")
        for i, chunk_data in enumerate(chunks[:5]):
            content = chunk_data[0]
            heading = chunk_data[1] if len(chunk_data) > 1 else "N/A"
            print(f"chunk[{i}]: Heading='{heading}' | Content='{content[:30]}...'")

    processed_text = "\n".join([c[0] for c in chunks]) if chunks else ""
    
    # Calculate Diacritics Preservation
    from app.utils.arabic_cleaner import calculate_diacritics_ratio
    # Load original text for comparison
    from app.parser.loader import load_document
    original_text = load_document(file_path)
    
    orig_ratio = calculate_diacritics_ratio(original_text)
    proc_ratio = calculate_diacritics_ratio(processed_text)
    
    # Score: How close is the processed ratio to the original?
    # (1 - abs(orig - proc) / orig) * 100 roughly
    if orig_ratio > 0:
        preservation_score = (1 - abs(orig_ratio - proc_ratio) / orig_ratio) * 100
    else:
        preservation_score = 100.0 # No diacritics to lose
    
    print("\n" + "="*30)
    print("📊 BENCHMARK RESULTS")
    print("="*30)
    print(f"📄 File: {os.path.basename(file_path)}")
    print(f"⏱️  Duration: {duration:.2f} seconds")
    print(f"🧠 Memory Delta: {mem_used:.2f} MB")
    print(f"📦 Document ID: {doc_id}")
    print(f"💎 Diacritics Preservation: {preservation_score:.2f}% (Orig: {orig_ratio:.4f}, Proc: {proc_ratio:.4f})")
    print("="*30)

if __name__ == "__main__":
    # You can point this to any test file
    import sys
    if len(sys.argv) > 1:
        benchmark_processor(sys.argv[1])
    else:
        print("Usage: python app/benchmark/test_suite.py <path_to_file>")
