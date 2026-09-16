from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.data.company_data import seed_company_data
from backend.app.data.mutual_fund_data import seed_mutual_fund_data
from backend.app.database.connection import get_db
from backend.app.database.models import Company, CompanyMetric, MutualFund, MutualFundMetric
from backend.app.utils.logger import logger

router = APIRouter(prefix="/research", tags=["Financial Research"])


# =====================================================================
# Pydantic Schemas
# =====================================================================

class CompanyMetricSchema(BaseModel):
    fiscal_year: int
    revenue: float
    revenue_growth: Optional[float] = None
    net_profit: float
    profit_growth: Optional[float] = None
    roe: Optional[float] = None
    roce: Optional[float] = None
    debt_to_equity: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    pe_ratio: Optional[float] = None
    market_cap: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class CompanyResponse(BaseModel):
    id: str
    symbol: str
    name: str
    sector: str
    industry: str
    description: Optional[str] = None
    metrics: List[CompanyMetricSchema] = []

    model_config = ConfigDict(from_attributes=True)


class CompanyCreateOrUpdate(BaseModel):
    symbol: str = Field(..., max_length=20, description="Stock ticker symbol (e.g. 'AAPL')")
    name: str = Field(..., max_length=255, description="Full company legal name")
    sector: str = Field(..., max_length=100)
    industry: str = Field(..., max_length=100)
    description: Optional[str] = None
    metrics: List[CompanyMetricSchema] = []


class MutualFundMetricSchema(BaseModel):
    aum: float
    expense_ratio: float
    risk_level: str
    return_3yr: Optional[float] = None
    return_5yr: Optional[float] = None
    exit_load: Optional[str] = None
    portfolio_holdings: List[Dict[str, Any]] = []

    model_config = ConfigDict(from_attributes=True)


class MutualFundResponse(BaseModel):
    id: str
    fund_name: str
    category: str
    benchmark: str
    fund_manager: Optional[str] = None
    metrics: List[MutualFundMetricSchema] = []

    model_config = ConfigDict(from_attributes=True)


class MutualFundCreateOrUpdate(BaseModel):
    fund_name: str = Field(..., max_length=255)
    category: str = Field(..., max_length=100)
    benchmark: str = Field(..., max_length=255)
    fund_manager: Optional[str] = None
    metrics: List[MutualFundMetricSchema] = []


# =====================================================================
# Company Research Endpoints
# =====================================================================

