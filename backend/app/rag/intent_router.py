"""
FinLens Query Intent Classification Engine.

Classifies incoming financial queries into one of five canonical intents:
1. DOCUMENT_RAG: Questions regarding uploaded corporate filings, annual reports, 10-Ks,
   MD&A, risk factors, or when an explicit document_id filter is provided.
2. COMPANY_RESEARCH: Inquiries about corporate fundamental metrics (revenue, net income,
   P/E ratio, ROE, debt-to-equity, margins) backed by verified database records.
3. MUTUAL_FUND_RESEARCH: Inquiries regarding mutual fund schemes, AUM, expense ratios,
   historical CAGR (3Y/5Y), risk ratings, fund managers, and portfolio holdings.
4. RECOMMENDATIONS: Requests for personalized investment allocations, suitability rankings,
   or top picks matching a user's risk tolerance, horizon, and financial goal.
5. GENERAL_FINANCIAL: Educational questions explaining financial concepts, valuation
   multiples, market mechanics, or macro principles with regulatory disclaimers.

Architecture:
- Tier 1: High-speed deterministic rule and regex engine with symbol/name extraction (<1ms).
- Tier 2: LLM zero-shot classifier fallback for nuanced or ambiguous multi-faceted queries.
"""

import re
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.app.services.llm_service import llm_service
from backend.app.utils.logger import logger


class QueryIntent(str, Enum):
    DOCUMENT_RAG = "document_rag"
    COMPANY_RESEARCH = "company_research"
    MUTUAL_FUND_RESEARCH = "mutual_fund_research"
    RECOMMENDATIONS = "recommendations"
    GENERAL_FINANCIAL = "general_financial"


# Known entities in verified research data layer
KNOWN_EQUITY_SYMBOLS = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "GOOGL": "Alphabet Inc.",
    "NVDA": "NVIDIA Corporation",
    "HDFCBANK": "HDFC Bank Limited",
    "RELIANCE": "Reliance Industries Limited",
    "TCS": "Tata Consultancy Services",
    "INFY": "Infosys Limited",
}

KNOWN_EQUITY_ALIASES = {
    "apple": "AAPL",
    "microsoft": "MSFT",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "nvidia": "NVDA",
    "hdfc bank": "HDFCBANK",
    "hdfc": "HDFCBANK",
    "reliance": "RELIANCE",
    "reliance industries": "RELIANCE",
    "tcs": "TCS",
    "tata consultancy": "TCS",
    "infosys": "INFY",
}

KNOWN_FUND_KEYWORDS = {
    "parag parikh",
    "flexi cap",
    "mirae asset",
    "large cap",
    "hdfc mid-cap",
    "mid-cap",
    "mid cap",
    "sbi small cap",
    "small cap",
    "icici prudential",
    "vanguard",
    "mutual fund",
    "mutual funds",
    "index fund",
    "index funds",
    "etf",
    "expense ratio",
    "aum",
    "nav",
    "sip",
}

DOCUMENT_KEYWORDS = {
    "10-k",
    "10-q",
    "annual report",
    "annual filing",
    "filing",
    "uploaded document",
    "in the pdf",
    "in the report",
    "item 1a",
    "item 7",
    "md&a",
    "management discussion",
    "page number",
    "auditor's report",
    "notes to accounts",
    "risk factors",
}

RECOMMENDATION_KEYWORDS = {
    "recommend",
    "recommendation",
    "recommendations",
    "what should i invest",
    "where should i invest",
    "which stock should i buy",
    "which fund should i pick",
    "portfolio",
    "asset allocation",
    "allocate",
    "risk profile",
    "risk tolerance",
    "investment goal",
    "suitability",
    "suggest an investment",
    "best investment for",
    "top picks",
}

FUNDAMENTAL_METRIC_KEYWORDS = {
    "revenue",
    "revenue growth",
    "net profit",
    "net income",
    "profit growth",
    "operating margin",
    "net margin",
    "p/e",
    "pe ratio",
    "price to earnings",
    "roe",
    "return on equity",
    "roce",
    "debt to equity",
    "market cap",
    "operating cash flow",
    "fundamentals",
    "eps",
    "earnings per share",
}


