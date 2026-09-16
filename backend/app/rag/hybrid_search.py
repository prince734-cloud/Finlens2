"""
FinAdvisor Hybrid Search Engine.

Fuses Sparse Lexical Search (BM25Okapi) and Dense Semantic Search (ChromaDB)
using Reciprocal Rank Fusion (RRF). 

In financial documents, dense vector representations excel at semantic matching
(e.g., 'profitability outlook' -> 'operating margins'), while sparse BM25 retrieval
excels at exact numeric metrics ('$391,035', '9%'), accounting identifiers
('Item 1A', 'MD&A'), and company tickers ('AAPL', 'MSFT').
"""

import math
import re
import threading
from typing import Any, Dict, List, Optional, Tuple

from rank_bm25 import BM25Okapi

from backend.app.config import settings
from backend.app.rag.retriever import RetrievedChunk, retriever
from backend.app.utils.logger import logger


def financial_tokenize(text: str) -> List[str]:
    """
    Tokenizes financial text while preserving:
    - Currency values ($391,035, $96.17B)
    - Percentages (9%, 15.4%)
    - Numbers with commas/decimals (391,035, 118,264)
    - Accounting items and tickers (Item 1A, FY2024, AAPL, 10-K)
    """
    text = text.lower()
    pattern = (
        r"\$\d+(?:,\d{3})*(?:\.\d+)?%?[a-z]?"
        r"|\b\d+(?:,\d{3})*(?:\.\d+)?%"
        r"|\b\d+(?:,\d{3})+(?:\.\d+)?\b"
        r"|\b[a-z0-9]+(?:-[a-z0-9]+)*\b"
    )
    tokens = re.findall(pattern, text)
    return tokens if tokens else text.split()


