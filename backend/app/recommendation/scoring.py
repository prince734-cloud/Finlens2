"""
FinAdvisor — Multi-Factor Deterministic Scoring Engine
Calculates transparent mathematical suitability scores (0-100) across 5 weighted dimensions:
1. Risk Compatibility (30 pts)
2. Investment Horizon Suitability (25 pts)
3. Financial Quality & Balance Sheet Health (25 pts)
4. Valuation & Cost Efficiency (10 pts)
5. Goal Alignment & Portfolio Fit (10 pts)
"""

from typing import Optional, Tuple
from pydantic import BaseModel, Field
from backend.app.recommendation.candidate_generator import CandidateAsset
from backend.app.recommendation.filters import normalize_risk, normalize_horizon


class ScoreBreakdown(BaseModel):
    risk_match_score: float = Field(..., ge=0, le=30)
    horizon_match_score: float = Field(..., ge=0, le=25)
    financial_quality_score: float = Field(..., ge=0, le=25)
    valuation_score: float = Field(..., ge=0, le=10)
    diversification_score: float = Field(..., ge=0, le=10)


def score_risk_compatibility(asset: CandidateAsset, user_risk_tier: str) -> float:
    """Calculates risk alignment score (0 to 30 points)."""
    user_risk = normalize_risk(user_risk_tier)
    asset_risk = asset.risk_level.title()

    if user_risk == "Conservative":
        if asset_risk == "Low":
            return 30.0
        elif asset_risk == "Moderate":
            return 20.0
        elif asset_risk == "High":
            return 6.0
        return 0.0

    elif user_risk == "Moderate":
        if asset_risk == "Moderate":
            return 30.0
        elif asset_risk == "Low":
            return 24.0
        elif asset_risk == "High":
            return 18.0
        return 5.0

    else:  # Aggressive
        if asset_risk == "High":
            return 30.0
        elif asset_risk == "Very High":
            return 26.0
        elif asset_risk == "Moderate":
            return 22.0
        return 14.0


def score_horizon_suitability(asset: CandidateAsset, user_horizon_tier: str) -> float:
    """Calculates investment horizon suitability score (0 to 25 points)."""
    user_h = normalize_horizon(user_horizon_tier)
    asset_h = normalize_horizon(asset.recommended_horizon)

    if user_h == asset_h:
        return 25.0

    if user_h == "Short":
        if asset_h == "Medium":
            return 12.0
        return 4.0

    elif user_h == "Medium":
        if asset_h == "Short":
            return 18.0
        return 16.0

    else:  # Long
        if asset_h == "Medium":
            return 20.0
        return 12.0


def score_financial_quality(asset: CandidateAsset) -> float:
    """
    Evaluates underlying fundamental quality (0 to 25 points).
    For Companies: ROE (8), ROCE (6), D/E (6), Operating Cash Flow (5).
    For Mutual Funds: Trailing CAGR (10), AUM stability (8), Consistency/Diversification (7).
    """
    metrics = asset.financial_metrics

    if asset.asset_type == "Company":
        score = 0.0

        # 1. ROE (max 8 pts)
        roe = metrics.get("roe")
        if roe is not None:
            if roe >= 25.0:
                score += 8.0
            elif roe >= 15.0:
                score += 6.0
            elif roe >= 10.0:
                score += 4.0
            elif roe > 0:
                score += 2.0
        else:
            score += 4.0

        # 2. ROCE (max 6 pts)
        roce = metrics.get("roce")
        if roce is not None:
            if roce >= 20.0:
                score += 6.0
            elif roce >= 12.0:
                score += 4.5
            elif roce >= 8.0:
                score += 3.0
            elif roce > 0:
                score += 1.5
        else:
            score += 3.0

        # 3. Debt to Equity (max 6 pts)
        is_bank = "financial" in (asset.sector_or_category or "").lower() or "bank" in (asset.sector_or_category or "").lower()
        if is_bank:
            # Banking models operate on leverage / deposits
            score += 5.0
        else:
            de = metrics.get("debt_to_equity")
            if de is not None:
                if de <= 0.2:
                    score += 6.0
                elif de <= 0.6:
                    score += 4.5
                elif de <= 1.2:
                    score += 2.5
                else:
                    score += 0.5
            else:
                score += 3.0

        # 4. Operating Cash Flow (max 5 pts)
        ocf = metrics.get("operating_cash_flow")
        net_profit = metrics.get("net_profit")
        if ocf is not None and ocf > 0:
            if net_profit is not None and ocf >= net_profit:
                score += 5.0
            else:
                score += 3.5
        else:
            score += 1.0

        return min(round(score, 1), 25.0)

    else:
        # Mutual Fund
        fund_score = 0.0

        # 1. Historical Returns (max 10 pts)
        r5 = metrics.get("return_5yr")
        r3 = metrics.get("return_3yr")
        perf = r5 if r5 is not None else r3
        if perf is not None:
            if perf >= 18.0:
                fund_score += 10.0
            elif perf >= 12.0:
                fund_score += 8.0
            elif perf >= 7.0:
                fund_score += 6.0
            else:
                fund_score += 4.0
        else:
            fund_score += 6.0

        # 2. AUM Size & Stability (max 8 pts)
        aum = metrics.get("aum")
        if aum is not None:
            if aum >= 20000.0:
                fund_score += 8.0
            elif aum >= 5000.0:
                fund_score += 6.5
            elif aum >= 1000.0:
                fund_score += 4.5
            else:
                fund_score += 3.0
        else:
            fund_score += 5.0

        # 3. Portfolio Diversification (max 7 pts)
        holdings = metrics.get("portfolio_holdings") or []
        if len(holdings) >= 4:
            fund_score += 7.0
        else:
            fund_score += 5.0

        return min(round(fund_score, 1), 25.0)


