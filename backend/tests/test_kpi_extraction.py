"""
Unit and integration tests for FinAdvisor Phase 4: Structured Financial KPI Extraction.

Tests:
1. Financial number parsing and normalization (millions, billions, percentages, negative brackets)
2. Pydantic FinancialKPIModel schema integrity
3. Robust JSON regex repair for LLM outputs
4. Relational database persistence and retrieval
5. KPI API endpoints (/api/v1/kpis, /api/v1/kpis/{document_id})
"""

import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.app.database.connection import get_db, init_db
from backend.app.database.models import Document, FinancialKPI
from backend.app.extraction.kpi_extractor import (
    FinancialKPIModel,
    kpi_extractor,
    normalize_financial_number,
)
from backend.app.main import app


# =====================================================================
# 1. Number Normalization Unit Tests
# =====================================================================

def test_normalize_financial_number():
    """Validates conversion of standard accounting figures into normalized floats."""
    # Millions & Billions
    assert normalize_financial_number("$391,035M") == 391035000000.0
    assert normalize_financial_number("391035 million") == 391035000000.0
    assert normalize_financial_number("$112.5B") == 112500000000.0
    assert normalize_financial_number("2.5 billion") == 2500000000.0
    assert normalize_financial_number("500K") == 500000.0

    # Percentages
    assert normalize_financial_number("8.2%") == 0.082
    assert normalize_financial_number("-3.5%") == -0.035

    # Accounting negative brackets
    assert normalize_financial_number("(5,200)") == -5200.0
    assert normalize_financial_number("-$1,250") == -1250.0

    # Clean numbers & edge cases
    assert normalize_financial_number(12345.67) == 12345.67
    assert normalize_financial_number("123,456") == 123456.0
    assert normalize_financial_number(None) is None
    assert normalize_financial_number("N/A") is None
    assert normalize_financial_number("—") is None


# =====================================================================
# 2. Pydantic Schema Validation Tests
# =====================================================================

def test_financial_kpi_model_schema():
    """Validates FinancialKPIModel adheres strictly to user-specified KPI requirements."""
    sample_data = {
        "company": "Apple Inc.",
        "financial_year": 2024,
        "currency": "USD",
        "revenue": 391035000000.0,
        "net_income": 93736000000.0,
        "operating_income": 123216000000.0,
        "operating_cash_flow": 118264000000.0,
        "total_assets": 364980000000.0,
        "total_liabilities": 308030000000.0,
        "revenue_growth": 0.0202,
        "net_income_growth": -0.0336,
        "growth_drivers": ["Services revenue expansion", "iPhone 16 upgrade cycle", "Wearables adoption"],
        "risk_factors": ["Supply chain concentration", "Foreign exchange volatility", "Regulatory antitrust scrutiny"]
    }

    model = FinancialKPIModel.model_validate(sample_data)
    assert model.company == "Apple Inc."
    assert model.financial_year == 2024
    assert model.revenue == 391035000000.0
    assert len(model.growth_drivers) == 3
    assert len(model.risk_factors) == 3
    assert model.revenue_growth == 0.0202


# =====================================================================
# 3. JSON Parsing & Regex Fallback Tests
# =====================================================================

def test_json_parsing_and_regex_fallback():
    """Tests that LLM responses with markdown fences or minor anomalies parse reliably."""
    raw_markdown_response = """
Here is the extracted financial information:
```json
{
  "company": "Microsoft Corporation",
  "financial_year": 2024,
  "currency": "USD",
  "revenue": 245120000000.0,
  "net_income": 88136000000.0,
  "operating_income": 109433000000.0,
  "operating_cash_flow": 118548000000.0,
  "total_assets": 512163000000.0,
  "total_liabilities": 243686000000.0,
  "revenue_growth": 0.156,
  "net_income_growth": 0.218,
  "growth_drivers": ["Azure cloud growth", "Office 365 commercial", "AI infrastructure"],
  "risk_factors": ["Cybersecurity incidents", "Data center capacity constraints"]
}
```
Hope this helps!
"""
    parsed = kpi_extractor._parse_json_response(
        response_text=raw_markdown_response,
        fallback_company="Microsoft",
        fallback_year=2024
    )
    assert parsed.company == "Microsoft Corporation"
    assert parsed.revenue == 245120000000.0
    assert len(parsed.growth_drivers) == 3


# =====================================================================
# 4. Database Persistence & API Integration Tests
# =====================================================================

