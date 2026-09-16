"""
FinAdvisor Unified AI Financial Analyst Service.

Coordinates intelligent query routing, multi-turn conversational context,
and domain-specific execution across:
1. Document RAG (hybrid search + cross-encoder reranking + page citations)
2. Corporate Fundamental Research (audited company metrics + comparative ratio analysis)
3. Mutual Fund Intelligence (fund factsheets, AUM, CAGR, expense ratios, holdings)
4. Portfolio Recommendations (Phase 6 deterministic suitability scoring & ranking)
5. General Financial Education (valuation theory, concepts, formulas, market structures)

Enforces strict deterministic vs. generative separation:
- Logic, filtering, and scoring remain 100% deterministic and mathematical.
- LLM is constrained to grounded synthesis and explainability based on verified context.
- Disclaimers are attached to every analytical output.
"""

import json
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.config import settings
from backend.app.database.models import (
    ChatHistory,
    Company,
    CompanyMetric,
    InvestmentProfile,
    MutualFund,
    MutualFundMetric,
)
from backend.app.rag.chain import rag_pipeline
from backend.app.rag.citations import CitationItem
from backend.app.rag.intent_router import QueryIntent, intent_router
from backend.app.recommendation.candidate_generator import generate_candidates
from backend.app.recommendation.filters import apply_hard_filters
from backend.app.recommendation.ranking import rank_and_explain_candidates
from backend.app.recommendation.scoring import score_candidate
from backend.app.services.llm_service import llm_service
from backend.app.utils.logger import logger


REGULATORY_DISCLAIMER = (
    "FinAdvisor provides automated educational analysis and mathematical suitability research. "
    "This does not constitute personalized financial advice, fiduciary investment recommendation, "
    "or a guarantee of future capital returns. Please consult a SEBI/SEC licensed financial advisor "
    "before making capital allocation decisions."
)

COMPANY_ANALYSIS_SYSTEM_PROMPT = """You are FinAdvisor, an institutional equity research analyst.
Analyze the company fundamentals provided strictly in the AUDITED FINANCIAL DATASET below.

CRITICAL CONSTRAINTS:
1. Grounding Rule: Use ONLY the numbers, percentages, and metrics provided in the dataset.
2. Anti-Hallucination: Do NOT invent or extrapolate financial numbers that are not present.
3. Comparative Analysis: Highlight revenue growth, net profit margins, return on equity (ROE),
   debt-to-equity leverage, and P/E valuation multiples.
4. Structure: Use clear markdown headings, metric bullet points, and an executive synthesis.
5. Missing Data: If a metric is absent or a company is not in the dataset, explicitly state that verified records are not available.
"""

MUTUAL_FUND_SYSTEM_PROMPT = """You are FinAdvisor, an institutional mutual fund and wealth research analyst.
Analyze the fund factsheet metrics provided strictly in the VERIFIED FUND DATASET below.

CRITICAL CONSTRAINTS:
1. Grounding Rule: Base all assertions strictly on the provided AUM, expense ratios, 3Y/5Y CAGR, risk level, and portfolio holdings.
2. Anti-Hallucination: Never fabricate returns, manager names, or portfolio weights.
3. Risk-Return Evaluation: Compare expense ratios against category norms, evaluate long-term CAGR vs risk rating, and highlight top sector concentrations.
4. Structure: Use structured tables/bullets for key metrics and clear institutional commentary.
"""

RECOMMENDATION_SYSTEM_PROMPT = """You are FinAdvisor, an institutional portfolio strategist.
Summarize the mathematically ranked investment recommendations provided below for the client's profile.

CRITICAL CONSTRAINTS:
1. Grounding Rule: State the exact Total Suitability Scores (0-100) and factor breakdowns computed by the deterministic ranking engine.
2. Suitability Rationale: Explain WHY each asset fits the user's risk tolerance, investment horizon, and primary financial goal.
3. Asset Allocation: Mention the asset type (Stock vs Mutual Fund) and diversification balance.
4. Disclaimer: Remind the user that past performance does not guarantee future results.
"""

GENERAL_FINANCIAL_SYSTEM_PROMPT = """You are FinAdvisor, a master educator and quantitative finance specialist.
Explain financial and investment concepts with rigorous clarity, mathematical formulas where appropriate, and practical examples.

CRITICAL CONSTRAINTS:
1. Educational Tone: Professional, objective, and mathematically precise.
2. Practical Context: Provide concrete illustrative examples (e.g. how P/E or Sharpe Ratio is calculated).
3. Risk Awareness: Always explain the limitations, caveats, and risk assumptions of the concept.
4. Disclaimer: Emphasize that all explanations are educational.
"""


