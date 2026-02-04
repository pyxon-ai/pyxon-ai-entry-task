"""
Example: Run Comprehensive Benchmark
Run with: py examples/run_benchmark.py
"""
from pathlib import Path
from main import ArabicRAGPipeline
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Run comprehensive benchmark on the Arabic RAG system"""
    
    print("="*80)
    print("Arabic RAG Document Parser - Benchmark Suite")
    print("="*80)
    
    # Initialize pipeline
    print("\n1. Initializing pipeline...")
    pipeline = ArabicRAGPipeline(
        chunking_strategy='auto',
        device='cpu'
    )
    
    # Prepare test files
    pdf_file = "file_ar.pdf"
    txt_file = "file.txt"
    
    if not Path(pdf_file).exists() or not Path(txt_file).exists():
        print(f"⚠️  Test files not found!")
        print(f"Please ensure these files exist:")
        print(f"  - {pdf_file}")
        print(f"  - {txt_file}")
        return
    
    # Test queries
    test_queries = [
        "ما هي الخدمات المتوفرة؟",
        "معلومات عن إعادة التدوير",
        "البلاستيك والمعادن",
        "النفايات العضوية",
        "الشركات والمؤسسات",
        "الحديد والمعادن",
        "الورق والكرتون",
        "نفايات الطعام",
    ]
    
    print("\n2. Running benchmark...")
    print(f"   - Documents: {pdf_file}, {txt_file}")
    print(f"   - Test queries: {len(test_queries)}")
    
    # Run benchmark
    results = pipeline.run_benchmark(
        file_paths=[pdf_file, txt_file],
        test_queries=test_queries,
        ground_truth_pdf=pdf_file,
        ground_truth_txt=txt_file,
        run_name="arabic_rag_benchmark"
    )
    
    # Display results
    print("\n" + "="*80)
    print("Benchmark Results")
    print("="*80)
    
    print("\n📊 Performance Metrics:")
    print(f"  Total processing time: {results['performance']['total_processing_time']:.2f}s")
    print(f"  Avg time per chunk: {results['performance']['avg_chunk_time']:.4f}s")
    print(f"  Peak memory usage: {results['performance']['peak_memory_mb']:.2f} MB")
    print(f"  Avg memory usage: {results['performance']['avg_memory_mb']:.2f} MB")
    
    print("\n🎯 Quality Metrics:")
    print(f"  Retrieval accuracy: {results['quality']['retrieval_accuracy']:.2%}")
    print(f"  Hit rate: {results['quality']['hit_rate']:.2%}")
    print(f"  MRR (Mean Reciprocal Rank): {results['quality']['mrr']:.3f}")
    
    print("\n⚙️  Configuration:")
    print(f"  Chunking strategy: {results['configuration']['chunking_strategy']}")
    print(f"  Number of documents: {results['configuration']['num_documents']}")
    print(f"  Number of chunks: {results['configuration']['num_chunks']}")
    
    print("\n⏱️  Timing Breakdown:")
    for step, time_taken in results['timing_breakdown'].items():
        print(f"  {step.capitalize()}: {time_taken:.2f}s")
    
    print("\n✅ Benchmark complete! Results saved to output directory.")
    
    # Compare different chunking strategies
    print("\n" + "="*80)
    print("Comparing Chunking Strategies")
    print("="*80)
    
    strategies = ['fixed', 'semantic', 'auto']
    strategy_results = []
    
    for strategy in strategies:
        print(f"\nTesting '{strategy}' strategy...")
        
        # Reinitialize with different strategy
        test_pipeline = ArabicRAGPipeline(
            chunking_strategy=strategy,
            device='cpu'
        )
        
        # Reset vector store
        test_pipeline.reset()
        
        # Run benchmark
        result = test_pipeline.run_benchmark(
            file_paths=[pdf_file],
            test_queries=test_queries[:3],  # Use subset for speed
            run_name=f"benchmark_{strategy}"
        )
        
        strategy_results.append({
            'strategy': strategy,
            'processing_time': result['performance']['total_processing_time'],
            'num_chunks': result['configuration']['num_chunks'],
            'hit_rate': result['quality']['hit_rate'],
        })
    
    # Display comparison
    print("\n" + "="*80)
    print("Strategy Comparison")
    print("="*80)
    print(f"{'Strategy':<15} {'Chunks':<10} {'Time (s)':<12} {'Hit Rate':<10}")
    print("-" * 80)
    
    for r in strategy_results:
        print(f"{r['strategy']:<15} {r['num_chunks']:<10} {r['processing_time']:<12.2f} {r['hit_rate']:<10.2%}")
    
    print("\n✅ All benchmarks complete!")


if __name__ == "__main__":
    main()
