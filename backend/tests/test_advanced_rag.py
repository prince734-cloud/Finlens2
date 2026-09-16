"""
Unit and integration tests for FinAdvisor Phase 3: Advanced RAG Engine.

Tests:
1. Financial-aware BM25 tokenization
2. BM25 sparse index retrieval and metadata filtering
3. Reciprocal Rank Fusion (RRF) scoring algorithm
4. Cross-Encoder precision reranking
5. Financial query rewriting, expansion, and decomposition
6. End-to-end Advanced LCEL RAG execution
"""

from pathlib import Path
import pytest
import pytest_asyncio

from backend.app.rag.hybrid_search import BM25Index, HybridSearchEngine, financial_tokenize, hybrid_search_engine
from backend.app.rag.query_rewriter import FinancialQueryRewriter, query_rewriter
from backend.app.rag.reranker import CrossEncoderReranker, reranker
from backend.app.rag.retriever import RetrievedChunk, retriever
from backend.app.rag.chain import rag_pipeline
from data.sample_documents.create_sample_report import create_apple_sample_report


@pytest.fixture(scope="session", autouse=True)
def ensure_sample_report():
    """Ensures test annual report exists."""
    pdf_path = Path("data/sample_documents/Apple_Inc_FY2024_Annual_Report.pdf")
    if not pdf_path.exists():
        create_apple_sample_report(str(pdf_path))
    return str(pdf_path)


def test_bm25_financial_tokenization():
    """Verifies tokenizer preserves financial values, percentages, and accounting codes."""
    sample_text = "Net sales reached $391,035M, growing 9.2% in FY2024 under Item 1A for AAPL-SEC."
    tokens = financial_tokenize(sample_text)

    assert "$391,035" in tokens or "391,035" in tokens or "$391,035m" in tokens
    assert "9.2%" in tokens or "9.2" in tokens
    assert "item" in tokens
    assert "1a" in tokens
    assert "fy2024" in tokens


def test_bm25_sparse_indexing_and_search():
    """Verifies BM25 index correctly indexes and searches numerical and lexical chunks."""
    index = BM25Index()

    chunk_1 = RetrievedChunk(
        id="chunk-1",
        content="Total consolidated net sales were $391,035 million for fiscal year 2024.",
        document_id="doc-apple",
        document_name="Apple_10K.pdf",
        company_name="Apple Inc.",
        financial_year=2024,
        page_number=1,
        section="Consolidated Statements of Operations",
        relevance_score=1.0,
        metadata={"company_name": "Apple Inc."}
    )

    chunk_2 = RetrievedChunk(
        id="chunk-2",
        content="Item 1A: Risk factors include global supply chain concentration and foreign exchange volatility.",
        document_id="doc-apple",
        document_name="Apple_10K.pdf",
        company_name="Apple Inc.",
        financial_year=2024,
        page_number=3,
        section="Item 1A Risk Factors",
        relevance_score=1.0,
        metadata={"company_name": "Apple Inc."}
    )

    index.add_chunks([chunk_1, chunk_2])
    assert index.count == 2

    # Query exact financial figure
    results = index.search(query="$391,035 net sales", top_k=2)
    assert len(results) > 0
    assert results[0][0].id == "chunk-1"

    # Query risk factors
    results_risk = index.search(query="supply chain concentration volatility", top_k=2)
    assert len(results_risk) > 0
    assert results_risk[0][0].id == "chunk-2"

    # Test metadata filter
    filtered = index.search(query="net sales", top_k=2, where={"company_name": "NonExistent"})
    assert len(filtered) == 0


