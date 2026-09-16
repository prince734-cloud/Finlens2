"""
Unit and integration tests for FinLens Phase 5:
1. User Investment Profile CRUD (GET, POST, PUT, validation)
2. Company Research Data Layer (seed, list, search, sector filter, upsert)
3. Mutual Fund Research Data Layer (seed, list, category filter, risk filter, upsert)
"""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.database.connection import get_db, init_db
from backend.app.data.company_data import seed_company_data
from backend.app.data.mutual_fund_data import seed_mutual_fund_data
from backend.app.main import app


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Initializes database tables before running tests."""
    await init_db()


# =====================================================================
# 1. Investment Profile CRUD Tests
# =====================================================================

@pytest.mark.asyncio
async def test_investment_profile_lifecycle():
    """Tests creating, fetching, and updating an investor profile with validation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create Profile
        payload = {
            "investment_amount": 750000.0,
            "monthly_investment_amount": 30000.0,
            "risk_tolerance": "High",
            "investment_horizon": "Long",
            "goal": "Wealth creation"
        }
        res_create = await client.post("/api/v1/profile", json=payload)
        assert res_create.status_code == 201
        created = res_create.json()
        assert created["investment_amount"] == 750000.0
        assert created["risk_tolerance"] == "High"

        # 2. Fetch Profile
        res_get = await client.get("/api/v1/profile")
        assert res_get.status_code == 200
        fetched = res_get.json()
        assert fetched["investment_amount"] == 750000.0
        assert fetched["goal"] == "Wealth creation"

        # 3. Update Profile via PUT
        update_payload = {
            "investment_amount": 1000000.0,
            "monthly_investment_amount": 50000.0,
            "risk_tolerance": "Moderate",
            "investment_horizon": "Medium",
            "goal": "Capital preservation"
        }
        res_put = await client.put("/api/v1/profile", json=update_payload)
        assert res_put.status_code == 200
        updated = res_put.json()
        assert updated["investment_amount"] == 1000000.0
        assert updated["risk_tolerance"] == "Moderate"
        assert updated["goal"] == "Capital preservation"

        # 4. Invalid risk category validation
        invalid_payload = {
            "investment_amount": 50000.0,
            "monthly_investment_amount": 0.0,
            "risk_tolerance": "SuperHigh",  # Invalid
            "investment_horizon": "Short",
            "goal": "Income"
        }
        res_invalid = await client.post("/api/v1/profile", json=invalid_payload)
        assert res_invalid.status_code == 400


# =====================================================================
# 2. Company Research Data Layer Tests
# =====================================================================

@pytest.mark.asyncio
async def test_company_research_layer():
    """Tests company fundamental data seeding, listing, searching, and upserting."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Trigger research seed
        res_seed = await client.post("/api/v1/research/seed")
        assert res_seed.status_code == 200

        # 2. List all companies
        res_list = await client.get("/api/v1/research/companies")
        assert res_list.status_code == 200
        companies = res_list.json()
        assert len(companies) >= 4
        symbols = [c["symbol"] for c in companies]
        assert "AAPL" in symbols
        assert "MSFT" in symbols

        # 3. Sector filter
        res_tech = await client.get("/api/v1/research/companies?sector=Technology")
        assert res_tech.status_code == 200
        tech_companies = res_tech.json()
        assert all("Technology" in c["sector"] for c in tech_companies)

        # 4. Search filter
        res_search = await client.get("/api/v1/research/companies?search=Apple")
        assert res_search.status_code == 200
        search_res = res_search.json()
        assert len(search_res) == 1
        assert search_res[0]["symbol"] == "AAPL"

        # 5. Fetch single company by ticker
        res_single = await client.get("/api/v1/research/companies/AAPL")
        assert res_single.status_code == 200
        aapl = res_single.json()
        assert aapl["name"] == "Apple Inc."
        assert len(aapl["metrics"]) >= 1
        m2024 = next(m for m in aapl["metrics"] if m["fiscal_year"] == 2024)
        assert m2024["revenue"] == 391035000000.0
        assert m2024["net_profit"] == 93736000000.0
        assert m2024["pe_ratio"] == 34.2

        # 6. Dynamic update of company data (future-proof data layer requirement)
        new_company_payload = {
            "symbol": "AMZN",
            "name": "Amazon.com Inc.",
            "sector": "Consumer Discretionary",
            "industry": "Internet Retail",
            "description": "E-commerce and cloud computing giant.",
            "metrics": [
                {
                    "fiscal_year": 2024,
                    "revenue": 574785000000.0,
                    "revenue_growth": 0.118,
                    "net_profit": 30425000000.0,
                    "profit_growth": 0.85,
                    "roe": 0.19,
                    "roce": 0.17,
                    "debt_to_equity": 0.72,
                    "operating_cash_flow": 84946000000.0,
                    "pe_ratio": 41.5,
                    "market_cap": 2000000000000.0
                }
            ]
        }
        res_upsert = await client.post("/api/v1/research/companies", json=new_company_payload)
        assert res_upsert.status_code == 201
        upserted = res_upsert.json()
        assert upserted["symbol"] == "AMZN"
        assert len(upserted["metrics"]) == 1


# =====================================================================
# 3. Mutual Fund Research Data Layer Tests
# =====================================================================

@pytest.mark.asyncio
async def test_mutual_fund_research_layer():
    """Tests mutual fund factsheet data seeding, listing, category and risk filters."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. List mutual funds
        res_funds = await client.get("/api/v1/research/mutual-funds")
        assert res_funds.status_code == 200
        funds = res_funds.json()
        assert len(funds) >= 4

        # 2. Category filter
        res_flexi = await client.get("/api/v1/research/mutual-funds?category=Flexi%20Cap")
        assert res_flexi.status_code == 200
        flexi_funds = res_flexi.json()
        assert any("Parag Parikh" in f["fund_name"] for f in flexi_funds)

        # 3. Risk level filter
        res_low_risk = await client.get("/api/v1/research/mutual-funds?risk_level=Low")
        assert res_low_risk.status_code == 200
        low_funds = res_low_risk.json()
        assert len(low_funds) >= 1
        assert any(m["risk_level"] == "Low" for f in low_funds for m in f["metrics"])

        # 4. Check holdings and factsheet metrics
        ppfc = next(f for f in funds if "Parag Parikh" in f["fund_name"])
        assert len(ppfc["metrics"]) == 1
        metric = ppfc["metrics"][0]
        assert metric["aum"] > 0
        assert metric["return_3yr"] > 0
        assert len(metric["portfolio_holdings"]) >= 3
