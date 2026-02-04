"""Answer generation using LLMs."""

from typing import List, Dict, Any, Optional
from openai import OpenAI
from anthropic import Anthropic

from src.config.settings import settings


class AnswerGenerator:
    """Generate answers using LLMs."""

    def __init__(self):
        """Initialize LLM clients."""
        self.openai_client = None
        self.anthropic_client = None
        
        if settings.openai_api_key:
            self.openai_client = OpenAI(api_key=settings.openai_api_key)
        
        if settings.anthropic_api_key:
            self.anthropic_client = Anthropic(api_key=settings.anthropic_api_key)

    def generate_answer(
        self,
        query: str,
        context: List[str],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        """
        Generate an answer based on query and context.
        
        Args:
            query: User question
            context: Relevant context chunks
            model: Model to use (gpt-4o, claude-3-5-sonnet, etc.)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        
        Returns:
            Generated answer
        """
        model = model or settings.llm_model

        # If no API clients are configured, return a simple extractive fallback
        if not self.openai_client and not self.anthropic_client:
            context_texts = [c for c in context if c]
            joined = "\n\n".join(context_texts)[:800]
            return joined if joined else "No relevant information found."

        # Format context
        context_text = "\n\n".join([f"Context {i+1}:\n{c}" for i, c in enumerate(context)])
        
        # Build prompt
        prompt = f"""You are a helpful assistant that answers questions based on the provided context.

Context:
{context_text}

Question: {query}

Please provide a comprehensive answer based on the context above. If the context doesn't contain enough information, say so.
"""
        
        # Generate answer based on model
        if model.startswith("gpt"):
            try:
                return self._generate_openai(prompt, model, temperature, max_tokens)
            except Exception:
                # Fallback extractive answer
                context_texts = [c for c in context if c]
                joined = "\n\n".join(context_texts)[:800]
                return joined if joined else "No relevant information found."
        elif model.startswith("claude"):
            try:
                return self._generate_anthropic(prompt, model, temperature, max_tokens)
            except Exception:
                context_texts = [c for c in context if c]
                joined = "\n\n".join(context_texts)[:800]
                return joined if joined else "No relevant information found."
        else:
            # Unknown model -> fallback
            context_texts = [c for c in context if c]
            joined = "\n\n".join(context_texts)[:800]
            return joined if joined else "No relevant information found."

    def _generate_openai(
        self, prompt: str, model: str, temperature: float, max_tokens: int
    ) -> str:
        """Generate answer using OpenAI."""
        if not self.openai_client:
            raise ValueError("OpenAI API key not configured")
        
        response = self.openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        return response.choices[0].message.content

    def _generate_anthropic(
        self, prompt: str, model: str, temperature: float, max_tokens: int
    ) -> str:
        """Generate answer using Anthropic."""
        if not self.anthropic_client:
            raise ValueError("Anthropic API key not configured")
        
        response = self.anthropic_client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "user", "content": prompt},
            ],
        )
        
        return response.content[0].text

    def generate_arabic_answer(
        self,
        query: str,
        context: List[str],
        model: Optional[str] = None,
    ) -> str:
        """
        Generate answer in Arabic.
        
        Args:
            query: User question (in Arabic)
            context: Relevant context chunks
            model: Model to use
        
        Returns:
            Generated Arabic answer
        """
        model = model or settings.llm_model

        # If no API clients are configured, return a simple extractive fallback in Arabic
        if not self.openai_client and not self.anthropic_client:
            context_texts = [c for c in context if c]
            joined = "\n\n".join(context_texts)[:800]
            return joined if joined else "لم يتم العثور على معلومات ذات صلة."

        # Format context
        context_text = "\n\n".join([f"السياق {i+1}:\n{c}" for i, c in enumerate(context)])
        
        # Build Arabic prompt
        prompt = f"""أنت مساعد مفيد يجيب على الأسئلة بناءً على السياق المقدم.

السياق:
{context_text}

السؤال: {query}

يرجى تقديم إجابة شاملة بناءً على السياق أعلاه. إذا لم يكن السياق يحتوي على معلومات كافية، قل ذلك.
"""
        
        # Generate answer
        if model.startswith("gpt"):
            try:
                return self._generate_openai(prompt, model, 0.7, 500)
            except Exception:
                context_texts = [c for c in context if c]
                joined = "\n\n".join(context_texts)[:800]
                return joined if joined else "لم يتم العثور على معلومات ذات صلة."
        elif model.startswith("claude"):
            try:
                return self._generate_anthropic(prompt, model, 0.7, 500)
            except Exception:
                context_texts = [c for c in context if c]
                joined = "\n\n".join(context_texts)[:800]
                return joined if joined else "لم يتم العثور على معلومات ذات صلة."
        else:
            context_texts = [c for c in context if c]
            joined = "\n\n".join(context_texts)[:800]
            return joined if joined else "لم يتم العثور على معلومات ذات صلة."


# Global answer generator instance
answer_generator = None


def get_answer_generator() -> AnswerGenerator:
    """Get or create the global answer generator instance."""
    global answer_generator
    if answer_generator is None:
        answer_generator = AnswerGenerator()
    return answer_generator
