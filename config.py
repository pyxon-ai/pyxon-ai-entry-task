"""
Configuration settings for Arabic RAG Document Parser
"""
import os
from pathlib import Path

# Project Root
PROJECT_ROOT = Path(__file__).parent.absolute()
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
DB_DIR = PROJECT_ROOT / "databases"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
DB_DIR.mkdir(exist_ok=True)

# Database Configuration
SQLITE_DB_PATH = DB_DIR / "metadata.db"
CHROMA_DB_PATH = str(DB_DIR / "chroma_db")

# Embedding Model Configuration
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIMENSION = 384  # For the multilingual MiniLM model

# Chunking Configuration
class ChunkingConfig:
    """Configuration for text chunking strategies"""
    
    # Fixed-size chunking
    FIXED_CHUNK_SIZE = 512
    FIXED_CHUNK_OVERLAP = 128
    
    # Semantic chunking
    SEMANTIC_MIN_CHUNK_SIZE = 300
    SEMANTIC_MAX_CHUNK_SIZE = 600
    SEMANTIC_SIMILARITY_THRESHOLD = 0.5
    
    # Auto-selector thresholds
    HEADER_DENSITY_THRESHOLD = 0.05  # 5% of lines are headers
    AVERAGE_PARAGRAPH_LENGTH_THRESHOLD = 300  # chars
    

# Arabic Text Processing Configuration
class ArabicConfig:
    """Configuration for Arabic text processing"""
    
    # Arabic Unicode range
    ARABIC_UNICODE_RANGE = r'[\u0600-\u06FF]'
    
    # Diacritics (Harakat) range
    HARAKAT_RANGE = r'[\u064B-\u065F]'
    
    # Normalization options
    NORMALIZE_ALEF = True
    NORMALIZE_HAMZA = True
    REMOVE_TATWEEL = True
    
    # Common Arabic patterns to fix (from extract.py)
    COMMON_FIXES = {
        r'اال': 'ال',
        r'األ': 'أل',
        r'اإل': 'إل',
        r'طال': 'طلال',
        r'\bأل': 'الأ',
        r'\bإل': 'الإ',
        r'وأل': 'والأ',
        r'وإل': 'والإ',
        r'\bالنتماء\b': 'الانتماء',
        r'\bالإعادة\b': 'لإعادة',
        r'\bطالل\b': 'طلال',
    }


# Benchmark Configuration
class BenchmarkConfig:
    """Configuration for benchmarking and evaluation"""
    
    # Metrics to track
    TRACK_RETRIEVAL_ACCURACY = True
    TRACK_PROCESSING_TIME = True
    TRACK_MEMORY_USAGE = True
    
    # Test queries for Arabic
    TEST_QUERIES = [
        "ما هي الخدمات المتوفرة؟",
        "معلومات عن إعادة التدوير",
        "البلاستيك والمعادن",
        "النفايات العضوية",
    ]
    
    # Ground truth for testing
    GROUND_TRUTH_PDF = "file_ar.pdf"
    GROUND_TRUTH_TXT = "file.txt"


# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Processing Configuration
MAX_WORKERS = 4  # For parallel processing
BATCH_SIZE = 10  # Documents to process in batch
