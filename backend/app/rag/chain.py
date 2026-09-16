"""
FinAdvisor LCEL Advanced RAG Execution Engine.

Constructs composable, high-speed, streaming-capable RAG pipelines using
LangChain Expression Language (LCEL) primitives:
- Query Rewriting & Decomposition (FinancialQueryRewriter)
- Hybrid Search Fusion (Dense ChromaDB + Sparse BM25 via Reciprocal Rank Fusion)
- Precision Cross-Encoder Reranking (ms-marco-MiniLM)
- Structured Source Grounding & Verifiable Citations (CitationEngine)
- RunnableParallel, RunnablePassthrough, RunnableLambda
- StrOutputParser
- ChatPromptTemplate / PromptTemplate
- Multi-provider LLMs (Groq, Mistral, Anthropic) with automatic fallbacks
"""

from typing import Any, Dict, List, Optional, Tuple

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import (
    Runnable,
    RunnableLambda,
    RunnableParallel,
)

from backend.app.config import settings
from backend.app.rag.citations import CitationEngine, CitationItem
from backend.app.rag.hybrid_search import hybrid_search_engine
from backend.app.rag.query_rewriter import query_rewriter
from backend.app.rag.reranker import reranker
from backend.app.rag.retriever import RetrievedChunk, retriever
from backend.app.services.llm_service import SYSTEM_FINANCIAL_RAG_PROMPT, llm_service
from backend.app.utils.logger import logger


# Domain-specific financial prompt template
RAG_CHAT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "{system_prompt}"),
    (
        "human",
        "=== RETRIEVED FINANCIAL SOURCES ===\n"
        "{context}\n\n"
        "=== USER QUERY ===\n"
        "{question}\n\n"
        "Provide a structured, fact-grounded response citing specific sources, pages, and sections:"
    )
])