@pytest.mark.asyncio
async def test_kpi_database_persistence_and_api():
    """Tests persisting extracted KPIs into the database and fetching via REST API."""
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create a dummy document in DB
        unique_id = str(uuid.uuid4())
        doc_filename = f"Test_Annual_Report_{unique_id[:8]}.pdf"

        # Manually save document and KPI to DB
        async for db in get_db():
            doc = Document(
                id=unique_id,
                filename=doc_filename,
                file_path=f"data/uploads/{doc_filename}",
                file_size_bytes=102400,
                document_type="annual_report",
                company_name="TestCorp",
                financial_year=2024,
                status="indexed",
                chunk_count=5
            )
            db.add(doc)
            await db.commit()

            kpi_model = FinancialKPIModel(
                company="TestCorp",
                financial_year=2024,
                currency="USD",
                revenue=500000000.0,
                net_income=75000000.0,
                operating_income=90000000.0,
                operating_cash_flow=85000000.0,
                total_assets=600000000.0,
                total_liabilities=300000000.0,
                revenue_growth=0.125,
                net_income_growth=0.150,
                growth_drivers=["Product expansion in APAC", "SaaS subscription transition"],
                risk_factors=["Interest rate sensitivity", "Talent retention"]
            )
            await kpi_extractor._save_kpis_to_db(
                document_id=unique_id,
                kpi_data=kpi_model,
                db=db
            )
            break

        # 2. Query GET /api/v1/kpis/{document_id}
        res_single = await client.get(f"/api/v1/kpis/{unique_id}")
        assert res_single.status_code == 200
        single_data = res_single.json()
        assert single_data["company_name"] == "TestCorp"
        assert single_data["revenue"] == 500000000.0
        assert single_data["net_income"] == 75000000.0
        assert single_data["operating_cash_flow"] == 85000000.0
        assert len(single_data["growth_drivers"]) == 2
        assert len(single_data["risk_factors"]) == 2

        # 3. Query GET /api/v1/kpis (All KPIs)
        res_all = await client.get("/api/v1/kpis")
        assert res_all.status_code == 200
        all_data = res_all.json()
        assert any(k["document_id"] == unique_id for k in all_data)


@pytest.mark.asyncio
async def test_extract_kpis_for_document_sync_hybrid_search(monkeypatch):
    """Verifies that kpi_extractor.extract_kpis_for_document calls hybrid search synchronously without 'await list' error."""
    await init_db()

    # Mock llm_service.generate_grounded_answer
    from backend.app.services.llm_service import llm_service
    async def mock_generate(*args, **kwargs):
        return """{
  "company": "Apple Inc.",
  "financial_year": 2024,
  "currency": "USD",
  "revenue": 391035000000.0,
  "net_income": 93736000000.0,
  "operating_income": 123216000000.0,
  "operating_cash_flow": 118264000000.0,
  "total_assets": 364980000000.0,
  "total_liabilities": 308030000000.0,
  "revenue_growth": 0.02,
  "net_income_growth": -0.034,
  "growth_drivers": ["Services revenue expansion", "iPhone 16 demand"],
  "risk_factors": ["Supply chain concentration", "Regulatory scrutiny"]
}"""
    from backend.app.rag.hybrid_search import hybrid_search_engine
    from backend.app.rag.retriever import RetrievedChunk
    import backend.app.extraction.kpi_extractor as kpi_module

    monkeypatch.setattr(kpi_module.llm_service, "generate_grounded_answer", mock_generate)

    def mock_search(*args, **kwargs):
        return [
            RetrievedChunk(
                id="chunk-1",
                content="Total net sales for FY2024 were $391,035M. Net income was $93,736M.",
                document_id="dummy",
                document_name="Sample_Report.pdf",
                company_name="Apple Inc.",
                financial_year=2024,
                page_number=32,
                section="Operations",
                relevance_score=0.98,
                metadata={}
            )
        ]
    monkeypatch.setattr(hybrid_search_engine, "search", mock_search)

    # Create dummy document in DB
    unique_id = str(uuid.uuid4())
    async for db in get_db():
        doc = Document(
            id=unique_id,
            filename="Sample_Report.pdf",
            file_path="data/uploads/Sample_Report.pdf",
            file_size_bytes=1024,
            document_type="annual_report",
            company_name="Apple Inc.",
            financial_year=2024,
            status="indexed",
            chunk_count=1
        )
        db.add(doc)
        await db.commit()

        # Run extract_kpis_for_document
        result = await kpi_extractor.extract_kpis_for_document(document_id=unique_id, db=db)
        assert result.kpi.revenue == 391035000000.0
        assert result.kpi.net_income == 93736000000.0
        assert len(result.kpi.growth_drivers) == 2
        break
