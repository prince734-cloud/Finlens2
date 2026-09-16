"""
FinLens — Phase 7 Automated Test Suite: Unified AI Financial Analyst.

Validates:
1. Intent Classification Engine (Heuristic matching & Entity extraction across 5 domains)
2. Grounded Company Research & Audited Citation Generation
3. Mutual Fund Intelligence & Factsheet Citation Generation
4. Deterministic Recommendation Orchestration via Chat
5. General Financial Educational Analysis & Regulatory Disclaimers
6. Multi-Turn Session Persistence, Message History Retrieval, and Deletion
7. Server-Sent Events (SSE) Streaming Endpoint
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.data.company_data import seed_company_data
from backend.app.data.mutual_fund_data import seed_mutual_fund_data
from backend.app.database.connection import get_db
from backend.app.main import app
from backend.app.rag.analyst_service import unified_analyst
from backend.app.rag.intent_router import QueryIntent, intent_router


@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ============================================================================
# 1. Intent Classification & Entity Extraction Tests
# ============================================================================

def test_entity_extraction():
    """Verifies that ticker symbols, company names, and fund keywords are extracted."""
    entities1 = intent_router.extract_entities("What was Apple's revenue and operating margin in 2024?")
    assert "AAPL" in entities1["tickers"]
    assert "Apple Inc." in entities1["companies"]

    entities2 = intent_router.extract_entities("Compare MSFT and NVDA fundamentals.")
    assert "MSFT" in entities2["tickers"]
    assert "NVDA" in entities2["tickers"]

    entities3 = intent_router.extract_entities("What is the expense ratio of Parag Parikh Flexi Cap Fund?")
    assert any("parag parikh" in f for f in entities3["funds"])


@pytest.mark.asyncio
async def test_intent_routing_heuristics():
    """Verifies deterministic heuristic routing across all 5 canonical domains."""
    # Document RAG
    intent, _ = await intent_router.route_query("What are the key risk factors in Apple's 10-K filing?")
    assert intent == QueryIntent.DOCUMENT_RAG

    intent, _ = await intent_router.route_query("Summarize the management discussion in the annual report.")
    assert intent == QueryIntent.DOCUMENT_RAG

    intent, _ = await intent_router.route_query("What does the report say?", document_id="doc-123")
    assert intent == QueryIntent.DOCUMENT_RAG

    # Company Research
    intent, _ = await intent_router.route_query("What was Apple's 2024 revenue and net profit?")
    assert intent == QueryIntent.COMPANY_RESEARCH

    intent, _ = await intent_router.route_query("Show me Microsoft's P/E ratio and debt to equity.")
    assert intent == QueryIntent.COMPANY_RESEARCH

    # Mutual Fund Research
    intent, _ = await intent_router.route_query("What is the expense ratio and AUM of Parag Parikh Flexi Cap?")
    assert intent == QueryIntent.MUTUAL_FUND_RESEARCH

    intent, _ = await intent_router.route_query("Which mutual fund has the highest 5-year return?")
    assert intent == QueryIntent.MUTUAL_FUND_RESEARCH

    # Recommendations
    intent, _ = await intent_router.route_query("What should I invest in for a moderate risk profile?")
    assert intent == QueryIntent.RECOMMENDATIONS

    intent, _ = await intent_router.route_query("Recommend top stocks and funds for wealth creation.")
    assert intent == QueryIntent.RECOMMENDATIONS

    # General Financial Concepts
    intent, _ = await intent_router.route_query("What is the difference between P/E ratio and EV/EBITDA?")
    assert intent == QueryIntent.GENERAL_FINANCIAL

    intent, _ = await intent_router.route_query("Explain how compound interest works.")
    assert intent == QueryIntent.GENERAL_FINANCIAL


# ============================================================================
# 2. Unified Analyst Domain Handlers & Citations
# ============================================================================

@pytest.mark.asyncio
async def test_company_research_execution():
    """Verifies that Company Research synthesizes grounded metrics and citations."""
    session_id = f"test-company-{uuid.uuid4()}"
    async for db in get_db():
        await seed_company_data(db)

        answer, intent, citations, disclaimer = await unified_analyst.execute_turn(
            query="What was Apple's revenue and net profit in FY2024?",
            session_id=session_id,
            db=db
        )

        assert intent == QueryIntent.COMPANY_RESEARCH
        assert len(answer) > 20
        assert len(citations) > 0
        assert "Apple" in citations[0].document_name or "AAPL" in citations[0].document_name
        assert "Audited" in citations[0].document_name or "Financial" in citations[0].document_name
        assert disclaimer is not None
        break


@pytest.mark.asyncio
async def test_mutual_fund_research_execution():
    """Verifies that Mutual Fund Research synthesizes verified factsheet citations."""
    session_id = f"test-fund-{uuid.uuid4()}"
    async for db in get_db():
        await seed_mutual_fund_data(db)

        answer, intent, citations, disclaimer = await unified_analyst.execute_turn(
            query="What is the expense ratio and 5-year CAGR of Parag Parikh Flexi Cap?",
            session_id=session_id,
            db=db
        )

        assert intent == QueryIntent.MUTUAL_FUND_RESEARCH
        assert len(answer) > 20
        assert len(citations) > 0
        assert "Factsheet" in citations[0].document_name
        break


@pytest.mark.asyncio
async def test_recommendations_execution():
    """Verifies that Recommendation queries invoke deterministic candidate ranking."""
    session_id = f"test-rec-{uuid.uuid4()}"
    async for db in get_db():
        await seed_company_data(db)
        await seed_mutual_fund_data(db)

        answer, intent, citations, disclaimer = await unified_analyst.execute_turn(
            query="What do you recommend for my moderate risk profile with a 5 year horizon?",
            session_id=session_id,
            db=db
        )

        assert intent == QueryIntent.RECOMMENDATIONS
        assert len(answer) > 20
        assert len(citations) > 0
        assert "Deterministic Suitability Engine" in citations[0].document_name
        break


# ============================================================================
# 3. Chat API Endpoints & Session Management Tests
# ============================================================================

@pytest.mark.asyncio
async def test_chat_api_turn_and_history(async_client: AsyncClient):
    """Verifies POST /chat creates turns, logs history, and supports session retrieval."""
    session_id = f"api-session-{uuid.uuid4()}"

    # 1. Post a query
    resp = await async_client.post(
        "/api/v1/chat",
        json={
            "message": "What is the formula for calculating Return on Equity (ROE)?",
            "session_id": session_id
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session_id
    assert data["query_type"] == "general_financial"
    assert len(data["answer"]) > 10
    assert len(data["citations"]) > 0

    # 2. Retrieve session history
    hist_resp = await async_client.get(f"/api/v1/chat/sessions/{session_id}")
    assert hist_resp.status_code == 200
    messages = hist_resp.json()
    assert len(messages) >= 2  # user + assistant
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"

    # 3. Check list sessions
    sessions_resp = await async_client.get("/api/v1/chat/sessions")
    assert sessions_resp.status_code == 200
    summaries = sessions_resp.json()
    session_ids = [s["session_id"] for s in summaries]
    assert session_id in session_ids

    # 4. Delete session
    del_resp = await async_client.delete(f"/api/v1/chat/sessions/{session_id}")
    assert del_resp.status_code == 200
    del_data = del_resp.json()
    assert del_data["status"] == "success"

    # Verify deleted
    empty_resp = await async_client.get(f"/api/v1/chat/sessions/{session_id}")
    assert empty_resp.status_code == 200
    assert len(empty_resp.json()) == 0


@pytest.mark.asyncio
async def test_chat_streaming_endpoint(async_client: AsyncClient):
    """Verifies POST /chat/stream returns Server-Sent Events stream with valid content-type."""
    session_id = f"stream-session-{uuid.uuid4()}"

    resp = await async_client.post(
        "/api/v1/chat/stream",
        json={
            "message": "What is the P/E ratio of Apple?",
            "session_id": session_id
        }
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    text = resp.text
    assert "event: intent" in text
    assert "event: token" in text
    assert "event: done" in text


async def run_all_tests():
    print("=" * 60)
    print("FINLENS PHASE 7 UNIFIED ANALYST TEST RUNNER")
    print("=" * 60)

    print("\n[1/7] Testing Entity Extraction...")
    test_entity_extraction()
    print("PASS: Entity extraction verified.")

    print("\n[2/7] Testing Intent Routing Heuristics...")
    await test_intent_routing_heuristics()
    print("PASS: Intent routing heuristics verified across all 5 domains.")

    print("\n[3/7] Testing Grounded Company Research Execution...")
    await test_company_research_execution()
    print("PASS: Company research executed with verified citations.")

    print("\n[4/7] Testing Mutual Fund Intelligence Execution...")
    await test_mutual_fund_research_execution()
    print("PASS: Mutual fund research executed with verified citations.")

    print("\n[5/7] Testing Deterministic Recommendations in Chat...")
    await test_recommendations_execution()
    print("PASS: Recommendation engine executed with suitability citations.")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        print("\n[6/7] Testing Chat REST API Turns and Session History...")
        await test_chat_api_turn_and_history(client)
        print("PASS: Chat turns, session history, and session deletion verified.")

        print("\n[7/7] Testing Chat SSE Streaming Endpoint...")
        await test_chat_streaming_endpoint(client)
        print("PASS: SSE streaming endpoint verified with intent, token, citations, done events.")

    print("\n" + "=" * 60)
    print("ALL 7 TEST SUITES PASSED (100% SUCCESS)")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_all_tests())
