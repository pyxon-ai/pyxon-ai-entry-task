"""
Example: Process and Query Arabic Documents
Run with: py examples/example_usage.py
"""
from pathlib import Path
from main import ArabicRAGPipeline
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Example workflow for processing and querying documents"""
    
    print("="*80)
    print("Arabic RAG Document Parser - Example Usage")
    print("="*80)
    
    # 1. Initialize pipeline
    print("\n1. Initializing pipeline...")
    pipeline = ArabicRAGPipeline(
        chunking_strategy='auto',  # Automatically select best strategy
        device='cpu'
    )
    
    # 2. Process documents
    print("\n2. Processing documents...")
    
    # Add your document paths here
    documents = [
        "file_ar.pdf",  # Arabic PDF
        "file.txt",     # Arabic text file
    ]
    
    # Filter existing files
    existing_docs = [doc for doc in documents if Path(doc).exists()]
    
    if not existing_docs:
        print("⚠️  No documents found! Please add documents to process.")
        print(f"Looking for: {documents}")
        return
    
    # Process all documents
    results = pipeline.process_batch(existing_docs)
    
    # Display results
    print("\n" + "="*80)
    print("Processing Results:")
    print("="*80)
    for result in results:
        if result['success']:
            print(f"✅ {result['file_path']}")
            print(f"   - Chunks: {result['num_chunks']}")
            print(f"   - Strategy: {result['chunking_strategy']}")
            print(f"   - Arabic: {result['is_arabic']}")
        else:
            print(f"❌ {result['file_path']}")
            print(f"   - Error: {result['error']}")
    
    # 3. Query the system
    print("\n3. Querying the system...")
    
    # Arabic queries
    queries = [
        "ما هي خدمات إعادة التدوير المتوفرة؟",
        "البلاستيك والمعادن",
        "معلومات عن النفايات العضوية",
        "الشركات والمنشآت",
    ]
    
    for query in queries:
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print('='*80)
        
        results = pipeline.query(query, n_results=3)
        
        if results['results']['documents'] and results['results']['documents'][0]:
            for i, (doc, distance) in enumerate(
                zip(results['results']['documents'][0], 
                    results['results']['distances'][0]),
                1
            ):
                print(f"\n{i}. Distance: {distance:.4f}")
                print(f"   {doc[:200]}...")
        else:
            print("   No results found.")
    
    # 4. Display statistics
    print("\n4. Pipeline Statistics:")
    print("="*80)
    stats = pipeline.get_stats()
    
    print(f"Documents processed: {stats['metadata_store']['total_documents']}")
    print(f"Total chunks: {stats['metadata_store']['total_chunks']}")
    print(f"Arabic documents: {stats['metadata_store']['arabic_documents']}")
    print(f"Embedding model: {stats['embedding_model']['model_name']}")
    print(f"Embedding dimension: {stats['embedding_model']['dimension']}")
    print(f"Chunking strategy: {stats['chunking_strategy']}")
    
    print("\n✅ Example complete!")


if __name__ == "__main__":
    main()