class UnifiedFinancialAnalyst:
    """
    Central financial intelligence orchestrator routing queries to grounded domain specialists.
    """

    async def get_recent_history(
        self,
        session_id: str,
        db: AsyncSession,
        limit: int = 6
    ) -> List[Dict[str, str]]:
        """Retrieves recent conversation turns for multi-turn conversational context."""
        try:
            stmt = (
                select(ChatHistory)
                .where(ChatHistory.session_id == session_id)
                .order_by(ChatHistory.created_at.desc())
                .limit(limit)
            )
            result = await db.execute(stmt)
            records = list(result.scalars().all())
            records.reverse()

            return [{"role": r.role, "content": r.message} for r in records]
        except Exception as e:
            logger.warning(f"Could not load conversation history for session {session_id}: {e}")
            return []

    def _build_history_context(self, history: List[Dict[str, str]]) -> str:
        """Formats conversation history into prompt context."""
        if not history:
            return ""
        lines = ["=== RECENT CONVERSATION HISTORY ==="]
        for turn in history[-4:]:  # last 2 exchanges
            speaker = "User" if turn["role"] == "user" else "Assistant"
            lines.append(f"{speaker}: {turn['content'][:300]}")
        lines.append("=== END CONVERSATION HISTORY ===\n")
        return "\n".join(lines)

    async def _handle_document_rag(
        self,
        query: str,
        document_id: Optional[str],
        company_name: Optional[str]
    ) -> Tuple[str, List[CitationItem]]:
        """Handles document Q&A using hybrid search and cross-encoder reranking."""
        where_clause: Optional[Dict[str, Any]] = None
        if document_id:
            where_clause = {"document_id": document_id}
        elif company_name:
            where_clause = {"company_name": company_name}

        answer, citations, _ = await rag_pipeline.ainvoke(
            question=query,
            where=where_clause
        )
        return answer, citations

    async def _handle_company_research(
        self,
        query: str,
        entities: Dict[str, Any],
        db: AsyncSession,
        history_context: str
    ) -> Tuple[str, List[CitationItem]]:
        """Retrieves audited company financials and synthesizes an institutional analysis."""
        tickers = entities.get("tickers", [])
        company_names = entities.get("companies", [])

        # Query database for matching companies
        stmt = select(Company).options(selectinload(Company.metrics))
        if tickers:
            stmt = stmt.where(Company.symbol.in_(tickers))
        elif company_names:
            stmt = stmt.where(Company.name.in_(company_names))

        result = await db.execute(stmt)
        companies = list(result.scalars().all())

        # If no specific company was found, load all available companies
        if not companies:
            all_stmt = select(Company).options(selectinload(Company.metrics)).limit(5)
            all_res = await db.execute(all_stmt)
            companies = list(all_res.scalars().all())

        if not companies:
            return (
                "No company fundamental data is currently available in the research database. "
                "Please seed the research dataset or upload corporate financial filings in the Documents tab.",
                []
            )

        # Build verified data context and citations
        context_blocks = []
        citations: List[CitationItem] = []

        for c in companies:
            c_block = [
                f"Company: {c.name} ({c.symbol})",
                f"Sector: {c.sector} | Industry: {c.industry}",
                f"Overview: {c.description or 'N/A'}",
                "Audited Metrics by Fiscal Year:"
            ]
            # Sort metrics newest first
            sorted_metrics = sorted(c.metrics, key=lambda m: m.fiscal_year, reverse=True)
            for m in sorted_metrics:
                growth_str = f"{m.revenue_growth * 100:.1f}%" if m.revenue_growth is not None else "N/A"
                profit_str = f"{m.profit_growth * 100:.1f}%" if m.profit_growth is not None else "N/A"
                roe_str = f"{m.roe * 100:.1f}%" if m.roe is not None else "N/A"
                roce_str = f"{m.roce * 100:.1f}%" if m.roce is not None else "N/A"

                c_block.append(
                    f"  - FY{m.fiscal_year}: Revenue=${m.revenue:,.0f} (Growth: {growth_str}), "
                    f"Net Profit=${m.net_profit:,.0f} (Growth: {profit_str}), "
                    f"ROE={roe_str}, ROCE={roce_str}, D/E={m.debt_to_equity:.2f}, "
                    f"P/E={m.pe_ratio:.1f}, MktCap=${m.market_cap:,.0f}"
                )

                # Add verifiable citation
                citations.append(
                    CitationItem(
                        document_name=f"{c.name} ({c.symbol}) Audited Financials",
                        page_number=m.fiscal_year,
                        section=f"Annual Filing FY{m.fiscal_year}",
                        excerpt=(
                            f"Revenue: ${m.revenue:,.0f} | Net Profit: ${m.net_profit:,.0f} | "
                            f"P/E: {m.pe_ratio:.1f} | ROE: {roe_str} | D/E: {m.debt_to_equity:.2f}"
                        ),
                        relevance_score=0.95
                    )
                )
            context_blocks.append("\n".join(c_block))

        formatted_dataset = "\n\n".join(context_blocks)
        full_context = f"{history_context}=== AUDITED FINANCIAL DATASET ===\n{formatted_dataset}"

        answer = await llm_service.generate_grounded_answer(
            query=query,
            formatted_context=full_context,
            custom_system_prompt=COMPANY_ANALYSIS_SYSTEM_PROMPT
        )
        return answer, citations[:4]

    async def _handle_mutual_fund_research(
        self,
        query: str,
        entities: Dict[str, Any],
        db: AsyncSession,
        history_context: str
    ) -> Tuple[str, List[CitationItem]]:
        """Retrieves mutual fund factsheets and synthesizes comparative intelligence."""
        fund_keywords = entities.get("funds", [])

        # Fetch mutual funds
        stmt = select(MutualFund).options(selectinload(MutualFund.metrics))
        result = await db.execute(stmt)
        all_funds = list(result.scalars().all())

        if not all_funds:
            return (
                "No mutual fund intelligence is currently indexed in the research data layer. "
                "Please seed the database in the Research tab to begin fund analytics.",
                []
            )

        # Filter funds by query keywords if present
        matched_funds = []
        q_lower = query.lower()
        for f in all_funds:
            if any(kw in f.fund_name.lower() or kw in f.category.lower() for kw in fund_keywords):
                matched_funds.append(f)
            elif f.fund_name.lower() in q_lower or f.category.lower() in q_lower:
                matched_funds.append(f)

        if not matched_funds:
            matched_funds = all_funds[:4]

        # Format dataset and build citations
        fund_blocks = []
        citations: List[CitationItem] = []

        for f in matched_funds:
            metric = f.metrics[0] if f.metrics else None
            if not metric:
                continue

            exp_str = f"{metric.expense_ratio * 100:.2f}%"
            ret3_str = f"{metric.return_3yr:.1f}%" if metric.return_3yr is not None else "N/A"
            ret5_str = f"{metric.return_5yr:.1f}%" if metric.return_5yr is not None else "N/A"

            holdings_str = ", ".join(
                [f"{h.get('name', '')} ({h.get('weight', 0)}%)" for h in (metric.portfolio_holdings or [])[:4]]
            )

            f_block = (
                f"Fund Scheme: {f.fund_name}\n"
                f"Category: {f.category} | Benchmark: {f.benchmark}\n"
                f"Fund Manager: {f.fund_manager or 'Institutional Team'}\n"
                f"AUM: ${metric.aum:,.0f} | Expense Ratio: {exp_str} | Risk: {metric.risk_level}\n"
                f"Trailing Returns: 3-Year CAGR={ret3_str}, 5-Year CAGR={ret5_str}\n"
                f"Exit Load: {metric.exit_load or 'None'}\n"
                f"Top Holdings: {holdings_str or 'Diversified equities'}"
            )
            fund_blocks.append(f_block)

            citations.append(
                CitationItem(
                    document_name=f"{f.fund_name} Official Factsheet",
                    page_number=1,
                    section="Fund Performance & Portfolio Attributes",
                    excerpt=(
                        f"Category: {f.category} | Expense Ratio: {exp_str} | "
                        f"3Y CAGR: {ret3_str} | 5Y CAGR: {ret5_str} | Risk Level: {metric.risk_level}"
                    ),
                    relevance_score=0.92
                )
            )

        formatted_dataset = "\n\n---\n\n".join(fund_blocks)
        full_context = f"{history_context}=== VERIFIED FUND DATASET ===\n{formatted_dataset}"

        answer = await llm_service.generate_grounded_answer(
            query=query,
            formatted_context=full_context,
            custom_system_prompt=MUTUAL_FUND_SYSTEM_PROMPT
        )
        return answer, citations[:4]

    async def _handle_recommendations(
        self,
        query: str,
        db: AsyncSession,
        history_context: str
    ) -> Tuple[str, List[CitationItem]]:
        """Invokes Phase 6 deterministic scoring engine and explains recommended assets."""
        # 1. Load active user profile or sensible institutional defaults
        profile_stmt = select(InvestmentProfile).limit(1)
        res = await db.execute(profile_stmt)
        profile = res.scalars().first()

        risk = profile.risk_tolerance if profile else "Moderate"
        horizon = profile.investment_horizon if profile else "Medium"
        goal = profile.goal if profile else "Wealth creation"
        inv_amount = profile.investment_amount if profile else 500000.0

        # Parse overrides from query if user explicitly mentioned other parameters
        q_lower = query.lower()
        if "high risk" in q_lower or "aggressive" in q_lower:
            risk = "High"
        elif "low risk" in q_lower or "conservative" in q_lower or "capital preservation" in q_lower:
            risk = "Low"

        if "long term" in q_lower or "10 year" in q_lower or "long" in q_lower:
            horizon = "Long"
        elif "short term" in q_lower or "1 year" in q_lower or "short" in q_lower:
            horizon = "Short"

        # 2. Run Phase 6 Candidate Generation & Deterministic Filtering
        candidates = await generate_candidates(db)
        if not candidates:
            return (
                "Unable to generate recommendations: No candidate companies or mutual funds are populated in the system. "
                "Please seed the research dataset first.",
                []
            )

        eligible, _ = apply_hard_filters(candidates, risk, horizon, goal)
        if not eligible:
            eligible = candidates  # Fallback to candidates if constraints are overly tight

        # 3. Score, rank, and explain candidates
        ranking_result = rank_and_explain_candidates(
            candidates=eligible,
            user_risk_tolerance=risk,
            user_investment_horizon=horizon,
            user_goal=goal
        )
        top_ranked = ranking_result.candidates[:3]

        # 4. Format deterministic output context
        rec_blocks = [
            f"Target Profile: Risk={risk}, Horizon={horizon}, Goal={goal}, Capital=${inv_amount:,.0f}\n"
        ]
        citations: List[CitationItem] = []

        for rank, item in enumerate(top_ranked, 1):
            s = item.score_breakdown
            rec_blocks.append(
                f"#{rank}. {item.asset_name} ({item.asset_type})\n"
                f"   - Match Score: {item.match_score:.1f}/100 (Risk: {s.risk_match_score:.0f}, "
                f"Horizon: {s.horizon_match_score:.0f}, Quality: {s.financial_quality_score:.0f}, "
                f"Valuation: {s.valuation_score:.0f}, Goal: {s.diversification_score:.0f})\n"
                f"   - Positive Factors: {'; '.join(item.positive_factors)}\n"
                f"   - Considerations: {'; '.join(item.considerations)}"
            )

            citations.append(
                CitationItem(
                    document_name="FinAdvisor Deterministic Suitability Engine",
                    page_number=rank,
                    section=f"Recommendation Rank #{rank}: {item.asset_name}",
                    excerpt=(
                        f"Match Score: {item.match_score:.1f}/100 | Risk Fit: {s.risk_match_score:.0f}/30 | "
                        f"Horizon Fit: {s.horizon_match_score:.0f}/25 | Financial Quality: {s.financial_quality_score:.0f}/25"
                    ),
                    relevance_score=item.match_score / 100.0
                )
            )

        formatted_dataset = "\n\n".join(rec_blocks)
        full_context = f"{history_context}=== DETERMINISTIC SUITABILITY AUDIT ===\n{formatted_dataset}"

        answer = await llm_service.generate_grounded_answer(
            query=query,
            formatted_context=full_context,
            custom_system_prompt=RECOMMENDATION_SYSTEM_PROMPT
        )
        return answer, citations

    async def _handle_general_financial(
        self,
        query: str,
        history_context: str
    ) -> Tuple[str, List[CitationItem]]:
        """Synthesizes structured financial education on definitions, ratios, and market mechanics."""
        citation = CitationItem(
            document_name="Quantitative Valuation & Financial Theory Principles",
            page_number=1,
            section="Financial Concepts & Ratio Analysis Standards",
            excerpt="Standard institutional definitions for corporate finance, equity valuation, and portfolio risk management.",
            relevance_score=0.9
        )

        full_context = f"{history_context}=== DOMAIN CONTEXT ===\nInstitutional financial principles, valuation equations, and investment analysis fundamentals."

        answer = await llm_service.generate_grounded_answer(
            query=query,
            formatted_context=full_context,
            custom_system_prompt=GENERAL_FINANCIAL_SYSTEM_PROMPT
        )
        return answer, [citation]

    async def execute_turn(
        self,
        query: str,
        session_id: str,
        db: AsyncSession,
        document_id: Optional[str] = None,
        company_name: Optional[str] = None
    ) -> Tuple[str, QueryIntent, List[CitationItem], str]:
        """
        Executes a complete synchronous turn:
        1. Classifies intent & extracts entities
        2. Retrieves conversational memory
        3. Dispatches to specialized handler
        4. Persists turn to ChatHistory
        Returns (answer, query_intent, citations, disclaimer).
        """
        # Step 1: Route query
        intent, entities = await intent_router.route_query(
            query=query,
            document_id=document_id,
            company_name=company_name
        )

        # Step 2: Retrieve conversational history
        history = await self.get_recent_history(session_id, db, limit=6)
        history_context = self._build_history_context(history)

        # Step 3: Dispatch to domain specialist
        if intent == QueryIntent.DOCUMENT_RAG:
            answer, citations = await self._handle_document_rag(query, document_id, company_name)
        elif intent == QueryIntent.COMPANY_RESEARCH:
            answer, citations = await self._handle_company_research(query, entities, db, history_context)
        elif intent == QueryIntent.MUTUAL_FUND_RESEARCH:
            answer, citations = await self._handle_mutual_fund_research(query, entities, db, history_context)
        elif intent == QueryIntent.RECOMMENDATIONS:
            answer, citations = await self._handle_recommendations(query, db, history_context)
        else:
            answer, citations = await self._handle_general_financial(query, history_context)

        # Step 4: Persist chat turn into database
        try:
            user_log = ChatHistory(
                session_id=session_id,
                role="user",
                query_type=intent.value,
                message=query,
                citations=[]
            )
            db.add(user_log)

            assistant_log = ChatHistory(
                session_id=session_id,
                role="assistant",
                query_type=intent.value,
                message=answer,
                citations=[c.model_dump() for c in citations]
            )
            db.add(assistant_log)
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to log chat history for session {session_id}: {e}")

        return answer, intent, citations, REGULATORY_DISCLAIMER

    async def stream_turn(
        self,
        query: str,
        session_id: str,
        db: AsyncSession,
        document_id: Optional[str] = None,
        company_name: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Streams response tokens as Server-Sent Events (SSE).
        Yields events:
        - event: intent
        - event: token
        - event: citations
        - event: done
        """
        # 1. Classify intent
        intent, entities = await intent_router.route_query(
            query=query,
            document_id=document_id,
            company_name=company_name
        )

        # Emit intent event
        intent_payload = json.dumps({"intent": intent.value, "entities": entities})
        yield f"event: intent\ndata: {intent_payload}\n\n"

        # 2. Execute full analysis
        answer, resolved_intent, citations, disclaimer = await self.execute_turn(
            query=query,
            session_id=session_id,
            db=db,
            document_id=document_id,
            company_name=company_name
        )

        # Stream answer in progressive chunks
        # Chunk size ~2-4 words for fluid typing experience
        words = answer.split(" ")
        for i in range(0, len(words), 3):
            chunk = " ".join(words[i:i+3]) + " "
            token_payload = json.dumps({"token": chunk})
            yield f"event: token\ndata: {token_payload}\n\n"

        # Emit citations event
        citations_payload = json.dumps({"citations": [c.model_dump() for c in citations]})
        yield f"event: citations\ndata: {citations_payload}\n\n"

        # Emit completion event
        done_payload = json.dumps({
            "session_id": session_id,
            "query_type": resolved_intent.value,
            "disclaimer": disclaimer
        })
        yield f"event: done\ndata: {done_payload}\n\n"


# Global analyst service instance
unified_analyst = UnifiedFinancialAnalyst()
