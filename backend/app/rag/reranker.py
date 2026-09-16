"""
FinAdvisor Cross-Encoder Reranker.

Applies deep cross-attention re-scoring to candidate chunks retrieved from
hybrid search. Unlike bi-encoders (which encode query and document separately),
a cross-encoder processes query and passage jointly through all transformer layers,
capturing subtle linguistic nuance, conditional negatives, and contextual precision.
"""

import math
import threading
from typing import List, Optional

from sentence_transformers import CrossEncoder

from backend.app.config import settings
from backend.app.rag.retriever import RetrievedChunk
from backend.app.utils.logger import logger


def _sigmoid(x: float) -> float:
    """Standard sigmoid activation function mapping logits to [0, 1]."""
    try:
        return 1.0 / (1.0 + math.exp(-x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0


class CrossEncoderReranker:
    """
    Singleton cross-encoder reranking service using sentence-transformers CrossEncoder.
    Thread-safe lazy initialization ensures model weights are loaded only once.
    """
    _instance: Optional["CrossEncoderReranker"] = None
    _lock = threading.Lock()

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.RERANKER_MODEL_NAME
        self._model: Optional[CrossEncoder] = None

    @classmethod
    def get_instance(cls, model_name: Optional[str] = None) -> "CrossEncoderReranker":
        """Thread-safe singleton accessor."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(model_name=model_name)
        return cls._instance

    def _ensure_model_loaded(self) -> None:
        """Loads CrossEncoder model weights lazily on first invocation."""
        if self._model is None:
            with self._lock:
                if self._model is None:
                    logger.info(f"Loading CrossEncoder reranker model: {self.model_name}...")
                    self._model = CrossEncoder(self.model_name)
                    logger.info("CrossEncoder reranker model loaded successfully.")

    def rerank(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        top_k: Optional[int] = None
    ) -> List[RetrievedChunk]:
        """
        Computes joint cross-attention relevance scores between query and each chunk.
        Returns top_k chunks sorted by score descending.
        
        Graceful degradation: Falls back to existing chunk ordering if model inference fails.
        """
        if not chunks:
            return []

        limit = top_k or settings.TOP_K_RERANKED

        # If only 1 chunk or query is empty, return up to limit
        if len(chunks) <= 1 or not query.strip():
            return chunks[:limit]

        try:
            self._ensure_model_loaded()
            assert self._model is not None

            # Prepare cross-encoder pairs: (query, passage_content)
            pairs = [(query, c.content) for c in chunks]
            raw_scores = self._model.predict(pairs)

            reranked_chunks: List[RetrievedChunk] = []
            for chunk, raw_score in zip(chunks, raw_scores):
                # Map cross-encoder logit to [0, 1] probability via sigmoid
                normalized_score = _sigmoid(float(raw_score))
                updated_chunk = RetrievedChunk(
                    id=chunk.id,
                    content=chunk.content,
                    document_id=chunk.document_id,
                    document_name=chunk.document_name,
                    company_name=chunk.company_name,
                    financial_year=chunk.financial_year,
                    page_number=chunk.page_number,
                    section=chunk.section,
                    relevance_score=round(normalized_score, 4),
                    metadata=dict(chunk.metadata)
                )
                reranked_chunks.append(updated_chunk)

            # Sort descending by cross-encoder score
            reranked_chunks.sort(key=lambda c: c.relevance_score, reverse=True)
            return reranked_chunks[:limit]

        except Exception as e:
            logger.warning(f"Cross-encoder reranking failed ({e}). Falling back to hybrid rankings.")
            return chunks[:limit]


# Singleton instance
reranker = CrossEncoderReranker.get_instance()
