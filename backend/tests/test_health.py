import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.config import settings
from backend.app.database.connection import check_db_health, init_db
from backend.app.main import app


@pytest.mark.asyncio
async def test_app_config():
    """Validates configuration parameters."""
    assert settings.APP_NAME is not None
    assert "FinLens" in settings.APP_NAME
    assert settings.PORT == 8000
    assert settings.VECTOR_STORE_BACKEND in ["chroma", "pgvector"]


@pytest.mark.asyncio
async def test_database_health():
    """Validates database schema creation and health probe."""
    await init_db()
    is_healthy = await check_db_health()
    assert is_healthy is True


@pytest.mark.asyncio
async def test_health_api_endpoint():
    """Validates the GET /api/v1/health endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database_connected"] is True
        assert "active_llm_provider" in data
        assert "disclaimer" in data


@pytest.mark.asyncio
async def test_profile_api_crud():
    """Validates creating and retrieving an investment profile."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create or update profile
        profile_payload = {
            "investment_amount": 500000.0,
            "monthly_investment_amount": 25000.0,
            "risk_tolerance": "Moderate",
            "investment_horizon": "Medium",
            "goal": "Wealth creation"
        }
        create_res = await client.post("/api/v1/profile", json=profile_payload)
        assert create_res.status_code == 201
        created_data = create_res.json()
        assert created_data["investment_amount"] == 500000.0
        assert created_data["risk_tolerance"] == "Moderate"

        # Fetch profile
        get_res = await client.get("/api/v1/profile")
        assert get_res.status_code == 200
        fetched_data = get_res.json()
        assert fetched_data["id"] == created_data["id"]
        assert fetched_data["goal"] == "Wealth creation"


@pytest.mark.asyncio
async def test_recommendations_endpoint_contract():
    """Validates the recommendations schema contract."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/recommendations")
        assert response.status_code == 200
        data = response.json()
        assert "candidates" in data
        assert len(data["candidates"]) > 0
        candidate = data["candidates"][0]
        assert "match_score" in candidate
        assert "positive_factors" in candidate
        assert "considerations" in candidate
        assert "score_breakdown" in candidate
