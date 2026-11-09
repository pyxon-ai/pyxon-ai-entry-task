"""Embedding backends.

``get_embedder()`` returns the best backend available:

1. ``SentenceTransformerEmbedder`` - multilingual neural model
   (default ``intfloat/multilingual-e5-small``, strong on Arabic) when
   ``sentence-transformers`` is installed and the model can be loaded.
2. ``HashingEmbedder`` - a dependency-light fallback: character n-grams
   (2-5, word-boundary aware) + word unigrams/bigrams hashed into a fixed
   space with sublinear TF and L2 normalization. It is stateless (no fit
   step), so documents can be added incrementally to the vector DB, and it
   runs on normalized text, so it is diacritic- and hamza-insensitive.

2b. ``FastEmbedEmbedder`` - the same kind of multilingual neural model run through
   ONNX Runtime (``pip install fastembed``), much lighter than PyTorch.

Set ``PYXON_EMBEDDER=hashing``, ``fastembed`` or ``<hf model name>`` to force one.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache

import numpy as np

from .arabic import normalize_for_index, strip_diacritics
from .text import content_tokens

log = logging.getLogger(__name__)


class Embedder:
    name: str = "base"
    dim: int = 0

    def embed(self, texts: list[str], *, is_query: bool = False) -> np.ndarray:
        raise NotImplementedError

    def embed_one(self, text: str, *, is_query: bool = False) -> np.ndarray:
        return self.embed([text], is_query=is_query)[0]

    @property
    def index_key(self) -> str:
        """Names the vector collection: the model plus how its input is prepared."""
        return self.name


class HashingEmbedder(Embedder):
    def __init__(self, dim: int = 2048):
        from sklearn.feature_extraction.text import HashingVectorizer

        self.dim = dim
        self.name = f"hashing-char2-5+word1-2-{dim}"
        # alternate_sign=False keeps vectors non-negative -> cosine in [0, 1].
        self._char = HashingVectorizer(
            analyzer="char_wb", ngram_range=(2, 5), n_features=dim, alternate_sign=False, norm=None
        )
        self._word = HashingVectorizer(
            analyzer=lambda s: self._word_ngrams(s), n_features=dim, alternate_sign=False, norm=None
        )

    @staticmethod
    def _word_ngrams(text: str) -> list[str]:
        toks = content_tokens(text, expand=False)
        return toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]

    def embed(self, texts: list[str], *, is_query: bool = False) -> np.ndarray:
        norm = [normalize_for_index(t) for t in texts]
        char = self._char.transform(norm)
        word = self._word.transform(texts)
        char.data = np.log1p(char.data)
        word.data = np.log1p(word.data)
        mat = (0.6 * char + 1.4 * word).toarray().astype(np.float32)
        lengths = np.linalg.norm(mat, axis=1, keepdims=True)
        lengths[lengths == 0] = 1.0
        return mat / lengths


def neural_input(texts: list[str]) -> list[str]:
    """Text as the neural models see it: harakat and tatweel removed, everything else unchanged.
    Pretrained multilingual models saw almost only unvocalized Arabic, so a vocalized word is cut into
    unfamiliar sub-word pieces and the same sentence with and without harakat gets different vectors.
    The stored text keeps every mark; only the model input is stripped."""
    return [strip_diacritics(t) for t in texts]


# Bump when neural_input changes: the vector collection name includes it, so stored vectors made
# from the old input are rebuilt automatically instead of being mixed with new ones.
NEURAL_INPUT_VERSION = "nodiac1"


class SentenceTransformerEmbedder(Embedder):
    def __init__(self, model_name: str = "intfloat/multilingual-e5-small"):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)
        self.name = model_name
        self.dim = self.model.get_sentence_embedding_dimension()
        self._e5 = "e5" in model_name.lower()

    @property
    def index_key(self) -> str:
        return f"{self.name}#{NEURAL_INPUT_VERSION}"

    def embed(self, texts: list[str], *, is_query: bool = False) -> np.ndarray:
        texts = neural_input(texts)
        if self._e5:
            prefix = "query: " if is_query else "passage: "
            texts = [prefix + t for t in texts]
        vecs = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(vecs, dtype=np.float32)


class FastEmbedEmbedder(Embedder):
    """Neural multilingual embeddings via ONNX Runtime (no PyTorch needed).

    Default model: paraphrase-multilingual-MiniLM-L12-v2 (quantized, ~220 MB, 384-d, 50+ languages
    incl. Arabic). Understands paraphrases and cross-language queries, which the hashing
    embedder cannot. Install with ``pip install fastembed``; the model downloads on first use.
    """

    DEFAULT = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    def __init__(self, model_name: str | None = None):
        from fastembed import TextEmbedding

        self.name = model_name or self.DEFAULT
        self.model = TextEmbedding(model_name=self.name)
        self.dim = len(next(iter(self.model.embed(["probe"]))))

    @property
    def index_key(self) -> str:
        return f"{self.name}#{NEURAL_INPUT_VERSION}"

    def embed(self, texts: list[str], *, is_query: bool = False) -> np.ndarray:
        vecs = np.asarray(list(self.model.embed(neural_input(texts))), dtype=np.float32)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vecs / norms


# Arabic-specific models suggested by the task (AraBERT / CAMeLBERT families), by short name.
# ``arabert`` is AraBERT v02 fine-tuned for Arabic sentence similarity (NLI + STS);
# ``camelbert`` is the raw CAMeLBERT-MSA encoder with mean pooling (not trained for similarity:
# included as a baseline to show why a sentence-level fine-tune matters).
ARABIC_MODELS = {
    "arabert": "Omartificial-Intelligence-Space/GATE-AraBert-v1",
    "camelbert": "CAMeL-Lab/bert-base-arabic-camelbert-msa",
}


@lru_cache(maxsize=4)
def get_embedder(choice: str | None = None) -> Embedder:
    """``hashing`` | ``fastembed`` | ``fastembed:<model>`` | ``arabert`` | ``camelbert`` | ``auto`` |
    <sentence-transformers model>. ``arabert``/``camelbert`` need ``pip install sentence-transformers``."""
    choice = choice or os.getenv("PYXON_EMBEDDER", "auto")
    choice = ARABIC_MODELS.get(choice, choice)
    if choice == "hashing":
        return HashingEmbedder()
    if choice.startswith("fastembed"):
        model = choice.split(":", 1)[1] if ":" in choice else None
        try:
            return FastEmbedEmbedder(model)
        except Exception as exc:
            log.warning("Could not load fastembed model (%s); falling back to hashing embedder", exc)
            return HashingEmbedder()
    model = "intfloat/multilingual-e5-small" if choice == "auto" else choice
    try:
        return SentenceTransformerEmbedder(model)
    except Exception as exc:  # missing package, no network, ...
        if choice != "auto":
            log.warning("Could not load %s (%s); falling back to hashing embedder", model, exc)
        return HashingEmbedder()


def cosine_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return a @ b.T
