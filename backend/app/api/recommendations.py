from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.profile import get_or_create_default_user
from backend.app.database.connection import get_db
from backend.app.database.models import InvestmentProfile
from backend.app.recommendation.candidate_generator import generate_candidates
from backend.app.recommendation.filters import apply_hard_filters
from backend.app.recommendation.ranking import (
    RankedCandidate,
    RecommendationResult,
    rank_and_explain_candidates,
)
from backend.app.recommendation.scoring import ScoreBreakdown
from backend.app.utils.logger import logger

router = APIRouter(prefix="/recommendations", tags=["Matching & Recommendations"])


class EvaluateRequest(BaseModel):
    """Custom profile parameters for on-the-fly what-if scenario evaluation."""
    risk_tolerance: str = Field("Moderate", description="'Conservative' / 'Low', 'Moderate', 'Aggressive' / 'High'")
    investment_horizon: str = Field("Medium", description="'Short', 'Medium', or 'Long'")
    goal: Optional[str] = Field("Wealth creation", description="Investment goal")
    asset_type_filter: Optional[str] = Field(None, description="Optional filter: 'Company', 'Mutual Fund', or None for All")


@router.get("", response_model=RecommendationResult)
async def get_recommendations(
    asset_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Computes deterministic candidate matches based on the active user's saved investment profile.
    Applies hard constraint filters, multi-factor scoring, rank ordering, and audited explainability.
    """
    user = await get_or_create_default_user(db)
    stmt = select(InvestmentProfile).where(InvestmentProfile.user_id == user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    # Fallback to standard defaults if user has not yet customized their profile
    risk_tolerance = profile.risk_tolerance if profile else "Moderate"
    investment_horizon = profile.investment_horizon if profile else "Medium"
    goal = profile.goal if profile else "Wealth creation"

    logger.info(
        f"Evaluating recommendations for profile: risk={risk_tolerance}, horizon={investment_horizon}, goal={goal}"
    )

    # 1. Generate universe of candidate assets from database
    candidates = await generate_candidates(db)

    # Optional asset type filter
    if asset_type and asset_type.lower() != "all":
        target = "Company" if "comp" in asset_type.lower() or "stock" in asset_type.lower() else "Mutual Fund"
        candidates = [c for c in candidates if c.asset_type == target]

    # 2. Apply hard constraint filters
    passed_candidates, _ = apply_hard_filters(
        candidates=candidates,
        user_risk_tolerance=risk_tolerance,
        user_investment_horizon=investment_horizon,
        user_goal=goal
    )

    # 3. Score, rank, and generate explainability rationale
    rec_result = rank_and_explain_candidates(
        candidates=passed_candidates,
        user_risk_tolerance=risk_tolerance,
        user_investment_horizon=investment_horizon,
        user_goal=goal
    )

    return rec_result


@router.post("/evaluate", response_model=RecommendationResult)
async def evaluate_custom_profile(
    payload: EvaluateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Simulates recommendations for custom/transient profile parameters
    without altering the user's saved profile in the database.
    """
    candidates = await generate_candidates(db)

    if payload.asset_type_filter and payload.asset_type_filter.lower() != "all":
        target = "Company" if "comp" in payload.asset_type_filter.lower() or "stock" in payload.asset_type_filter.lower() else "Mutual Fund"
        candidates = [c for c in candidates if c.asset_type == target]

    passed_candidates, _ = apply_hard_filters(
        candidates=candidates,
        user_risk_tolerance=payload.risk_tolerance,
        user_investment_horizon=payload.investment_horizon,
        user_goal=payload.goal
    )

    rec_result = rank_and_explain_candidates(
        candidates=passed_candidates,
        user_risk_tolerance=payload.risk_tolerance,
        user_investment_horizon=payload.investment_horizon,
        user_goal=payload.goal
    )

    return rec_result
