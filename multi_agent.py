"""
Multi-Agent Orchestrator using Gemini API + RAG
Combines retrieval-augmented generation with Gemini's language understanding
"""
import os
import logging
from typing import List, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv

from google import genai

from main import ArabicRAGPipeline

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class MultiAgentOrchestrator:
    """
    Multi-Agent system that orchestrates:
    1. RAG Agent: Retrieves relevant context from documents
    2. Gemini Agent: Generates intelligent responses using retrieved context
    """
    
    def __init__(
        self,
        rag_pipeline: Optional[ArabicRAGPipeline] = None,
        gemini_api_key: Optional[str] = None,
        gemini_model: str = "gemini-3-flash-preview",
        max_results: int = 5,
        temperature: float = 0.7
    ):
        """
        Initialize Multi-Agent Orchestrator
        
        Args:
            rag_pipeline: Existing RAG pipeline or create new one
            gemini_api_key: Gemini API key (from .env if not provided)
            gemini_model: Gemini model name
            max_results: Number of context chunks to retrieve
            temperature: Response creativity (0=deterministic, 1=creative)
        """
        # Initialize RAG pipeline
        self.rag_pipeline = rag_pipeline or ArabicRAGPipeline()
        
        # Initialize Gemini client
        self.api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("Gemini API key not found. Set GEMINI_API_KEY in .env file")
        
        self.gemini_client = genai.Client(api_key=self.api_key)
        self.gemini_model = gemini_model
        self.max_results = max_results
        self.temperature = temperature
        
        logger.info(f"🤖 Multi-Agent Orchestrator initialized with {gemini_model}")
    
    def retrieve_context(self, query: str, n_results: Optional[int] = None) -> Dict:
        """
        RAG Agent: Retrieve relevant context from vector database
        
        Args:
            query: User query
            n_results: Number of results to retrieve
            
        Returns:
            Dictionary with retrieved documents and metadata
        """
        n_results = n_results or self.max_results
        
        logger.info(f"🔍 RAG Agent: Retrieving context for query: '{query}'")
        
        results = self.rag_pipeline.query(
            query_text=query,
            n_results=n_results
        )
        
        # Extract documents
        documents = results.get('results', {}).get('documents', [[]])[0]
        distances = results.get('results', {}).get('distances', [[]])[0]
        
        logger.info(f"✅ Retrieved {len(documents)} relevant chunks")
        
        return {
            'documents': documents,
            'distances': distances,
            'query': query
        }
    
    def generate_response(
        self,
        query: str,
        context_docs: List[str],
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Gemini Agent: Generate response using retrieved context
        
        Args:
            query: User query
            context_docs: Retrieved context documents
            system_prompt: Custom system prompt
            
        Returns:
            Generated response
        """
        # Default system prompt
        if system_prompt is None:
            system_prompt = """أنت مساعد ذكي متخصص في الإجابة على الأسئلة باللغة العربية.
استخدم المعلومات المتوفرة في السياق للإجابة على السؤال بدقة ووضوح.
إذا لم تجد إجابة في السياق، قل ذلك بصراحة."""
        
        # Build context
        context = "\n\n---\n\n".join(context_docs)
        
        # Build prompt
        prompt = f"""{system_prompt}

**السياق المتاح:**
{context}

**السؤال:**
{query}

**الإجابة:**"""
        
        logger.info(f"🧠 Gemini Agent: Generating response...")
        
        # Generate response with Gemini
        try:
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=prompt,
                config={
                    'temperature': self.temperature,
                }
            )
            
            answer = response.text
            logger.info(f"✅ Response generated ({len(answer)} chars)")
            
            return answer
            
        except Exception as e:
            logger.error(f"❌ Gemini API error: {e}")
            return f"عذراً، حدث خطأ في توليد الإجابة: {str(e)}"
    
    def ask(
        self,
        query: str,
        n_results: Optional[int] = None,
        system_prompt: Optional[str] = None,
        return_context: bool = False
    ) -> Dict[str, any]:
        """
        Main orchestration method: Retrieve context + Generate response
        
        Args:
            query: User question
            n_results: Number of context chunks to retrieve
            system_prompt: Custom system prompt for Gemini
            return_context: Whether to return retrieved context
            
        Returns:
            Dictionary with answer and optional context
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"🎯 User Query: {query}")
        logger.info(f"{'='*80}\n")
        
        # Step 1: Retrieve context (RAG Agent)
        context_data = self.retrieve_context(query, n_results)
        
        # Step 2: Generate response (Gemini Agent)
        answer = self.generate_response(
            query=query,
            context_docs=context_data['documents'],
            system_prompt=system_prompt
        )
        
        # Prepare result
        result = {
            'query': query,
            'answer': answer,
            'status': 'success'
        }
        
        if return_context:
            result['context'] = {
                'documents': context_data['documents'],
                'distances': context_data['distances'],
                'num_chunks': len(context_data['documents'])
            }
        
        return result
    
    def chat(self):
        """
        Interactive chat interface with multi-agent system
        """
        print("\n" + "="*80)
        print("🤖 Multi-Agent Arabic RAG Chat")
        print("="*80)
        print("اطرح أسئلتك بالعربية. اكتب 'exit' للخروج.")
        print("="*80 + "\n")
        
        while True:
            try:
                # Get user input
                query = input("✍️  أنت: ").strip()
                
                if not query:
                    continue
                
                if query.lower() in ['exit', 'quit', 'خروج']:
                    print("\n👋 شكراً لاستخدامك النظام!")
                    break
                
                # Get response
                result = self.ask(query, return_context=False)
                
                # Display answer
                print(f"\n🤖 المساعد: {result['answer']}\n")
                print("-" * 80 + "\n")
                
            except KeyboardInterrupt:
                print("\n\n👋 تم إنهاء المحادثة.")
                break
            except Exception as e:
                logger.error(f"Error in chat: {e}")
                print(f"\n❌ خطأ: {str(e)}\n")


def main():
    """Example usage of Multi-Agent Orchestrator"""
    
    print("\n" + "="*80)
    print("🚀 Initializing Multi-Agent System")
    print("="*80 + "\n")
    
    # Initialize orchestrator
    orchestrator = MultiAgentOrchestrator()
    
    # Example queries
    example_queries = [
        "ما هي خدمات إعادة التدوير المتوفرة في الأردن؟",
        "كيف يمكنني الاستفادة من إعادة تدوير البلاستيك؟",
        "ما هي فوائد إعادة التدوير للبيئة؟",
    ]
    
    print("📝 Running example queries...\n")
    
    for query in example_queries:
        result = orchestrator.ask(query, return_context=True)
        
        print(f"{'='*80}")
        print(f"❓ السؤال: {result['query']}")
        print(f"{'='*80}")
        print(f"💡 الإجابة:\n{result['answer']}")
        print(f"\n📚 عدد المراجع: {result['context']['num_chunks']}")
        print(f"{'='*80}\n")
    
    # Start interactive chat
    print("\n🎮 Starting interactive chat mode...\n")
    orchestrator.chat()


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    main()
