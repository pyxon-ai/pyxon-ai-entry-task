import json
import google.generativeai as genai
from helpers.config import get_settings
import cohere
import logging
from typing import Dict, List, Any
from datetime import datetime
import os

logger = logging.getLogger('uvicorn.error')

class EvaluationService:
    
    def __init__(self):
        settings = get_settings()
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.gemini = genai.GenerativeModel('gemini-2.0-flash-exp')
        self.cohere_client = cohere.Client(settings.COHERE_API_KEY)
        self.results_file = "evaluation_results.json"
    
    def load_test_questions(self) -> List[Dict]:
        questions_path = os.path.join(os.path.dirname(__file__), "..", "test_questions.json")
        with open(questions_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    async def search_for_question(self, question: str, limit: int = 5) -> List[Dict]:
        from services.weaviate_client import weaviate_client
        
        embedding_response = self.cohere_client.embed(
            texts=[question],
            model='embed-multilingual-v3.0',
            input_type='search_query',
            embedding_types=['float']
        )
        query_vector = embedding_response.embeddings.float[0]
        
        results = weaviate_client.semantic_search(
            query_vector=query_vector,
            limit=limit * 2
        )
        
        if not results:
            return []
        
        documents = [r["content"] for r in results]
        
        rerank_response = self.cohere_client.rerank(
            query=question,
            documents=documents,
            model='rerank-multilingual-v3.0',
            top_n=limit
        )
        
        reranked_results = []
        for result in rerank_response.results:
            original = results[result.index]
            reranked_results.append({
                **original,
                "relevance_score": result.relevance_score
            })
        
        return reranked_results
    
    def judge_with_gemini(self, question: str, source_file: str, chunks: List[Dict]) -> Dict:
        chunks_text = "\n\n".join([
            f"Chunk {i+1} (from: {chunk.get('file_name', 'unknown')}):\n{chunk['content'][:500]}"
            for i, chunk in enumerate(chunks)
        ])
        
        prompt = f"""You are evaluating a RAG system's retrieval quality for Arabic content.

Question: {question}
Expected Source File: {source_file}

Retrieved Chunks:
{chunks_text}

Evaluate on these criteria (0-10 scale):
1. **Relevance**: Do chunks relate to the question?
2. **Completeness**: Enough information to answer the question?
3. **Accuracy**: Is the information factually correct?
4. **Source Match**: Are chunks from the correct source file?

Respond ONLY in valid JSON format:
{{
  "relevance": <0-10>,
  "completeness": <0-10>,
  "accuracy": <0-10>,
  "source_match": <0-10>,
  "overall": <0-10>,
  "reasoning": "brief explanation in Arabic"
}}
"""
        
        try:
            response = self.gemini.generate_content(prompt)
            response_text = response.text.strip()
            
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            scores = json.loads(response_text)
            return scores
            
        except Exception as e:
            logger.error(f"Gemini judging error: {e}")
            return {
                "relevance": 0,
                "completeness": 0,
                "accuracy": 0,
                "source_match": 0,
                "overall": 0,
                "reasoning": f"Error: {str(e)}"
            }
    
    async def run_evaluation(self) -> Dict[str, Any]:
        questions = self.load_test_questions()
        results = []
        
        for q in questions:
            logger.info(f"Evaluating question {q['id']}: {q['question'][:50]}...")
            
            chunks = await self.search_for_question(q['question'], limit=5)
            
            scores = self.judge_with_gemini(
                question=q['question'],
                source_file=q['source_file'],
                chunks=chunks
            )
            
            result = {
                "question_id": q['id'],
                "question": q['question'],
                "source_file": q['source_file'],
                "retrieved_chunks": len(chunks),
                "chunks": chunks,
                "scores": scores,
                "timestamp": datetime.now().isoformat()
            }
            
            results.append(result)
        
        statistics = self.generate_statistics(results)
        
        output = {
            "timestamp": datetime.now().isoformat(),
            "total_questions": len(questions),
            "results": results,
            "statistics": statistics
        }
        
        with open(self.results_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        return output
    
    def generate_statistics(self, results: List[Dict]) -> Dict[str, Any]:
        if not results:
            return {}
        
        total = len(results)
        
        avg_relevance = sum(r['scores']['relevance'] for r in results) / total
        avg_completeness = sum(r['scores']['completeness'] for r in results) / total
        avg_accuracy = sum(r['scores']['accuracy'] for r in results) / total
        avg_source_match = sum(r['scores']['source_match'] for r in results) / total
        avg_overall = sum(r['scores']['overall'] for r in results) / total
        
        pass_count = sum(1 for r in results if r['scores']['overall'] >= 7)
        pass_rate = (pass_count / total) * 100
        
        by_file = {}
        for r in results:
            file = r['source_file']
            if file not in by_file:
                by_file[file] = []
            by_file[file].append(r['scores']['overall'])
        
        file_stats = {
            file: {
                "count": len(scores),
                "average": sum(scores) / len(scores),
                "min": min(scores),
                "max": max(scores)
            }
            for file, scores in by_file.items()
        }
        
        return {
            "total_questions": total,
            "pass_count": pass_count,
            "pass_rate": round(pass_rate, 2),
            "average_scores": {
                "relevance": round(avg_relevance, 2),
                "completeness": round(avg_completeness, 2),
                "accuracy": round(avg_accuracy, 2),
                "source_match": round(avg_source_match, 2),
                "overall": round(avg_overall, 2)
            },
            "by_file": file_stats
        }
    
    def get_latest_results(self) -> Dict[str, Any]:
        if not os.path.exists(self.results_file):
            return {"error": "No evaluation results found. Run evaluation first."}
        
        with open(self.results_file, 'r', encoding='utf-8') as f:
            return json.load(f)

evaluation_service = EvaluationService()
