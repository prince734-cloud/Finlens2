"""
FinLens Reranker Engine.

Supports two operational modes:
1. Fast Lexical & Hybrid Cross-Scorer (Default for <= 512MB RAM environments):
   Computes high-precision financial lexical overlap, exact phrase alignment,
   and numerical match scores. Consumes 0 MB model RAM, runs in < 1 ms.
2. Neural CrossEncoder (Optional for environments with >= 2GB RAM):
   Uses sentence-transformers CrossEncoder (ms-marco-MiniLM-L-6-v2) for joint
   transformer cross-attention when USE_CROSS_ENCODER is explicitly enabled.
"""

import math
import re
import threading
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
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


def _lexical_cross_score(query: str, chunk: RetrievedChunk) -> float:
    """
    Computes a deterministic cross-matching relevance score between query and chunk
    without requiring PyTorch or transformer weights in memory.
    Factors:
    - Query term coverage in passage
    - Exact financial phrase matches (e.g. 'net sales', 'supply chain', '$391,035')
    - Financial number / percentage matches
    - Section header relevance
    """
    query_lower = query.lower()
    content_lower = f"{chunk.section} {chunk.content}".lower()

    # Extract distinct alphanumeric tokens
    stop_words = {"what", "was", "were", "is", "are", "the", "in", "of", "and", "for", "to", "a", "an", "its", "it"}
    query_terms = [t for t in re.findall(r"[a-z0-9$%\.,]+", query_lower) if t not in stop_words]

    if not query_terms:
        return chunk.relevance_score

    # 1. Term overlap ratio
    matched_count = sum(1 for term in query_terms if term in content_lower)
    term_ratio = matched_count / max(len(query_terms), 1)

    # 2. Number / Currency exact matching boost
    number_terms = [t for t in query_terms if re.search(r"\d", t)]
    num_boost = 0.0
    if number_terms:
        matched_nums = sum(1 for nt in number_terms if nt in content_lower)
        num_boost = (matched_nums / len(number_terms)) * 0.25

    # 3. Exact high-signal phrases
    phrase_boost = 0.0
    high_signal_phrases = [
        "net sales", "total net sales", "net income", "operating income",
        "cash flow", "supply chain", "risk factors", "gross margin",
        "total revenue", "revenue growth", "balance sheet"
    ]
    for phrase in high_signal_phrases:
        if phrase in query_lower and phrase in content_lower:
            phrase_boost += 0.20

    # 4. Section relevance boost
    section_boost = 0.0
    if "risk" in query_lower and ("risk" in chunk.section.lower() or "item 1a" in chunk.section.lower()):
        section_boost += 0.15
    if any(k in query_lower for k in ("sale", "revenue", "income", "profit")) and ("operation" in chunk.section.lower() or "item 7" in chunk.section.lower() or "financial" in chunk.section.lower()):
        section_boost += 0.15

    # Raw composite score
    raw_score = (0.45 * term_ratio) + (0.25 * chunk.relevance_score) + num_boost + phrase_boost + section_boost
    # Normalize to [0.0, 1.0] range
    normalized = max(0.05, min(0.98, raw_score))
    return round(normalized, 4)


class CrossEncoderReranker:
    """
    Reranking service supporting both zero-RAM Lexical RRF scoring and Neural CrossEncoder.
    Thread-safe lazy initialization ensures model weights are loaded only once if enabled.
    """
    _instance: Optional["CrossEncoderReranker"] = None
    _lock = threading.Lock()

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.RERANKER_MODEL_NAME
        self.use_cross_encoder = settings.USE_CROSS_ENCODER and not settings.LOW_MEMORY_MODE
        self._model: Optional[object] = None

    @classmethod
    def get_instance(cls, model_name: Optional[str] = None) -> "CrossEncoderReranker":
        """Thread-safe singleton accessor."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(model_name=model_name)
        return cls._instance

    def _ensure_model_loaded(self) -> None:
        """Loads CrossEncoder model weights lazily on first invocation only if enabled."""
        if not self.use_cross_encoder:
            return

        if self._model is None:
            with self._lock:
                if self._model is None:
                    try:
                        from sentence_transformers import CrossEncoder
                        logger.info(f"Loading CrossEncoder reranker model: {self.model_name}...")
                        self._model = CrossEncoder(self.model_name)
                        logger.info("CrossEncoder reranker model loaded successfully.")
                    except Exception as e:
                        logger.warning(
                            f"Could not load CrossEncoder model ({e}). "
                            "Switching to zero-RAM lexical cross-reranker."
                        )
                        self.use_cross_encoder = False

    def rerank(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        top_k: Optional[int] = None
    ) -> List[RetrievedChunk]:
        """
        Reranks candidate chunks by contextual semantic relevance to the query.
        Returns top_k chunks sorted by score descending.
        """
        if not chunks:
            return []

        limit = top_k or settings.TOP_K_RERANKED

        if len(chunks) <= 1 or not query.strip():
            return chunks[:limit]

        # Mode A: Neural CrossEncoder (if enabled and high-memory environment)
        if self.use_cross_encoder:
            try:
                self._ensure_model_loaded()
                if self._model is not None:
                    pairs = [(query, c.content) for c in chunks]
                    raw_scores = self._model.predict(pairs)

                    reranked_chunks: List[RetrievedChunk] = []
                    for chunk, raw_score in zip(chunks, raw_scores):
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

                    reranked_chunks.sort(key=lambda c: c.relevance_score, reverse=True)
                    return reranked_chunks[:limit]
            except Exception as e:
                logger.warning(f"Neural CrossEncoder failed ({e}). Falling back to fast lexical reranker.")

        # Mode B: High-Performance Zero-RAM Lexical Reranker (Default for <= 512MB RAM)
        reranked_chunks = []
        for chunk in chunks:
            score = _lexical_cross_score(query, chunk)
            updated_chunk = RetrievedChunk(
                id=chunk.id,
                content=chunk.content,
                document_id=chunk.document_id,
                document_name=chunk.document_name,
                company_name=chunk.company_name,
                financial_year=chunk.financial_year,
                page_number=chunk.page_number,
                section=chunk.section,
                relevance_score=score,
                metadata=dict(chunk.metadata)
            )
            reranked_chunks.append(updated_chunk)

        reranked_chunks.sort(key=lambda c: c.relevance_score, reverse=True)
        return reranked_chunks[:limit]


# Singleton instance
reranker = CrossEncoderReranker.get_instance()
