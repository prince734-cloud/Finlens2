"""
FinLens — Phase 6 Automated Test Suite
Validates Candidate Generation, Hard Constraint Filtering, Multi-Factor Scoring,
Ranking Order, Grounded Explainability, and Recommendations REST APIs.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.connection import get_db
from backend.app.data.company_data import seed_company_data
from backend.app.data.mutual_fund_data import seed_mutual_fund_data
from backend.app.recommendation.candidate_generator import (
    CandidateAsset,
    generate_candidates,
)
from backend.app.recommendation.filters import apply_hard_filters
from backend.app.recommendation.scoring import (
    score_candidate,
    score_risk_compatibility,
    score_horizon_suitability,
    score_financial_quality,
    score_valuation_and_cost,
    score_goal_alignment,
)
from backend.app.recommendation.ranking import rank_and_explain_candidates
from backend.app.main import app


@pytest.fixture
async def async_client():
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_candidate_generation():
    """Verifies candidate generator extracts and normalizes both companies and funds."""
    async for db in get_db():
        # Ensure seed data is populated
        await seed_company_data(db)
        await seed_mutual_fund_data(db)

        candidates = await generate_candidates(db)
        assert len(candidates) >= 10

        types = {c.asset_type for c in candidates}
        assert "Company" in types
        assert "Mutual Fund" in types

        # Validate candidate schema consistency
        for c in candidates:
            assert c.id is not None
            assert len(c.asset_name) > 0
            assert c.risk_level in ["Low", "Moderate", "High", "Very High"]
            assert c.recommended_horizon in ["Short", "Medium", "Long"]
            assert isinstance(c.financial_metrics, dict)
            assert len(c.source_reference) > 0
        break


@pytest.mark.asyncio
async def test_hard_filters_suitability():
    """Verifies that hard constraint filters eliminate high-risk assets for conservative/short profiles."""
    candidates = [
        CandidateAsset(
            id="c-safe",
            asset_name="Liquid Debt Fund",
            asset_type="Mutual Fund",
            symbol_or_code="LIQUID",
            sector_or_category="Debt - Liquid",
            risk_level="Low",
            recommended_horizon="Short",
            financial_metrics={"expense_ratio": 0.0025, "debt_to_equity": 0.0},
            source_reference="Factsheet"
        ),
        CandidateAsset(
            id="c-risky",
            asset_name="High Beta Semi Stock",
            asset_type="Company",
            symbol_or_code="RISK",
            sector_or_category="Technology",
            risk_level="High",
            recommended_horizon="Long",
            financial_metrics={"debt_to_equity": 1.8, "pe_ratio": 65.0, "roe": 22.0},
            source_reference="Annual Report"
        )
    ]

    # 1. Conservative + Short Horizon: Must reject high-beta equity stock
    passed, audit = apply_hard_filters(
        candidates=candidates,
        user_risk_tolerance="Conservative",
        user_investment_horizon="Short",
        user_goal="Capital preservation"
    )
    passed_ids = [c.id for c in passed]
    assert "c-safe" in passed_ids
    assert "c-risky" not in passed_ids

    # 2. Aggressive + Long Horizon: Must retain high-beta asset
    passed_agg, _ = apply_hard_filters(
        candidates=candidates,
        user_risk_tolerance="Aggressive",
        user_investment_horizon="Long",
        user_goal="Wealth creation"
    )
    agg_ids = [c.id for c in passed_agg]
    assert "c-risky" in agg_ids


def test_deterministic_scoring_bounds_and_repeatability():
    """Validates mathematical score boundaries (0-100) and deterministic repeatability."""
    sample_company = CandidateAsset(
        id="aapl-1",
        asset_name="Apple Inc.",
        asset_type="Company",
        symbol_or_code="AAPL",
        sector_or_category="Technology",
        risk_level="Moderate",
        recommended_horizon="Long",
        financial_metrics={
            "roe": 153.8,
            "roce": 58.2,
            "debt_to_equity": 0.15,
            "operating_cash_flow": 118264000000.0,
            "net_profit": 93736000000.0,
            "pe_ratio": 34.2,
            "revenue_growth": 0.02
        },
        source_reference="FY2024 10-K"
    )

    # Score across multiple profiles
    for risk in ["Conservative", "Moderate", "Aggressive"]:
        for horizon in ["Short", "Medium", "Long"]:
            total, breakdown = score_candidate(
                asset=sample_company,
                user_risk_tolerance=risk,
                user_investment_horizon=horizon,
                user_goal="Wealth creation"
            )
            # Assert boundaries
            assert 0.0 <= total <= 100.0
            assert 0.0 <= breakdown.risk_match_score <= 30.0
            assert 0.0 <= breakdown.horizon_match_score <= 25.0
            assert 0.0 <= breakdown.financial_quality_score <= 25.0
            assert 0.0 <= breakdown.valuation_score <= 10.0
            assert 0.0 <= breakdown.diversification_score <= 10.0

            # Repeatability check
            total_2, _ = score_candidate(
                asset=sample_company,
                user_risk_tolerance=risk,
                user_investment_horizon=horizon,
                user_goal="Wealth creation"
            )
            assert total == total_2, "Scoring function must be strictly deterministic"


def test_ranking_order_and_grounded_explainability():
    """Verifies descending rank ordering and fact-grounded positive/consideration factors."""
    candidates = [
        CandidateAsset(
            id="low-score",
            asset_name="Low Quality Asset",
            asset_type="Company",
            symbol_or_code="LOW",
            sector_or_category="Industrials",
            risk_level="High",
            recommended_horizon="Long",
            financial_metrics={"roe": 2.0, "debt_to_equity": 2.5, "pe_ratio": 70.0},
            source_reference="Report"
        ),
        CandidateAsset(
            id="high-score",
            asset_name="Top Quality Compounding Fund",
            asset_type="Mutual Fund",
            symbol_or_code="PPFC",
            sector_or_category="Flexi Cap",
            risk_level="Moderate",
            recommended_horizon="Medium",
            financial_metrics={
                "return_5yr": 22.4,
                "aum": 72000.0,
                "expense_ratio": 0.0065,
                "exit_load": "1.0% within 365 days",
                "portfolio_holdings": [{"name": "HDFC Bank", "weight": 8.0}] * 5
            },
            source_reference="Factsheet Q4 2024"
        )
    ]

    result = rank_and_explain_candidates(
        candidates=candidates,
        user_risk_tolerance="Moderate",
        user_investment_horizon="Medium",
        user_goal="Wealth creation"
    )

    # 1. Verify descending order
    assert len(result.candidates) == 2
    assert result.candidates[0].match_score >= result.candidates[1].match_score
    assert result.candidates[0].id == "high-score"

    # 2. Verify explainability factors cite real metrics
    top_cand = result.candidates[0]
    assert len(top_cand.positive_factors) >= 2
    assert len(top_cand.considerations) >= 1

    positives_joined = " ".join(top_cand.positive_factors)
    # Audited return should be cited
    assert "22.4%" in positives_joined or "CAGR" in positives_joined
    assert "0.65%" in positives_joined or "fee drag" in positives_joined


@pytest.mark.asyncio
async def test_recommendations_api_endpoints(async_client: AsyncClient):
    """Tests GET /api/v1/recommendations and POST /api/v1/recommendations/evaluate."""
    # 1. GET /api/v1/recommendations
    res = await async_client.get("/api/v1/recommendations")
    assert res.status_code == 200
    data = res.json()
    assert "user_risk_tolerance" in data
    assert "user_investment_horizon" in data
    assert "candidates" in data
    assert len(data["candidates"]) > 0

    first = data["candidates"][0]
    assert "match_score" in first
    assert "score_breakdown" in first
    assert "positive_factors" in first
    assert "considerations" in first
    assert first["match_score"] > 0

    # 2. Test Asset Type filtering on API
    comp_res = await async_client.get("/api/v1/recommendations?asset_type=Company")
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    for c in comp_data["candidates"]:
        assert c["asset_type"] == "Company"

    # 3. POST /api/v1/recommendations/evaluate (What-If Simulation)
    sim_res = await async_client.post(
        "/api/v1/recommendations/evaluate",
        json={
            "risk_tolerance": "Conservative",
            "investment_horizon": "Short",
            "goal": "Capital preservation"
        }
    )
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert sim_data["user_risk_tolerance"] == "Conservative"
    assert sim_data["user_investment_horizon"] == "Short"
    assert len(sim_data["candidates"]) > 0
    # Top asset for short conservative should be a low-risk liquid/debt fund
    top_asset = sim_data["candidates"][0]
    assert top_asset["score_breakdown"]["risk_match_score"] > 0
