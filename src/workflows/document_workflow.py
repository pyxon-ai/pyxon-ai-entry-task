"""LlamaIndex Workflows for intelligent document processing."""

from typing import List, Dict, Any, Optional
from llama_index.core import Document as LlamaDocument
from llama_index.core.workflow import (
    Workflow,
    StartEvent,
    StopEvent,
    step,
)
from llama_index.llms.openai import OpenAI
from llama_index.llms.anthropic import Anthropic

from src.models.document import Document, Chunk
from src.chunking.strategies import IntelligentChunker, FixedChunker, DynamicChunker
from src.embeddings.generator import get_embedding_generator
from src.arabic.processor import get_arabic_processor
from src.config.settings import settings


class DocumentAnalysisEvent:
    """Event for document analysis."""
    def __init__(self, document: Document):
        self.document = document


class ChunkingDecisionEvent:
    """Event for chunking decision."""
    def __init__(self, document: Document, decision: str):
        self.document = document
        self.decision = decision


class ChunkingEvent:
    """Event for chunking."""
    def __init__(self, document: Document, chunks: List[Chunk]):
        self.document = document
        self.chunks = chunks


class EmbeddingEvent:
    """Event for embedding generation."""
    def __init__(self, chunks: List[Chunk]):
        self.chunks = chunks


class DocumentProcessingWorkflow(Workflow):
    """LlamaIndex workflow for intelligent document processing."""

    def __init__(self):
        super().__init__()
        self.embedding_generator = get_embedding_generator()
        self.arabic_processor = get_arabic_processor()
        
        # Initialize LLM for decision making
        if settings.openai_api_key:
            self.llm = OpenAI(api_key=settings.openai_api_key, model=settings.llm_model)
        elif settings.anthropic_api_key:
            self.llm = Anthropic(api_key=settings.anthropic_api_key, model=settings.llm_model)
        else:
            self.llm = None
        
        # Initialize chunkers
        self.fixed_chunker = FixedChunker(
            chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap,
        )
        self.dynamic_chunker = DynamicChunker(
            max_chunk_size=1000,
            min_chunk_size=200,
        )
        self.intelligent_chunker = IntelligentChunker(
            fixed_chunker=self.fixed_chunker,
            dynamic_chunker=self.dynamic_chunker,
        )

    @step()
    async def analyze_document(self, ev: StartEvent) -> DocumentAnalysisEvent:
        """Analyze document structure and content."""
        document = ev.document
        
        # Extract key features
        features = {
            "language": document.metadata.language,
            "has_arabic": document.metadata.has_arabic,
            "has_diacritics": document.metadata.has_diacritics,
            "word_count": document.metadata.word_count,
            "page_count": document.metadata.page_count or 0,
            "title": document.metadata.title,
            "content_sample": document.content[:500],
        }
        
        # Store analysis in document
        document.analysis = features
        
        return DocumentAnalysisEvent(document=document)

    @step()
    async def decide_chunking_strategy(
        self, ev: DocumentAnalysisEvent
    ) -> ChunkingDecisionEvent:
        """Decide on the best chunking strategy using LLM."""
        document = ev.document
        
        if self.llm:
            # Use LLM to make intelligent decision
            prompt = f"""Analyze this document and decide the best chunking strategy.

Document Info:
- Title: {document.metadata.title}
- Language: {document.metadata.language}
- Has Arabic: {document.metadata.has_arabic}
- Has Diacritics: {document.metadata.has_diacritics}
- Word Count: {document.metadata.word_count}
- Page Count: {document.metadata.page_count}

Content Sample:
{document.content[:1000]}

Decide the best chunking strategy:
1. "fixed" - For uniform, structured documents (reports, forms)
2. "dynamic" - For documents with varying structure (books, mixed content)
3. "intelligent" - Let the system decide based on content analysis

Respond with just the strategy name (one word)."""

            try:
                response = await self.llm.achat_complete(prompt)
                decision = str(response).strip().lower()
                
                # Validate decision
                if decision not in ["fixed", "dynamic", "intelligent"]:
                    decision = "intelligent"
            except Exception as e:
                print(f"LLM decision failed: {e}")
                decision = "intelligent"
        else:
            # Fallback to intelligent chunking
            decision = "intelligent"
        
        return ChunkingDecisionEvent(document=document, decision=decision)

    @step()
    async def apply_chunking(self, ev: ChunkingDecisionEvent) -> ChunkingEvent:
        """Apply the chosen chunking strategy."""
        document = ev.document
        decision = ev.decision
        
        # Apply chunking based on decision
        if decision == "fixed":
            chunks = self.fixed_chunker.chunk(document)
            document.chunking_strategy = "fixed"
        elif decision == "dynamic":
            chunks = self.dynamic_chunker.chunk(document)
            document.chunking_strategy = "dynamic"
        else:
            chunks = self.intelligent_chunker.chunk(document)
            document.chunking_strategy = "intelligent"
        
        document.chunks = chunks
        
        return ChunkingEvent(document=document, chunks=chunks)

    @step()
    async def generate_embeddings(self, ev: ChunkingEvent) -> EmbeddingEvent:
        """Generate embeddings for chunks."""
        chunks = ev.chunks
        
        if chunks:
            self.embedding_generator.embed_chunks(chunks)
        
        return EmbeddingEvent(chunks=chunks)

    @step()
    async def finalize(self, ev: EmbeddingEvent) -> StopEvent:
        """Finalize processing."""
        return StopEvent(result={"chunks": ev.chunks, "status": "completed"})


async def process_document_with_workflow(document: Document) -> Dict[str, Any]:
    """Process a document using LlamaIndex workflow."""
    workflow = DocumentProcessingWorkflow()
    
    result = await workflow.run(document=document)
    
    return result
