"""
FinAdvisor — Hard Constraint Filters
Applies fiduciary and suitability rules to screen out unsuitable assets
based on the user's risk tolerance, investment horizon, and primary goal.
"""

from typing import Any, Dict, List, Optional, Tuple
from backend.app.recommendation.candidate_generator import CandidateAsset
from backend.app.utils.logger import logger


def normalize_risk(risk_str: str) -> str:
    """Normalizes risk tolerance string to standard tiers."""
    r = (risk_str or "").strip().title()
    if r in ["Low", "Conservative"]:
        return "Conservative"
    if r in ["High", "Aggressive"]:
        return "Aggressive"
    return "Moderate"


def normalize_horizon(horizon_str: str) -> str:
    """Normalizes horizon string to standard tiers."""
    h = (horizon_str or "").strip().title()
    if "Short" in h:
        return "Short"
    if "Long" in h:
        return "Long"
    return "Medium"


def apply_hard_filters(
    candidates: List[CandidateAsset],
    user_risk_tolerance: str,
    user_investment_horizon: str,
    user_goal: Optional[str] = None
) -> Tuple[List[CandidateAsset], List[Dict[str, Any]]]:
    """
    Executes hard filtering checks on candidate universe.
    Returns:
        (passed_candidates, filter_audit_log)
    """
    risk_tier = normalize_risk(user_risk_tolerance)
    horizon_tier = normalize_horizon(user_investment_horizon)
    goal = (user_goal or "").strip().title()

    passed: List[CandidateAsset] = []
    audit_log: List[Dict[str, Any]] = []

    for asset in candidates:
        rejection_reasons = []

        # 1. Risk Tolerance Constraints
        if risk_tier == "Conservative":
            if asset.risk_level in ["High", "Very High"]:
                rejection_reasons.append(
                    f"Asset risk '{asset.risk_level}' violates Conservative risk ceiling."
                )
            de = asset.financial_metrics.get("debt_to_equity")
            if de is not None and de > 1.0:
                rejection_reasons.append(
                    f"Debt-to-equity ratio of {de:.2f} exceeds Conservative leverage threshold (1.0)."
                )

        elif risk_tier == "Moderate":
            if asset.risk_level == "Very High":
                rejection_reasons.append(
                    "Asset classified as Very High risk; exceeds Moderate risk tolerance."
                )
            de = asset.financial_metrics.get("debt_to_equity")
            if de is not None and de > 2.0:
                rejection_reasons.append(
                    f"Excessive debt-to-equity ({de:.2f}) exceeds Moderate ceiling (2.0)."
                )

        # 2. Investment Horizon Constraints
        if horizon_tier == "Short":
            # For short horizon (< 1 year), equity market volatility creates unacceptable drawdown risk
            if asset.asset_type == "Company":
                rejection_reasons.append(
                    "Individual equity stocks are unsuitable for Short horizon (<1 yr) due to market volatility."
                )
            elif asset.asset_type == "Mutual Fund":
                cat = asset.sector_or_category.lower()
                if not any(k in cat for k in ["liquid", "debt", "money market", "overnight", "arbitrage"]):
                    rejection_reasons.append(
                        f"Equity mutual fund category '{asset.sector_or_category}' requires 3+ years to mitigate drawdown risk."
                    )

        elif horizon_tier == "Medium":
            if asset.recommended_horizon == "Long" and asset.risk_level == "High":
                rejection_reasons.append(
                    "High-beta growth assets require 5+ years horizon; exceeds Medium horizon (1-5 yrs)."
                )

        # 3. Goal Constraints
        if "Capital Preservation" in goal:
            if asset.risk_level in ["High", "Very High"]:
                rejection_reasons.append(
                    "High volatility incompatible with Capital Preservation objective."
                )
            ocf = asset.financial_metrics.get("operating_cash_flow")
            if ocf is not None and ocf < 0:
                rejection_reasons.append(
                    "Negative operating cash flow violates Capital Preservation safety rule."
                )

        # Record outcome
        if rejection_reasons:
            audit_log.append({
                "asset_id": asset.id,
                "asset_name": asset.asset_name,
                "status": "REJECTED",
                "reasons": rejection_reasons
            })
        else:
            passed.append(asset)
            audit_log.append({
                "asset_id": asset.id,
                "asset_name": asset.asset_name,
                "status": "PASSED",
                "reasons": []
            })

    # Graceful Fallback: If hard filters eliminated all candidates, fall back to safest assets
    if not passed and candidates:
        logger.warning(
            f"Hard filters rejected all {len(candidates)} candidates for {risk_tier}/{horizon_tier}. Applying safety fallback."
        )
        # Select low/moderate risk assets sorted by lowest risk
        fallback_candidates = [
            c for c in candidates if c.risk_level in ["Low", "Moderate"]
        ]
        if not fallback_candidates:
            fallback_candidates = candidates[:3]
        return fallback_candidates, audit_log

    logger.info(
        f"Hard filters passed {len(passed)} of {len(candidates)} candidates for profile ({risk_tier}, {horizon_tier})."
    )
    return passed, audit_log
