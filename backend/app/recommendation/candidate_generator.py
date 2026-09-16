"""
FinAdvisor — Candidate Generator
Queries and standardizes companies and mutual funds from the research data layer
into unified CandidateAsset models with normalized risk and horizon classifications.
"""

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.database.models import Company, CompanyMetric, MutualFund, MutualFundMetric
from backend.app.utils.logger import logger


class CandidateAsset(BaseModel):
    """Unified representation of an investable asset for matching and ranking."""
    id: str
    asset_name: str
    asset_type: str  # 'Company' or 'Mutual Fund'
    symbol_or_code: str
    sector_or_category: str
    risk_level: str  # 'Low', 'Moderate', 'High', 'Very High'
    recommended_horizon: str  # 'Short', 'Medium', 'Long'
    financial_metrics: Dict[str, Any] = Field(default_factory=dict)
    source_reference: str


def classify_company_risk_and_horizon(
    company: Company,
    metric: Optional[CompanyMetric]
) -> Tuple[str, str]:
    """
    Deterministically computes inherent risk tier and suitable horizon
    for an individual equity stock based on valuation, leverage, and profitability.
    """
    if not metric:
        return "Moderate", "Long"

    debt_to_equity = metric.debt_to_equity if metric.debt_to_equity is not None else 0.5
    pe_ratio = metric.pe_ratio if metric.pe_ratio is not None else 25.0
    roe = metric.roe if metric.roe is not None else 15.0

    # Risk evaluation
    if debt_to_equity > 1.5 or pe_ratio > 50.0:
        risk = "High"
    elif debt_to_equity > 0.8 or pe_ratio > 35.0:
        risk = "Moderate"
    elif debt_to_equity <= 0.4 and roe >= 20.0:
        risk = "Moderate"  # Blue-chip quality equity
    else:
        risk = "Moderate"

    # Equities require at least Medium or Long horizon to navigate drawdown volatility
    if risk == "High" or pe_ratio > 30.0:
        horizon = "Long"
    else:
        horizon = "Medium"

    return risk, horizon


def classify_fund_horizon(
    fund: MutualFund,
    metric: Optional[MutualFundMetric]
) -> str:
    """
    Deterministically maps fund asset category and duration to a recommended horizon.
    """
    cat = (fund.category or "").lower()
    if "liquid" in cat or "debt" in cat or "money market" in cat or "overnight" in cat:
        return "Short"
    elif "hybrid" in cat or "balanced" in cat or "arbitrage" in cat:
        return "Medium"
    elif "large cap" in cat:
        return "Medium"
    else:
        # Flexi cap, mid cap, small cap, thematic
        return "Long"


async def generate_candidates(db: AsyncSession) -> List[CandidateAsset]:
    """
    Loads all companies and mutual funds from the database, transforming them
    into a standardized universe of CandidateAsset instances.
    """
    candidates: List[CandidateAsset] = []

    # 1. Fetch Companies with eager-loaded metrics
    comp_stmt = select(Company).options(selectinload(Company.metrics))
    comp_res = await db.execute(comp_stmt)
    companies = comp_res.scalars().all()

    for comp in companies:
        latest_metric: Optional[CompanyMetric] = None
        if comp.metrics:
            # Sort by fiscal_year descending to get the most recent audit
            sorted_metrics = sorted(comp.metrics, key=lambda m: m.fiscal_year, reverse=True)
            latest_metric = sorted_metrics[0]

        risk_level, horizon = classify_company_risk_and_horizon(comp, latest_metric)

        metrics_dict: Dict[str, Any] = {}
        source_ref = f"{comp.symbol} Company Profile"
        if latest_metric:
            metrics_dict = {
                "fiscal_year": latest_metric.fiscal_year,
                "revenue": latest_metric.revenue,
                "revenue_growth": latest_metric.revenue_growth,
                "net_profit": latest_metric.net_profit,
                "profit_growth": latest_metric.profit_growth,
                "roe": latest_metric.roe,
                "roce": latest_metric.roce,
                "debt_to_equity": latest_metric.debt_to_equity,
                "operating_cash_flow": latest_metric.operating_cash_flow,
                "pe_ratio": latest_metric.pe_ratio,
                "market_cap": latest_metric.market_cap,
            }
            source_ref = f"FY{latest_metric.fiscal_year} Audited Financials"

        candidates.append(
            CandidateAsset(
                id=f"comp-{comp.id}",
                asset_name=comp.name,
                asset_type="Company",
                symbol_or_code=comp.symbol,
                sector_or_category=comp.sector,
                risk_level=risk_level,
                recommended_horizon=horizon,
                financial_metrics=metrics_dict,
                source_reference=source_ref
            )
        )

    # 2. Fetch Mutual Funds with eager-loaded metrics
    fund_stmt = select(MutualFund).options(selectinload(MutualFund.metrics))
    fund_res = await db.execute(fund_stmt)
    funds = fund_res.scalars().all()

    for fund in funds:
        latest_fund_metric: Optional[MutualFundMetric] = None
        if fund.metrics:
            latest_fund_metric = fund.metrics[-1]

        risk_level = "Moderate"
        if latest_fund_metric and latest_fund_metric.risk_level:
            risk_level = latest_fund_metric.risk_level

        horizon = classify_fund_horizon(fund, latest_fund_metric)

        fund_metrics_dict: Dict[str, Any] = {}
        source_ref = f"{fund.fund_name} Factsheet"
        if latest_fund_metric:
            fund_metrics_dict = {
                "aum": latest_fund_metric.aum,
                "expense_ratio": latest_fund_metric.expense_ratio,
                "risk_level": latest_fund_metric.risk_level,
                "return_3yr": latest_fund_metric.return_3yr,
                "return_5yr": latest_fund_metric.return_5yr,
                "exit_load": latest_fund_metric.exit_load,
                "portfolio_holdings": latest_fund_metric.portfolio_holdings or [],
                "benchmark": fund.benchmark
            }
            source_ref = f"Factsheet ({fund.benchmark})"

        candidates.append(
            CandidateAsset(
                id=f"fund-{fund.id}",
                asset_name=fund.fund_name,
                asset_type="Mutual Fund",
                symbol_or_code=fund.fund_name.split()[0].upper(),
                sector_or_category=fund.category,
                risk_level=risk_level,
                recommended_horizon=horizon,
                financial_metrics=fund_metrics_dict,
                source_reference=source_ref
            )
        )

    logger.info(f"Generated {len(candidates)} candidate assets for recommendation screening.")
    return candidates