class FinancialRAGPipeline:
    """
    Production-grade Advanced RAG pipeline implementing LangChain Expression Language (LCEL).
    
    Phase 3 Upgrades:
    1. Query Rewriting & Multi-Intent Decomposition: Handles compound questions and translates
       financial abbreviations (MD&A, P&L, 10-K) to official filing terminology.
    2. Hybrid Search (Dense + BM25 with RRF): Pairs dense semantic vectors with lexical
       keyword matching for exact financial figures, percentages, and tickers.
    3. Cross-Encoder Reranker: Joint cross-attention re-scoring to select top high-precision chunks.
    4. Verifiable Citations: Strict source grounding with document, page, and section references.
    """

    def __init__(self):
        self._prompt = RAG_CHAT_PROMPT
        self._output_parser = StrOutputParser()

    def _retrieve_chunks(self, inputs: Dict[str, Any]) -> List[RetrievedChunk]:
        """
        Executes Advanced RAG multi-stage retrieval:
        1. Query decomposition and financial expansion
        2. Hybrid search (Dense + BM25 RRF) per sub-query
        3. Deduplication and candidate fusion
        4. Cross-Encoder precision reranking
        """
        question = inputs.get("question", "")
        where = inputs.get("where")
        top_k = inputs.get("top_k", settings.TOP_K_RERANKED)
        use_reranker = inputs.get("use_reranker", True)

        if not question or not question.strip():
            return []

        # If vector store is completely empty, early exit
        if retriever.count() == 0:
            return []

        # 1. Query decomposition & domain expansion
        retrieval_queries = query_rewriter.rewrite_and_expand(question)

        # 2. Hybrid search across all sub-queries
        candidate_map: Dict[str, RetrievedChunk] = {}
        fetch_k = max(top_k * 3, 10)

        for query_variant in retrieval_queries:
            chunks = hybrid_search_engine.search(
                query=query_variant,
                top_k=fetch_k,
                where=where
            )
            # Fallback to unrestricted search if filtered search returned 0 results
            if not chunks and where is not None:
                logger.info(f"Filtered hybrid search returned 0 results for '{query_variant}'. Retrying across all indexed documents...")
                chunks = hybrid_search_engine.search(
                    query=query_variant,
                    top_k=fetch_k,
                    where=None
                )

            for chunk in chunks:
                if chunk.id not in candidate_map or chunk.relevance_score > candidate_map[chunk.id].relevance_score:
                    candidate_map[chunk.id] = chunk

        candidates = list(candidate_map.values())
        if not candidates:
            return []

        # 3. Cross-Encoder precision reranking
        if use_reranker and len(candidates) > 1:
            reranked = reranker.rerank(query=question, chunks=candidates, top_k=top_k)
            return reranked

        # If reranker disabled or not needed, sort by fused score
        candidates.sort(key=lambda c: c.relevance_score, reverse=True)
        return candidates[:top_k]

    def _format_context(self, chunks: List[RetrievedChunk]) -> str:
        """Formats retrieved chunks with precise citation metadata."""
        return CitationEngine.format_context_for_llm(chunks)

    def build_lcel_chain(self) -> Runnable:
        """
        Builds the core LCEL RAG Runnable chain:
        RunnableParallel -> PromptTemplate -> Robust LLM (Mistral/Groq) -> StrOutputParser
        """
        # Ensure LLM runnable chain is initialized
        if llm_service.runnable_chain is None:
            llm_service._init_runnable_chain()

        # Retrieve robust chat model with fallbacks from LLMService
        primary_model = llm_service._build_model(llm_service.provider)
        fallback_models = [
            m for p in ["groq", "mistral"]
            if p != llm_service.provider and (m := llm_service._build_model(p)) is not None
        ]

        if primary_model is None and fallback_models:
            primary_model = fallback_models.pop(0)

        if primary_model is None:
            raise RuntimeError("No active LLM providers configured in settings.")

        robust_model = primary_model.with_fallbacks(fallback_models) if fallback_models else primary_model

        def _extract_chunks(data: Any) -> List[RetrievedChunk]:
            if isinstance(data, dict):
                return data.get("chunks", [])
            return []

        def _extract_question(data: Any) -> str:
            if isinstance(data, dict):
                inputs = data.get("inputs", {})
                if isinstance(inputs, dict):
                    return str(inputs.get("question", ""))
            return ""

        def _extract_system_prompt(data: Any) -> str:
            if isinstance(data, dict):
                inputs = data.get("inputs", {})
                if isinstance(inputs, dict):
                    prompt = inputs.get("system_prompt")
                    if prompt:
                        return str(prompt)
            return SYSTEM_FINANCIAL_RAG_PROMPT

        # Composable LCEL chain with RunnableParallel and RunnableLambda
        chain = (
            RunnableParallel({
                "context": RunnableLambda(_extract_chunks) | RunnableLambda(self._format_context),
                "question": RunnableLambda(_extract_question),
                "system_prompt": RunnableLambda(_extract_system_prompt),
            })
            | self._prompt
            | robust_model
            | self._output_parser
        )
        return chain

    async def ainvoke(
        self,
        question: str,
        where: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None,
        top_k: int = settings.TOP_K_RERANKED,
        use_reranker: bool = True
    ) -> Tuple[str, List[CitationItem], List[RetrievedChunk]]:
        """
        Asynchronously executes the Advanced RAG pipeline.
        Returns:
            Tuple of (answer_text, formatted_citations, raw_retrieved_chunks)
        """
        inputs = {
            "question": question,
            "where": where,
            "system_prompt": system_prompt,
            "top_k": top_k,
            "use_reranker": use_reranker
        }

        # Step 1: Advanced Hybrid Retrieval & Reranking
        chunks = self._retrieve_chunks(inputs)
        citations = CitationEngine.build_citations(chunks, max_citations=4)

        if not chunks:
            if retriever.count() == 0:
                empty_msg = (
                    "Welcome to FinAdvisor! There are currently no financial documents indexed in the system. "
                    "Please upload an annual report, 10-K, or mutual fund factsheet in the Documents tab "
                    "to begin querying grounded financial intelligence."
                )
            else:
                empty_msg = (
                    "No relevant financial context found in the uploaded documents to answer your question. "
                    "Please verify your query or upload the corresponding annual filing."
                )
            return empty_msg, citations, chunks

        # Step 2: Execute LCEL chain
        chain = self.build_lcel_chain()
        answer = await chain.ainvoke({
            "inputs": inputs,
            "chunks": chunks
        })

        return str(answer), citations, chunks


# Singleton pipeline instance
rag_pipeline = FinancialRAGPipeline()
