from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.connection import get_db
from backend.app.database.models import InvestmentProfile, User
from backend.app.utils.logger import logger

router = APIRouter(prefix="/profile", tags=["Investment Profile"])


class ProfileCreateOrUpdate(BaseModel):
    investment_amount: float = Field(..., gt=0, description="Total capital available to invest in local currency")
    monthly_investment_amount: Optional[float] = Field(0.0, ge=0, description="Monthly recurring investment amount")
    risk_tolerance: str = Field(..., description="Investor risk tolerance: 'Low', 'Moderate', or 'High'")
    investment_horizon: str = Field(..., description="Horizon: 'Short' (1-3y), 'Medium' (3-5y), or 'Long' (5y+)")
    goal: str = Field(..., description="Primary goal: 'Wealth creation', 'Capital preservation', 'Income', 'Other'")


class ProfileResponse(BaseModel):
    id: str
    user_id: str
    investment_amount: float
    monthly_investment_amount: Optional[float]
    risk_tolerance: str
    investment_horizon: str
    goal: str

    model_config = ConfigDict(from_attributes=True)


async def get_or_create_default_user(db: AsyncSession) -> User:
    """Helper to retrieve or create a default demo user for local session development."""
    stmt = select(User).where(User.email == "demo@finadvisor.ai")
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(email="demo@finadvisor.ai", full_name="Portfolio Demo Investor")
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


@router.get("", response_model=Optional[ProfileResponse])
async def get_profile(db: AsyncSession = Depends(get_db)):
    """Fetches the active user's investment profile."""
    user = await get_or_create_default_user(db)
    stmt = select(InvestmentProfile).where(InvestmentProfile.user_id == user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    
    if not profile:
        # Return a sensible default demo profile if not yet created
        return None
    return profile


@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_profile(payload: ProfileCreateOrUpdate, db: AsyncSession = Depends(get_db)):
    """Creates or updates the user's investment profile."""
    # Validate allowed categories
    valid_risks = {"Low", "Moderate", "High"}
    valid_horizons = {"Short", "Medium", "Long"}
    valid_goals = {"Wealth creation", "Capital preservation", "Income", "Other"}

    if payload.risk_tolerance not in valid_risks:
        raise HTTPException(status_code=400, detail=f"Risk tolerance must be one of {valid_risks}")
    if payload.investment_horizon not in valid_horizons:
        raise HTTPException(status_code=400, detail=f"Investment horizon must be one of {valid_horizons}")
    if payload.goal not in valid_goals:
        raise HTTPException(status_code=400, detail=f"Goal must be one of {valid_goals}")

    user = await get_or_create_default_user(db)
    stmt = select(InvestmentProfile).where(InvestmentProfile.user_id == user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if profile:
        profile.investment_amount = payload.investment_amount
        profile.monthly_investment_amount = payload.monthly_investment_amount
        profile.risk_tolerance = payload.risk_tolerance
        profile.investment_horizon = payload.investment_horizon
        profile.goal = payload.goal
    else:
        profile = InvestmentProfile(
            user_id=user.id,
            investment_amount=payload.investment_amount,
            monthly_investment_amount=payload.monthly_investment_amount,
            risk_tolerance=payload.risk_tolerance,
            investment_horizon=payload.investment_horizon,
            goal=payload.goal
        )
        db.add(profile)

    await db.commit()
    await db.refresh(profile)
    logger.info(f"Investment profile saved for user {user.id}")
    return profile


@router.put("", response_model=ProfileResponse)
async def update_profile(payload: ProfileCreateOrUpdate, db: AsyncSession = Depends(get_db)):
    """Updates the active user's investment profile."""
    return await create_or_update_profile(payload=payload, db=db)
