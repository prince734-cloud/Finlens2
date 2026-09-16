import os
from pathlib import Path
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.app.main import app
from backend.app.database.connection import init_db
from backend.app.rag.loader import FinancialPDFLoader
from backend.app.rag.chunking import FinancialRecursiveChunker
from backend.app.rag.embeddings import embedding_service
from backend.app.rag.retriever import ChromaRetriever, retriever
from backend.app.rag.citations import CitationEngine
from backend.app.rag.chain import rag_pipeline, FinancialRAGPipeline
from data.sample_documents.create_sample_report import create_apple_sample_report


@pytest.fixture(scope="session", autouse=True)
def sample_pdf_path():
    """Generates the test PDF if it doesn't already exist."""
    pdf_path = Path("data/sample_documents/Apple_Inc_FY2024_Annual_Report.pdf")
    if not pdf_path.exists():
        create_apple_sample_report(str(pdf_path))
    return str(pdf_path)


def test_pdf_loader_sections_and_pages(sample_pdf_path):
    """Verifies PyMuPDF loader correctly parses pages, cleans text, and detects financial sections."""
    loader = FinancialPDFLoader()
    pages = loader.load_pdf(sample_pdf_path)

    assert len(pages) == 3
    assert pages[0].page_number == 1
    assert pages[1].page_number == 2
    assert pages[2].page_number == 3

    # Check that text was extracted
    assert "391,035" in pages[0].text
    assert "Consolidated Statements of Operations" in pages[0].section or "Business Overview" in pages[0].section

    # Page 2 should detect MD&A
    assert "Item 7" in pages[1].section or "Management" in pages[1].section
    assert "Services net sales grew 9%" in pages[1].text

    # Page 3 should detect Risk Factors
    assert "Item 1A" in pages[2].section or "Risk Factors" in pages[2].section
    assert "Supply Chain" in pages[2].text


def test_recursive_financial_chunker(sample_pdf_path):
    """Verifies chunking preserves financial metrics and attaches enriched metadata."""
    loader = FinancialPDFLoader()
    pages = loader.load_pdf(sample_pdf_path)

    chunker = FinancialRecursiveChunker(chunk_size=700, chunk_overlap=100)
    chunks = chunker.chunk_pages(
        pages=pages,
        document_id="test-doc-apple-2024",
        document_name="Apple_Inc_FY2024_Annual_Report.pdf",
        company_name="Apple Inc.",
        financial_year=2024
    )

    assert len(chunks) >= 3
    for chunk in chunks:
        assert chunk.document_id == "test-doc-apple-2024"
        assert chunk.document_name == "Apple_Inc_FY2024_Annual_Report.pdf"
        assert chunk.company_name == "Apple Inc."
        assert chunk.financial_year == 2024
        assert chunk.page_number in [1, 2, 3]
        assert chunk.section != ""
        # Context header should be injected for dense vector retrieval
        assert "[Document: Apple_Inc_FY2024_Annual_Report.pdf" in chunk.content


def test_embeddings_service():
    """Verifies 384-dim dense embeddings and semantic similarity."""
    dim = embedding_service.dimension
    assert dim == 384

    v1 = embedding_service.embed_query("Apple annual net sales and total revenue")
    v2 = embedding_service.embed_query("Apple total turnover and product revenues")
    v3 = embedding_service.embed_query("How to make chocolate chip cookies")

    assert len(v1) == 384
    assert len(v2) == 384
    assert len(v3) == 384

    # Dot product of normalized vectors equals cosine similarity
    sim_finance = sum(a * b for a, b in zip(v1, v2))
    sim_unrelated = sum(a * b for a, b in zip(v1, v3))

    assert sim_finance > sim_unrelated
    assert sim_finance > 0.60


def test_chroma_indexing_and_similarity_retrieval(sample_pdf_path):
    """Verifies vector storage and semantic query retrieval."""
    loader = FinancialPDFLoader()
    pages = loader.load_pdf(sample_pdf_path)
    chunker = FinancialRecursiveChunker(chunk_size=700, chunk_overlap=100)
    chunks = chunker.chunk_pages(
        pages=pages,
        document_id="apple-test-id",
        document_name="Apple_Inc_FY2024_Annual_Report.pdf",
        company_name="Apple Inc.",
        financial_year=2024
    )

    retriever.add_chunks(chunks)
    assert retriever.count() >= len(chunks)

    # Query revenue
    results = retriever.query_similar("What was Apple's total net sales in fiscal 2024?", top_k=3)
    assert len(results) > 0
    top_chunk = results[0]
    assert top_chunk.company_name == "Apple Inc."
    assert "391,035" in top_chunk.content or "Total net sales" in top_chunk.content

    # Query risk factors
    risk_results = retriever.query_similar("What are the main risks regarding supply chain?", top_k=3)
    assert len(risk_results) > 0
    risk_chunk = risk_results[0]
    assert "Supply Chain" in risk_chunk.content or "Risk Factors" in risk_chunk.section


def test_citations_engine():
    """Verifies citations are accurately extracted and formatted without fabrication."""
    loader = FinancialPDFLoader()
    pages = loader.load_pdf("data/sample_documents/Apple_Inc_FY2024_Annual_Report.pdf")
    chunker = FinancialRecursiveChunker(chunk_size=700, chunk_overlap=100)
    chunks = chunker.chunk_pages(
        pages=pages,
        document_id="cite-test-id",
        document_name="Apple_Inc_FY2024_Annual_Report.pdf",
        company_name="Apple Inc.",
        financial_year=2024
    )

    retriever.add_chunks(chunks)
    retrieved = retriever.query_similar("What were Apple's operating cash flows?", top_k=2)

    citations = CitationEngine.build_citations(retrieved, max_citations=2)
    assert len(citations) > 0
    assert citations[0].document_name == "Apple_Inc_FY2024_Annual_Report.pdf"
    assert citations[0].page_number in [1, 2, 3]
    assert len(citations[0].excerpt) > 10


@pytest.mark.asyncio
async def test_api_chat_rag_end_to_end():
    """End-to-end test of the /api/v1/chat endpoint with grounded RAG retrieval."""
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/chat",
            json={"message": "What was Apple's total net sales and net income in 2024?"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert data["query_type"] == "document_rag"
        assert len(data["citations"]) > 0
        assert data["citations"][0]["document_name"] == "Apple_Inc_FY2024_Annual_Report.pdf"
        assert "disclaimer" in data


@pytest.mark.asyncio
async def test_lcel_rag_pipeline_execution(sample_pdf_path):
    """Directly verifies the LCEL RAG pipeline (RunnableParallel, Prompt, LLM, Parser)."""
    answer, citations, chunks = await rag_pipeline.ainvoke(
        question="Summarize Apple's cash generated from operations in fiscal 2024",
        where={"company_name": "Apple Inc."}
    )
    assert isinstance(answer, str)
    assert len(answer) > 0
    assert isinstance(citations, list)
    assert len(citations) > 0
    assert citations[0].document_name == "Apple_Inc_FY2024_Annual_Report.pdf"
