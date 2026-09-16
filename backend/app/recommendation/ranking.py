"""
FinAdvisor — Ranking & Grounded Explainability Engine
Ranks scored candidate assets and generates fact-grounded positive factors
and risk considerations referencing audited metrics.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.recommendation.candidate_generator import CandidateAsset
from backend.app.recommendation.scoring import ScoreBreakdown, score_candidate
from backend.app.utils.logger import logger


class RankedCandidate(BaseModel):
    """Output candidate schema expected by API and UI."""
    id: str
    asset_name: str
    asset_type: str  # 'Company' or 'Mutual Fund'
    symbol_or_code: str
    match_score: float = Field(..., ge=0, le=100)
    positive_factors: List[str]
    considerations: List[str]
    score_breakdown: ScoreBreakdown
    source_reference: str


class RecommendationResult(BaseModel):
    user_risk_tolerance: str
    user_investment_horizon: str
    user_goal: Optional[str] = None
    disclaimer: str = (
        "This application provides educational and analytical intelligence based on audited data. "
        "It does not constitute personalized financial advice or guaranteed investment returns."
    )
    candidates: List[RankedCandidate]


def format_currency_amount(val: Optional[float]) -> str:
    """Formats large monetary numbers concisely."""
    if val is None:
        return "N/A"
    abs_val = abs(val)
    if abs_val >= 1_000_000_000:
        return f"${val / 1_000_000_000:.1f}B"
    if abs_val >= 1_000_000:
        return f"${val / 1_000_000:.1f}M"
    return f"${val:,.0f}"


def generate_company_explainability(
    asset: CandidateAsset,
    breakdown: ScoreBreakdown,
    user_risk: str,
    user_horizon: str
) -> tuple[List[str], List[str]]:
    """Generates fact-grounded positive factors and risk considerations for companies."""
    positives: List[str] = []
    risks: List[str] = []
    m = asset.financial_metrics

    # Positive Factors
    roe = m.get("roe")
    if roe is not None and roe >= 15.0:
        positives.append(f"Outstanding Return on Equity (ROE) of {roe:.1f}%, indicating superior capital efficiency.")
    
    de = m.get("debt_to_equity")
    if de is not None and de <= 0.5:
        positives.append(f"Conservative capital structure with low Debt-to-Equity of {de:.2f}.")

    ocf = m.get("operating_cash_flow")
    if ocf is not None and ocf > 0:
        positives.append(f"Robust core cash generation with Operating Cash Flow of {format_currency_amount(ocf)}.")

    rev_growth = m.get("revenue_growth")
    if rev_growth is not None and rev_growth > 0.08:
        positives.append(f"Strong top-line momentum with YoY revenue expansion of {rev_growth * 100:.1f}%.")

    pe = m.get("pe_ratio")
    if pe is not None and pe <= 28.0:
        positives.append(f"Attractive valuation multiple with P/E ratio of {pe:.1f}x relative to earnings power.")

    if not positives:
        positives.append(f"Matches specified {user_risk} risk profile and {user_horizon} horizon targets.")
    if len(positives) < 3:
        positives.append(f"Established market presence in {asset.sector_or_category} sector.")

    # Risk Considerations
    if pe is not None and pe > 35.0:
        risks.append(f"Premium valuation (P/E {pe:.1f}x) leaves little buffer if earnings decelerate.")

    if de is not None and de > 0.7:
        risks.append(f"Moderate-to-high leverage with Debt-to-Equity of {de:.2f} requires interest coverage monitoring.")

    if rev_growth is not None and rev_growth < 0.05:
        risks.append(f"Slowing revenue growth ({rev_growth * 100:.1f}%) warrants tracking competitive pressures.")

    risks.append(f"Individual equity holdings are subject to market cycles and {asset.sector_or_category} sector risks.")

    return positives[:4], risks[:3]


def generate_fund_explainability(
    asset: CandidateAsset,
    breakdown: ScoreBreakdown,
    user_risk: str,
    user_horizon: str
) -> tuple[List[str], List[str]]:
    """Generates fact-grounded positive factors and risk considerations for mutual funds."""
    positives: List[str] = []
    risks: List[str] = []
    m = asset.financial_metrics

    # Positive Factors
    r5 = m.get("return_5yr")
    r3 = m.get("return_3yr")
    best_ret = r5 if r5 is not None else r3
    if best_ret is not None and best_ret >= 10.0:
        positives.append(f"Proven compounding track record with {best_ret:.1f}% trailing CAGR.")

    er = m.get("expense_ratio")
    if er is not None:
        er_pct = er if er > 0.05 else (er * 100.0)
        if er_pct <= 0.85:
            positives.append(f"Cost-efficient expense ratio of {er_pct:.2f}%, minimizing cumulative fee drag.")

    aum = m.get("aum")
    if aum is not None and aum >= 5000.0:
        positives.append(f"High institutional liquidity with AUM exceeding ₹{aum:,.0f} Cr.")

    positives.append(f"Suited for {user_horizon} investment horizon within {asset.sector_or_category} category.")

    # Risk Considerations
    exit_load = m.get("exit_load")
    if exit_load and exit_load.lower() != "nil":
        risks.append(f"Exit load: {exit_load}.")

    if er is not None:
        er_pct = er if er > 0.05 else (er * 100.0)
        if er_pct > 1.0:
            risks.append(f"Expense ratio ({er_pct:.2f}%) is higher than low-cost passive alternatives.")

    risks.append("Performance depends on underlying asset allocation and benchmark tracking error.")

    return positives[:4], risks[:3]


def rank_and_explain_candidates(
    candidates: List[CandidateAsset],
    user_risk_tolerance: str,
    user_investment_horizon: str,
    user_goal: Optional[str] = None
) -> RecommendationResult:
    """
    Scores, rank-orders, and generates grounded explainability rationales
    for filtered candidates.
    """
    scored_items = []

    for asset in candidates:
        match_score, breakdown = score_candidate(
            asset=asset,
            user_risk_tolerance=user_risk_tolerance,
            user_investment_horizon=user_investment_horizon,
            user_goal=user_goal
        )

        if asset.asset_type == "Company":
            positives, considerations = generate_company_explainability(
                asset=asset,
                breakdown=breakdown,
                user_risk=user_risk_tolerance,
                user_horizon=user_investment_horizon
            )
        else:
            positives, considerations = generate_fund_explainability(
                asset=asset,
                breakdown=breakdown,
                user_risk=user_risk_tolerance,
                user_horizon=user_investment_horizon
            )

        ranked_cand = RankedCandidate(
            id=asset.id,
            asset_name=asset.asset_name,
            asset_type=asset.asset_type,
            symbol_or_code=asset.symbol_or_code,
            match_score=match_score,
            positive_factors=positives,
            considerations=considerations,
            score_breakdown=breakdown,
            source_reference=asset.source_reference
        )
        scored_items.append(ranked_cand)

    # Sort descending by match_score
    scored_items.sort(key=lambda x: x.match_score, reverse=True)

    logger.info(
        f"Ranked {len(scored_items)} candidates. Top match: "
        f"{scored_items[0].asset_name if scored_items else 'None'} ({scored_items[0].match_score if scored_items else 0})"
    )

    return RecommendationResult(
        user_risk_tolerance=user_risk_tolerance,
        user_investment_horizon=user_investment_horizon,
        user_goal=user_goal,
        candidates=scored_items
    )