def test_reciprocal_rank_fusion():
    """Verifies RRF scoring merges dense and sparse rankings deterministically."""
    engine = HybridSearchEngine()

    chunk_a = RetrievedChunk(
        id="chunk-A", content="Chunk A Content", document_id="doc-1",
        document_name="doc.pdf", company_name="Co", financial_year=2024,
        page_number=1, section="Sec A", relevance_score=0.9, metadata={}
    )
    chunk_b = RetrievedChunk(
        id="chunk-B", content="Chunk B Content", document_id="doc-1",
        document_name="doc.pdf", company_name="Co", financial_year=2024,
        page_number=2, section="Sec B", relevance_score=0.8, metadata={}
    )
    chunk_c = RetrievedChunk(
        id="chunk-C", content="Chunk C Content", document_id="doc-1",
        document_name="doc.pdf", company_name="Co", financial_year=2024,
        page_number=3, section="Sec C", relevance_score=0.7, metadata={}
    )

    # Dense ranks: [A, B, C]
    dense_list = [chunk_a, chunk_b, chunk_c]
    # Sparse ranks: [B, A]
    sparse_list = [(chunk_b, 15.0), (chunk_a, 10.0)]

    fused = engine.reciprocal_rank_fusion(
        dense_results=dense_list,
        sparse_results=sparse_list,
        rrf_k=60
    )

    assert len(fused) == 3
    # Both A and B appeared in dense and sparse top-2, so both should have higher scores than C
    c_score = next(c.relevance_score for c in fused if c.id == "chunk-C")
    a_score = next(c.relevance_score for c in fused if c.id == "chunk-A")
    b_score = next(c.relevance_score for c in fused if c.id == "chunk-B")

    assert a_score > c_score
    assert b_score > c_score


def test_cross_encoder_reranker():
    """Verifies Cross-Encoder reorders candidate passages by contextual semantic relevance."""
    query = "What was Apple's annual net sales in 2024?"

    irrelevant_chunk = RetrievedChunk(
        id="chunk-irr",
        content="Directors and executive officers are subject to stock ownership guidelines.",
        document_id="doc-1",
        document_name="doc.pdf",
        company_name="Apple Inc.",
        financial_year=2024,
        page_number=4,
        section="Corporate Governance",
        relevance_score=0.5,
        metadata={}
    )

    relevant_chunk = RetrievedChunk(
        id="chunk-rel",
        content="Total net sales for fiscal year 2024 were $391,035 million, compared to $383,285 million in fiscal year 2023.",
        document_id="doc-1",
        document_name="doc.pdf",
        company_name="Apple Inc.",
        financial_year=2024,
        page_number=1,
        section="Statements of Operations",
        relevance_score=0.5,
        metadata={}
    )

    # Candidate order has irrelevant chunk first
    candidates = [irrelevant_chunk, relevant_chunk]

    reranked = reranker.rerank(query=query, chunks=candidates, top_k=2)

    assert len(reranked) == 2
    # The relevant chunk must be promoted to the top position
    assert reranked[0].id == "chunk-rel"
    assert reranked[0].relevance_score > reranked[1].relevance_score


def test_query_rewriter_and_decomposition():
    """Verifies domain expansion and composite query decomposition."""
    rewriter = FinancialQueryRewriter()

    # 1. Term expansion
    expanded = rewriter.expand_terms("What was reported in the P&L and MD&A?")
    assert "Statements of Operations" in expanded or "Income Statement" in expanded
    assert "Management's Discussion" in expanded or "Item 7" in expanded

    # 2. Decomposition
    compound_query = "What was Apple's 2024 revenue growth and what are its key supply chain risks?"
    sub_queries = rewriter.decompose(compound_query)
    assert len(sub_queries) == 2
    assert "revenue" in sub_queries[0].lower() or "sales" in sub_queries[0].lower()
    assert "risk" in sub_queries[1].lower()

    # 3. Full rewrite and expand
    retrieval_queries = rewriter.rewrite_and_expand(compound_query)
    assert len(retrieval_queries) >= 2
    assert compound_query in retrieval_queries


@pytest.mark.asyncio
async def test_end_to_end_advanced_rag_pipeline(ensure_sample_report):
    """Verifies complete Phase 3 execution: query rewrite -> hybrid search -> rerank -> LLM answer."""
    # Ensure sample report is ingested in ChromaDB and BM25
    hybrid_search_engine.sync_with_chroma()

    query = "What was Apple's total net sales in fiscal 2024?"
    answer, citations, chunks = await rag_pipeline.ainvoke(
        question=query,
        top_k=3,
        use_reranker=True
    )

    assert len(answer) > 20
    assert len(chunks) > 0
    assert len(citations) > 0

    # Citations must be grounded with page numbers and valid excerpts
    for citation in citations:
        assert citation.page_number >= 1
        assert len(citation.excerpt) > 10
        assert citation.document_name != ""
