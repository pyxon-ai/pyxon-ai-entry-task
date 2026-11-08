# Pyxon AI - Junior Engineer Entry Task

## Overview

Your task is to build an **AI-powered document parser** that intelligently processes documents, understands their content, and prepares them for retrieval-augmented generation (RAG) systems. The parser should support multiple file formats, intelligent chunking strategies, and full Arabic language support including diacritics (harakat).

## Task Requirements

### 1. Document Parser

Create an AI parser that can:

- **Read multiple file formats:**
  - PDF files
  - DOC/DOCX files
  - TXT files

- **Content Understanding:**
  - Analyze and understand the semantic content of documents
  - Identify document structure, topics, and key concepts
  - Determine the most appropriate chunking strategy based on content

- **Intelligent Chunking:**
  - **Fixed chunking:** For uniform documents (e.g., structured reports, forms)
  - **Dynamic chunking:** For documents with varying structure (e.g., books with chapters, mixed content)
  - The parser should automatically decide which strategy to use based on document analysis

- **Storage:**
  - Save processed chunks to a **Vector Database** (for semantic search)
  - Save metadata and structured information to a **SQL Database** (for relational queries)

- **Arabic Language Support:**
  - Full support for Arabic text
  - Support for Arabic diacritics (harakat/tashkeel)
  - Proper handling of Arabic text encoding and directionality

### 2. Benchmark Suite

Create a comprehensive benchmark to test:

- **Retrieval accuracy:** How well the system retrieves relevant chunks for given queries
- **Chunking quality:** Evaluate if chunks maintain semantic coherence
- **Performance metrics:** Speed, memory usage, and scalability
- **Arabic-specific tests:** Verify proper handling of Arabic text and diacritics

### 3. RAG Integration

The parser should be designed to integrate with a RAG system that:
- Connects to LLMs for question answering
- Uses the vector database for semantic retrieval
- Uses the SQL database for structured queries

## Technical Specifications

### Recommended Approaches

Consider implementing advanced RAG techniques:

1. **Graph RAG:** Use knowledge graphs to represent document relationships and improve retrieval
2. **RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval):** Implement hierarchical document understanding and chunking
3. **Hybrid Retrieval:** Combine semantic (vector) and keyword-based retrieval

### Reference Material

- [NotebookLM Processing Sources - RAG Discussion](https://www.reddit.com/r/notebooklm/comments/1h1saih/how_is_notebooklm_processing_sources_rag_brute/)
- Research papers on Graph RAG
- RAPTOR implementation techniques

### Technology Stack

**You are free to use any framework, library, or technology stack of your choice.** The following are suggestions only:

- **Document Processing:** PyPDF2, python-docx, or similar libraries
- **NLP/Embeddings:** Transformers, sentence-transformers, or multilingual models
- **Vector DB:** Chroma, Pinecone, Weaviate, or Qdrant
- **SQL DB:** PostgreSQL, SQLite, or MySQL
- **Arabic NLP:** Consider models like CAMeLBERT, AraBERT, or multilingual models with Arabic support

Choose the tools and frameworks that best fit your implementation approach and expertise.

## Deadline

**Submission Deadline:** Monday, February 2nd, 13:00 Amman time.

**Review Timeline:** Code reviews and candidate calls will be conducted on Tuesday, February 3rd.

## Submission Guidelines

### Process

1. **Fork this repository** to your GitHub account
2. **Implement the solution** following the requirements above
3. **Create a working demo** that can be accessed and tested online
4. **Create a Pull Request** with:
   - **Contact Information** (required) - Your email address or phone number for communication
   - **Demo link** (required) - A live, accessible demo to test the implementation
   - Clear description of what was implemented
   - Architecture decisions and trade-offs
   - How to run the code
   - Benchmark results
   - Any limitations or future improvements
   - **Questions & Assumptions** - If you have any questions about the requirements, list them in the PR along with the assumptions you made to proceed

### Important Notes

- **Reply to emails:** After submitting your PR, you will receive an email. Please reply to confirm receipt and availability.
- **Questions:** If you have any questions or ambiguities about the requirements, include them in your PR description along with the assumptions you made to proceed with the implementation.

### PR Description Template

```markdown
## Summary
Brief overview of the implementation

## Contact Information
📧 Email: [your-email@example.com] or 📱 Phone: [your-phone-number] - **REQUIRED**

## Demo Link
🔗 [Link to live demo] - **REQUIRED**

## Features Implemented
- [ ] Document parsing (PDF, DOCX, TXT)
- [ ] Content analysis and chunking strategy selection
- [ ] Fixed and dynamic chunking
- [ ] Vector DB integration
- [ ] SQL DB integration
- [ ] Arabic language support
- [ ] Arabic diacritics support
- [ ] Benchmark suite
- [ ] RAG integration ready

## Architecture
Description of system design and key components

## Technologies Used
List of libraries and frameworks

## Benchmark Results
Key metrics and performance data

## How to Run
Step-by-step instructions

## Questions & Assumptions
If you had any questions about the requirements, list them here along with the assumptions you made:
- Question 1: [Your question]
  - Assumption: [How you proceeded]
- Question 2: [Your question]
  - Assumption: [How you proceeded]

## Future Improvements
Ideas for enhancement
```

**Note:** The demo link is a **mandatory requirement**. It should allow reviewers to test your implementation with sample documents (including Arabic documents with diacritics) and see the chunking and retrieval in action.

## Evaluation Criteria

Your submission will be evaluated on:

1. **Functionality:** All requirements are met
2. **Code Quality:** Clean, maintainable, well-documented code
3. **Arabic Support:** Proper handling of Arabic text and diacritics
4. **Intelligent Chunking:** Effective strategy selection and implementation
5. **Benchmark Quality:** Comprehensive tests and meaningful metrics
6. **Architecture:** Well-designed, scalable solution
7. **Documentation:** Clear README and code comments

## Questions?

If you have any questions about the requirements, please include them in your PR description along with the assumptions you made to proceed with the implementation. This helps us understand your decision-making process.

Good luck! 🚀