def score_valuation_and_cost(asset: CandidateAsset) -> float:
    """
    Evaluates valuation attractiveness and cost efficiency (0 to 10 points).
    For Companies: P/E Ratio.
    For Mutual Funds: Expense Ratio.
    """
    metrics = asset.financial_metrics

    if asset.asset_type == "Company":
        pe = metrics.get("pe_ratio")
        if pe is not None:
            if pe <= 20.0:
                return 10.0
            elif pe <= 32.0:
                return 8.0
            elif pe <= 45.0:
                return 5.5
            elif pe <= 65.0:
                return 3.5
            else:
                return 2.0
        return 6.0

    else:
        # Mutual Fund Expense Ratio
        er = metrics.get("expense_ratio")
        if er is not None:
            # Handle decimal vs percentage (e.g., 0.0065 vs 0.65)
            er_pct = er if er > 0.05 else (er * 100.0)
            if er_pct <= 0.40:
                return 10.0
            elif er_pct <= 0.75:
                return 8.5
            elif er_pct <= 1.20:
                return 6.0
            elif er_pct <= 1.60:
                return 3.5
            else:
                return 2.0
        return 6.0


def score_goal_alignment(
    asset: CandidateAsset,
    user_goal: Optional[str]
) -> float:
    """Evaluates alignment with user's financial goal (0 to 10 points)."""
    goal = (user_goal or "").strip().title()

    if "Wealth" in goal or "Growth" in goal:
        # Rewards high-growth equities and equity mutual funds
        if asset.asset_type == "Company":
            rev_growth = asset.financial_metrics.get("revenue_growth") or 0.0
            return 10.0 if rev_growth > 0.10 else 8.0
        else:
            cat = asset.sector_or_category.lower()
            return 10.0 if ("flexi" in cat or "mid" in cat or "large" in cat) else 6.0

    elif "Preservation" in goal:
        # Rewards low leverage, strong cash flow, and debt/liquid assets
        if asset.asset_type == "Mutual Fund":
            cat = asset.sector_or_category.lower()
            return 10.0 if ("debt" in cat or "liquid" in cat or "hybrid" in cat) else 5.0
        else:
            de = asset.financial_metrics.get("debt_to_equity") or 0.5
            return 9.0 if de < 0.3 else 5.0

    elif "Income" in goal:
        # Steady cash flow or balanced asset
        if asset.asset_type == "Mutual Fund" and "hybrid" in asset.sector_or_category.lower():
            return 9.5
        return 7.5

    else:
        # Default balanced alignment
        return 8.0


def score_candidate(
    asset: CandidateAsset,
    user_risk_tolerance: str,
    user_investment_horizon: str,
    user_goal: Optional[str] = None
) -> Tuple[float, ScoreBreakdown]:
    """
    Computes deterministic multi-factor match score (0-100) and breakdown.
    """
    risk_score = score_risk_compatibility(asset, user_risk_tolerance)
    horizon_score = score_horizon_suitability(asset, user_investment_horizon)
    quality_score = score_financial_quality(asset)
    valuation_score = score_valuation_and_cost(asset)
    goal_score = score_goal_alignment(asset, user_goal)

    breakdown = ScoreBreakdown(
        risk_match_score=risk_score,
        horizon_match_score=horizon_score,
        financial_quality_score=quality_score,
        valuation_score=valuation_score,
        diversification_score=goal_score
    )

    total_score = round(
        risk_score + horizon_score + quality_score + valuation_score + goal_score,
        1
    )
    # Guarantee 0 <= score <= 100
    bounded_score = max(0.0, min(100.0, total_score))

    return bounded_score, breakdown