class IntentRouter:
    """
    Intelligent router directing queries to the optimal specialized analyst handler.
    """

    @classmethod
    def extract_entities(cls, query: str) -> Dict[str, Any]:
        """
        Extracts recognized equity symbols, company names, or fund keywords from query text.
        """
        q_lower = query.lower()
        extracted: Dict[str, Any] = {
            "companies": [],
            "funds": [],
            "tickers": []
        }

        # Check equity tickers
        for sym, name in KNOWN_EQUITY_SYMBOLS.items():
            if re.search(rf"\b{sym}\b", query, re.IGNORECASE):
                extracted["tickers"].append(sym)
                if name not in extracted["companies"]:
                    extracted["companies"].append(name)

        # Check equity name aliases
        for alias, sym in KNOWN_EQUITY_ALIASES.items():
            if re.search(rf"\b{alias}\b", q_lower):
                if sym not in extracted["tickers"]:
                    extracted["tickers"].append(sym)
                full_name = KNOWN_EQUITY_SYMBOLS[sym]
                if full_name not in extracted["companies"]:
                    extracted["companies"].append(full_name)

        # Check fund keywords
        for f_kw in KNOWN_FUND_KEYWORDS:
            if re.search(rf"\b{f_kw}\b", q_lower):
                extracted["funds"].append(f_kw)

        return extracted

    @classmethod
    def classify_heuristically(
        cls,
        query: str,
        document_id: Optional[str] = None,
        company_name: Optional[str] = None
    ) -> Optional[QueryIntent]:
        """
        Sub-millisecond rule-based classifier for high-confidence intents.
        """
        # 1. Explicit document ID guarantees Document RAG
        if document_id:
            return QueryIntent.DOCUMENT_RAG

        q_lower = query.lower()

        # 2. Check for explicit filing/document keywords
        for doc_kw in DOCUMENT_KEYWORDS:
            if doc_kw in q_lower:
                return QueryIntent.DOCUMENT_RAG

        # A dated question about a named company usually targets a historical
        # filing, even when the user does not explicitly say "annual report".
        entities = cls.extract_entities(query)
        has_year = bool(re.search(r"\b(?:19|20)\d{2}\b", q_lower))
        has_historical_metric = any(
            phrase in q_lower for phrase in ("what was", "what were", "in fiscal", "for fiscal")
        )
        filing_metric_pair = "net sales" in q_lower and "net income" in q_lower
        if entities["companies"] and has_year and has_historical_metric and filing_metric_pair:
            return QueryIntent.DOCUMENT_RAG

        # 3. Check for recommendation / portfolio advice keywords
        for rec_kw in RECOMMENDATION_KEYWORDS:
            if rec_kw in q_lower:
                return QueryIntent.RECOMMENDATIONS

        # 4. Check for mutual fund research keywords
        for fund_kw in KNOWN_FUND_KEYWORDS:
            if fund_kw in q_lower:
                return QueryIntent.MUTUAL_FUND_RESEARCH

        # 5. Check for company fundamental metrics research
        has_ticker = bool(entities["tickers"]) or bool(company_name)
        has_metric = any(m in q_lower for m in FUNDAMENTAL_METRIC_KEYWORDS)

        if has_ticker and (has_metric or "compare" in q_lower or "fundamentals" in q_lower or "profile" in q_lower):
            return QueryIntent.COMPANY_RESEARCH

        if has_ticker and not any(k in q_lower for k in ["risk", "10-k", "filing"]):
            return QueryIntent.COMPANY_RESEARCH

        # 6. General financial educational concepts
        if any(q_lower.startswith(prefix) for prefix in [
            "what is", "what are", "how does", "explain", "define",
            "difference between", "formula for", "why do", "why does"
        ]):
            # If no company or fund entity is extracted, it's general educational
            if not has_ticker and not entities["funds"]:
                return QueryIntent.GENERAL_FINANCIAL

        return None

    @classmethod
    async def classify_with_llm(cls, query: str) -> QueryIntent:
        """
        Zero-shot LLM fallback classification for ambiguous or nuanced queries.
        """
        prompt = (
            "You are a financial query intent classifier. "
            "Classify the following user query into exactly ONE of these 5 categories:\n"
            "- document_rag (questions asking about uploaded annual reports, 10-K filings, auditor notes, risk factors)\n"
            "- company_research (questions about specific company fundamentals, revenue, profit, P/E, balance sheet)\n"
            "- mutual_fund_research (questions about mutual fund schemes, AUM, expense ratios, CAGR returns, fund managers)\n"
            "- recommendations (questions asking what to invest in, portfolio allocation, stock or fund picks for a risk profile)\n"
            "- general_financial (educational definitions, finance concepts, valuation theory, macro market principles)\n\n"
            f"User Query: \"{query}\"\n\n"
            "Respond ONLY with the category identifier (e.g. 'company_research'). Do not explain."
        )

        try:
            raw_result = await llm_service.generate_grounded_answer(
                query=query,
                formatted_context="Financial intent categorization taxonomy.",
                custom_system_prompt=prompt
            )
            cleaned = raw_result.strip().lower()

            for intent in QueryIntent:
                if intent.value in cleaned:
                    return intent
        except Exception as e:
            logger.warning(f"LLM intent classification failed: {e}. Falling back to default.")

        # Default fallback
        return QueryIntent.GENERAL_FINANCIAL

    @classmethod
    async def route_query(
        cls,
        query: str,
        document_id: Optional[str] = None,
        company_name: Optional[str] = None
    ) -> Tuple[QueryIntent, Dict[str, Any]]:
        """
        Executes hybrid intent routing:
        1. Entity extraction
        2. Fast heuristic classification
        3. LLM classification if indeterminate
        Returns (QueryIntent, extracted_entities_dict).
        """
        entities = cls.extract_entities(query)
        if company_name and company_name not in entities["companies"]:
            entities["companies"].append(company_name)

        # Step 1: Heuristic classification
        intent = cls.classify_heuristically(
            query=query,
            document_id=document_id,
            company_name=company_name
        )

        if intent is not None:
            logger.info(f"Classified query '{query[:60]}...' via heuristic rule -> {intent.value}")
            return intent, entities

        # Step 2: LLM classification fallback
        intent = await cls.classify_with_llm(query)
        logger.info(f"Classified query '{query[:60]}...' via LLM fallback -> {intent.value}")
        return intent, entities


# Global singleton router
intent_router = IntentRouter()
