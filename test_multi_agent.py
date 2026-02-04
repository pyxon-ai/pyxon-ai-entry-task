"""
Simple test for Multi-Agent Orchestrator
"""
from multi_agent import MultiAgentOrchestrator
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

def main():
    print("\n" + "="*80)
    print("🧪 Testing Multi-Agent Orchestrator")
    print("="*80 + "\n")
    
    # Initialize
    orchestrator = MultiAgentOrchestrator()
    
    # Test query
    query = "ما هي خدمات إعادة التدوير المتوفرة؟"
    
    print(f"📝 Query: {query}\n")
    
    # Get response
    result = orchestrator.ask(query, return_context=True)
    
    # Display result
    print("\n" + "="*80)
    print("📊 Result:")
    print("="*80)
    print(f"\n💡 Answer:\n{result['answer']}\n")
    print(f"📚 Context chunks used: {result['context']['num_chunks']}")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