@router.get("/companies", response_model=List[CompanyResponse])
async def list_companies(
    sector: Optional[str] = Query(None, description="Filter by economic sector"),
    search: Optional[str] = Query(None, description="Search by name or ticker symbol"),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves tracked research companies with audited fundamental metrics."""
    stmt = select(Company).options(selectinload(Company.metrics)).order_by(Company.symbol)

    if sector:
        stmt = stmt.where(Company.sector.ilike(f"%{sector}%"))
    if search:
        search_filter = or_(
            Company.symbol.ilike(f"%{search}%"),
            Company.name.ilike(f"%{search}%")
        )
        stmt = stmt.where(search_filter)

    result = await db.execute(stmt)
    companies = result.scalars().all()

    # If database is completely unseeded, auto-seed and reload
    if not companies and not sector and not search:
        logger.info("Companies table is empty. Auto-seeding verified company records...")
        await seed_company_data(db)
        result = await db.execute(stmt)
        companies = result.scalars().all()

    return companies


@router.get("/companies/{symbol_or_id}", response_model=CompanyResponse)
async def get_company(symbol_or_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieves a single research company by ticker symbol (e.g. 'AAPL') or UUID."""
    stmt = (
        select(Company)
        .where(or_(Company.symbol == symbol_or_id.upper(), Company.id == symbol_or_id))
        .options(selectinload(Company.metrics))
    )
    result = await db.execute(stmt)
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company '{symbol_or_id}' not found.")
    return company


@router.post("/companies", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def upsert_company(
    payload: CompanyCreateOrUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Creates or updates a company record and associated metrics.
    Ensures financial research data can be dynamically refreshed and updated over time.
    """
    stmt = select(Company).where(Company.symbol == payload.symbol.upper()).options(selectinload(Company.metrics))
    result = await db.execute(stmt)
    company = result.scalar_one_or_none()

    if not company:
        company = Company(
            symbol=payload.symbol.upper(),
            name=payload.name,
            sector=payload.sector,
            industry=payload.industry,
            description=payload.description
        )
        db.add(company)
        await db.flush()
    else:
        company.name = payload.name
        company.sector = payload.sector
        company.industry = payload.industry
        if payload.description:
            company.description = payload.description

    # Update or add metrics
    for m in payload.metrics:
        m_stmt = select(CompanyMetric).where(
            CompanyMetric.company_id == company.id,
            CompanyMetric.fiscal_year == m.fiscal_year
        )
        m_res = await db.execute(m_stmt)
        metric_rec = m_res.scalar_one_or_none()

        if metric_rec:
            metric_rec.revenue = m.revenue
            metric_rec.revenue_growth = m.revenue_growth
            metric_rec.net_profit = m.net_profit
            metric_rec.profit_growth = m.profit_growth
            metric_rec.roe = m.roe
            metric_rec.roce = m.roce
            metric_rec.debt_to_equity = m.debt_to_equity
            metric_rec.operating_cash_flow = m.operating_cash_flow
            metric_rec.pe_ratio = m.pe_ratio
            metric_rec.market_cap = m.market_cap
        else:
            metric_rec = CompanyMetric(
                company_id=company.id,
                fiscal_year=m.fiscal_year,
                revenue=m.revenue,
                revenue_growth=m.revenue_growth,
                net_profit=m.net_profit,
                profit_growth=m.profit_growth,
                roe=m.roe,
                roce=m.roce,
                debt_to_equity=m.debt_to_equity,
                operating_cash_flow=m.operating_cash_flow,
                pe_ratio=m.pe_ratio,
                market_cap=m.market_cap
            )
            db.add(metric_rec)

    await db.commit()
    logger.info(f"Upserted company research record: {company.symbol}")
    
    # Reload with selectinload so relationship is safely populated for serialization
    stmt_reload = select(Company).where(Company.id == company.id).options(selectinload(Company.metrics))
    res_reload = await db.execute(stmt_reload)
    return res_reload.scalar_one()


# =====================================================================
# Mutual Fund Research Endpoints
# =====================================================================

@router.get("/mutual-funds", response_model=List[MutualFundResponse])
async def list_mutual_funds(
    category: Optional[str] = Query(None, description="Filter by fund category"),
    risk_level: Optional[str] = Query(None, description="Filter by risk rating ('Low', 'Moderate', 'High')"),
    search: Optional[str] = Query(None, description="Search by fund name"),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves tracked mutual funds and audited performance metrics."""
    stmt = select(MutualFund).options(selectinload(MutualFund.metrics)).order_by(MutualFund.fund_name)

    if category:
        stmt = stmt.where(MutualFund.category.ilike(f"%{category}%"))
    if search:
        stmt = stmt.where(MutualFund.fund_name.ilike(f"%{search}%"))

    result = await db.execute(stmt)
    funds = result.scalars().all()

    # If database is unseeded, auto-seed baseline funds
    if not funds and not category and not search:
        logger.info("Mutual funds table is empty. Auto-seeding verified mutual fund records...")
        await seed_mutual_fund_data(db)
        result = await db.execute(stmt)
        funds = result.scalars().all()

    # Filter by risk level in memory if requested
    if risk_level:
        funds = [
            f for f in funds 
            if any(m.risk_level.lower() == risk_level.lower() for m in f.metrics)
        ]

    return funds


@router.get("/mutual-funds/{fund_id}", response_model=MutualFundResponse)
async def get_mutual_fund(fund_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieves a single mutual fund by ID or exact name."""
    stmt = (
        select(MutualFund)
        .where(or_(MutualFund.id == fund_id, MutualFund.fund_name == fund_id))
        .options(selectinload(MutualFund.metrics))
    )
    result = await db.execute(stmt)
    fund = result.scalar_one_or_none()
    if not fund:
        raise HTTPException(status_code=404, detail=f"Mutual fund '{fund_id}' not found.")
    return fund


@router.post("/mutual-funds", response_model=MutualFundResponse, status_code=status.HTTP_201_CREATED)
async def upsert_mutual_fund(
    payload: MutualFundCreateOrUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Creates or updates a mutual fund factsheet record.
    Enables ongoing performance updates and portfolio rebalancing tracking.
    """
    stmt = select(MutualFund).where(MutualFund.fund_name == payload.fund_name).options(selectinload(MutualFund.metrics))
    result = await db.execute(stmt)
    fund = result.scalar_one_or_none()

    if not fund:
        fund = MutualFund(
            fund_name=payload.fund_name,
            category=payload.category,
            benchmark=payload.benchmark,
            fund_manager=payload.fund_manager
        )
        db.add(fund)
        await db.flush()
    else:
        fund.category = payload.category
        fund.benchmark = payload.benchmark
        if payload.fund_manager:
            fund.fund_manager = payload.fund_manager

    # Update or add metrics
    for m in payload.metrics:
        m_stmt = select(MutualFundMetric).where(MutualFundMetric.fund_id == fund.id)
        m_res = await db.execute(m_stmt)
        metric_rec = m_res.scalar_one_or_none()

        if metric_rec:
            metric_rec.aum = m.aum
            metric_rec.expense_ratio = m.expense_ratio
            metric_rec.risk_level = m.risk_level
            metric_rec.return_3yr = m.return_3yr
            metric_rec.return_5yr = m.return_5yr
            metric_rec.exit_load = m.exit_load
            metric_rec.portfolio_holdings = m.portfolio_holdings
        else:
            metric_rec = MutualFundMetric(
                fund_id=fund.id,
                aum=m.aum,
                expense_ratio=m.expense_ratio,
                risk_level=m.risk_level,
                return_3yr=m.return_3yr,
                return_5yr=m.return_5yr,
                exit_load=m.exit_load,
                portfolio_holdings=m.portfolio_holdings
            )
            db.add(metric_rec)

    await db.commit()
    logger.info(f"Upserted mutual fund research record: {fund.fund_name}")

    # Reload with selectinload so relationship is safely populated for serialization
    stmt_reload = select(MutualFund).where(MutualFund.id == fund.id).options(selectinload(MutualFund.metrics))
    res_reload = await db.execute(stmt_reload)
    return res_reload.scalar_one()


@router.post("/seed", status_code=status.HTTP_200_OK)
async def seed_research_data(db: AsyncSession = Depends(get_db)):
    """Explicitly triggers population of verified company and mutual fund records."""
    comp_count = await seed_company_data(db)
    fund_count = await seed_mutual_fund_data(db)
    return {
        "status": "success",
        "message": f"Seeded {comp_count} new companies and {fund_count} new mutual funds."
    }