class BM25Index:
    """
    In-memory BM25 index over document chunks with financial tokenization
    and metadata filtering.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._chunks: List[RetrievedChunk] = []
        self._chunk_lookup: Dict[str, RetrievedChunk] = {}
        self._corpus: List[List[str]] = []
        self._bm25: Optional[BM25Okapi] = None

    def _rebuild_index_locked(self) -> None:
        """Rebuilds BM25Okapi instance from current chunks with Lucene IDF adjustment."""
        if not self._chunks:
            self._bm25 = None
            self._corpus = []
            return

        self._corpus = [financial_tokenize(c.content) for c in self._chunks]
        self._bm25 = BM25Okapi(self._corpus)
        # Apply standard Lucene positive IDF formula: ln(1 + (N - n + 0.5) / (n + 0.5))
        # This guarantees non-negative, non-zero IDFs even in small test corpora (N <= 2)
        nd: Dict[str, int] = {}
        for doc in self._corpus:
            for term in set(doc):
                nd[term] = nd.get(term, 0) + 1

        n_docs = len(self._corpus)
        for term, freq in nd.items():
            self._bm25.idf[term] = math.log(1.0 + (n_docs - freq + 0.5) / (freq + 0.5))
        logger.debug(f"BM25 index updated with {len(self._chunks)} chunks.")

    def add_chunks(self, new_chunks: List[RetrievedChunk]) -> None:
        """Adds or updates chunks in the BM25 index."""
        if not new_chunks:
            return

        with self._lock:
            for c in new_chunks:
                if c.id in self._chunk_lookup:
                    # Update existing chunk
                    idx = next(i for i, existing in enumerate(self._chunks) if existing.id == c.id)
                    self._chunks[idx] = c
                else:
                    self._chunks.append(c)
                self._chunk_lookup[c.id] = c

            self._rebuild_index_locked()

    def remove_by_document_id(self, document_id: str) -> None:
        """Removes all chunks associated with a document_id."""
        with self._lock:
            self._chunks = [c for c in self._chunks if c.document_id != document_id]
            self._chunk_lookup = {c.id: c for c in self._chunks}
            self._rebuild_index_locked()

    def clear(self) -> None:
        """Clears all chunks from the index."""
        with self._lock:
            self._chunks.clear()
            self._chunk_lookup.clear()
            self._corpus.clear()
            self._bm25 = None

    def search(
        self,
        query: str,
        top_k: int = 10,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[RetrievedChunk, float]]:
        """
        Executes BM25 sparse search with optional metadata filtering.
        Returns list of (RetrievedChunk, raw_score) sorted by score descending.
        """
        with self._lock:
            if self._bm25 is None or not self._chunks:
                return []

            query_tokens = financial_tokenize(query)
            if not query_tokens:
                return []

            scores = self._bm25.get_scores(query_tokens)

            # Filter candidates based on 'where' condition if provided
            candidates: List[Tuple[RetrievedChunk, float]] = []
            for chunk, score in zip(self._chunks, scores):
                if score <= 0.0:
                    continue

                if where:
                    match = True
                    for k, v in where.items():
                        chunk_val = getattr(chunk, k, chunk.metadata.get(k))
                        if str(chunk_val) != str(v):
                            match = False
                            break
                    if not match:
                        continue

                candidates.append((chunk, float(score)))

            # Sort descending by BM25 score
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[:top_k]

    @property
    def count(self) -> int:
        return len(self._chunks)


class HybridSearchEngine:
    """
    Combines Dense Vector Retrieval (ChromaDB) and Sparse Lexical Retrieval (BM25)
    via Reciprocal Rank Fusion (RRF).
    """

    def __init__(self, bm25_index: Optional[BM25Index] = None):
        self.bm25_index = bm25_index or BM25Index()
        self._synced_with_chroma = False

    def sync_with_chroma(self) -> None:
        """
        Hydrates BM25 index with existing chunks stored in ChromaDB if available.
        """
        if self._synced_with_chroma:
            return

        try:
            total_count = retriever.count()
            if total_count == 0:
                self._synced_with_chroma = True
                return

            # Query all items from collection
            results = retriever.collection.get(include=["documents", "metadatas"])
            ids = results.get("ids", [])
            docs = results.get("documents", [])
            metas = results.get("metadatas", [])

            if ids and docs:
                chunks: List[RetrievedChunk] = []
                for chunk_id, doc, meta in zip(ids, docs, metas or []):
                    m = meta or {}
                    chunks.append(
                        RetrievedChunk(
                            id=chunk_id,
                            content=doc or "",
                            document_id=str(m.get("document_id", "")),
                            document_name=str(m.get("document_name", "Unknown Document")),
                            company_name=str(m.get("company_name", "Unknown Company")),
                            financial_year=int(str(m.get("financial_year", 2024))),
                            page_number=int(str(m.get("page_number", 1))),
                            section=str(m.get("section", "General")),
                            relevance_score=1.0,
                            metadata=dict(m)
                        )
                    )
                self.bm25_index.add_chunks(chunks)
                logger.info(f"Hydrated BM25 index with {len(chunks)} chunks from ChromaDB.")

            self._synced_with_chroma = True
        except Exception as e:
            logger.warning(f"Could not hydrate BM25 from ChromaDB on startup: {e}")

    def reciprocal_rank_fusion(
        self,
        dense_results: List[RetrievedChunk],
        sparse_results: List[Tuple[RetrievedChunk, float]],
        rrf_k: int = 60,
        dense_weight: float = 0.5,
        sparse_weight: float = 0.5
    ) -> List[RetrievedChunk]:
        """
        Computes Reciprocal Rank Fusion (RRF) scores:
        RRF_Score(d) = dense_weight / (rrf_k + rank_dense) + sparse_weight / (rrf_k + rank_sparse)
        """
        fused_scores: Dict[str, float] = {}
        chunk_map: Dict[str, RetrievedChunk] = {}

        # 1. Process dense rankings
        for rank, chunk in enumerate(dense_results, start=1):
            chunk_map[chunk.id] = chunk
            fused_scores[chunk.id] = fused_scores.get(chunk.id, 0.0) + (dense_weight / (rrf_k + rank))

        # 2. Process sparse rankings
        for rank, (chunk, _) in enumerate(sparse_results, start=1):
            if chunk.id not in chunk_map:
                chunk_map[chunk.id] = chunk
            fused_scores[chunk.id] = fused_scores.get(chunk.id, 0.0) + (sparse_weight / (rrf_k + rank))

        if not fused_scores:
            return []

        # Find max theoretical RRF score for normalization
        max_theoretical = (dense_weight / (rrf_k + 1)) + (sparse_weight / (rrf_k + 1))

        # Build fused list
        fused_chunks: List[RetrievedChunk] = []
        for chunk_id, raw_score in fused_scores.items():
            normalized_score = min(1.0, raw_score / max_theoretical) if max_theoretical > 0 else raw_score
            original = chunk_map[chunk_id]
            fused_chunk = RetrievedChunk(
                id=original.id,
                content=original.content,
                document_id=original.document_id,
                document_name=original.document_name,
                company_name=original.company_name,
                financial_year=original.financial_year,
                page_number=original.page_number,
                section=original.section,
                relevance_score=round(normalized_score, 4),
                metadata=dict(original.metadata)
            )
            fused_chunks.append(fused_chunk)

        # Sort descending by fused score
        fused_chunks.sort(key=lambda c: c.relevance_score, reverse=True)
        return fused_chunks

    def search(
        self,
        query: str,
        top_k: int = settings.TOP_K_RETRIEVAL,
        where: Optional[Dict[str, Any]] = None,
        rrf_k: int = 60,
        dense_weight: float = 0.5,
        sparse_weight: float = 0.5
    ) -> List[RetrievedChunk]:
        """
        Executes hybrid retrieval:
        1. Queries Dense Vector store (ChromaDB)
        2. Queries Sparse Lexical index (BM25)
        3. Combines candidates via Reciprocal Rank Fusion
        """
        self.sync_with_chroma()

        fetch_k = max(top_k * 2, 10)

        # 1. Dense retrieval
        dense_chunks = retriever.query_similar(query_text=query, top_k=fetch_k, where=where)

        # 2. Sparse retrieval
        sparse_results = self.bm25_index.search(query=query, top_k=fetch_k, where=where)

        # 3. Fuse results
        fused = self.reciprocal_rank_fusion(
            dense_results=dense_chunks,
            sparse_results=sparse_results,
            rrf_k=rrf_k,
            dense_weight=dense_weight,
            sparse_weight=sparse_weight
        )

        return fused[:top_k]


# Singleton instance
hybrid_search_engine = HybridSearchEngine()
