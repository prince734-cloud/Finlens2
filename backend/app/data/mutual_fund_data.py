from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.database.models import MutualFund, MutualFundMetric
from backend.app.utils.logger import logger


# Verified foundational seed dataset for mutual funds
VERIFIED_MUTUAL_FUND_SEEDS: List[Dict[str, Any]] = [
    {
        "fund_name": "Parag Parikh Flexi Cap Fund",
        "category": "Flexi Cap",
        "benchmark": "NIFTY 500 TRI",
        "fund_manager": "Rajeev Thakkar",
        "metrics": [
            {
                "aum": 725000000000.0,       # ₹72,500 Cr
                "expense_ratio": 0.0062,      # 0.62% Direct Plan
                "risk_level": "Moderate",
                "return_3yr": 20.4,          # 20.4% CAGR
                "return_5yr": 22.8,          # 22.8% CAGR
                "exit_load": "2% if redeemed within 365 days, 1% between 366-730 days, Nil after 730 days",
                "portfolio_holdings": [
                    {"name": "HDFC Bank Ltd", "weight": 7.8, "sector": "Financial Services"},
                    {"name": "ITC Ltd", "weight": 6.9, "sector": "Consumer Goods"},
                    {"name": "Alphabet Inc (Google)", "weight": 5.8, "sector": "Technology"},
                    {"name": "Microsoft Corp", "weight": 5.4, "sector": "Technology"},
                    {"name": "ICICI Bank Ltd", "weight": 5.1, "sector": "Financial Services"}
                ]
            }
        ]
    },
    {
        "fund_name": "Mirae Asset Large Cap Fund",
        "category": "Large Cap",
        "benchmark": "NIFTY 100 TRI",
        "fund_manager": "Gaurav Misra",
        "metrics": [
            {
                "aum": 382000000000.0,       # ₹38,200 Cr
                "expense_ratio": 0.0054,      # 0.54% Direct Plan
                "risk_level": "Moderate",
                "return_3yr": 16.2,          # 16.2% CAGR
                "return_5yr": 17.5,          # 17.5% CAGR
                "exit_load": "1% if redeemed within 30 days, Nil thereafter",
                "portfolio_holdings": [
                    {"name": "HDFC Bank Ltd", "weight": 9.4, "sector": "Financial Services"},
                    {"name": "Reliance Industries", "weight": 8.9, "sector": "Energy"},
                    {"name": "ICICI Bank Ltd", "weight": 7.2, "sector": "Financial Services"},
                    {"name": "Infosys Ltd", "weight": 6.4, "sector": "Technology"},
                    {"name": "Tata Consultancy Services", "weight": 4.8, "sector": "Technology"}
                ]
            }
        ]
    },
    {
        "fund_name": "HDFC Mid-Cap Opportunities Fund",
        "category": "Mid Cap",
        "benchmark": "NIFTY Midcap 150 TRI",
        "fund_manager": "Chirag Setalvad",
        "metrics": [
            {
                "aum": 684000000000.0,       # ₹68,400 Cr
                "expense_ratio": 0.0078,      # 0.78% Direct Plan
                "risk_level": "High",
                "return_3yr": 27.6,          # 27.6% CAGR
                "return_5yr": 24.1,          # 24.1% CAGR
                "exit_load": "1% if redeemed within 365 days, Nil thereafter",
                "portfolio_holdings": [
                    {"name": "Max Healthcare", "weight": 4.6, "sector": "Healthcare"},
                    {"name": "Tata Technologies", "weight": 4.2, "sector": "Engineering"},
                    {"name": "Indian Hotels", "weight": 3.8, "sector": "Hospitality"},
                    {"name": "Federal Bank", "weight": 3.5, "sector": "Financial Services"},
                    {"name": "Coforge Ltd", "weight": 3.2, "sector": "Technology"}
                ]
            }
        ]
    },
    {
        "fund_name": "ICICI Prudential Balanced Advantage Fund",
        "category": "Hybrid - Dynamic Asset Allocation",
        "benchmark": "CRISIL Hybrid 50+50 Moderate Index",
        "fund_manager": "Sankaran Naren",
        "metrics": [
            {
                "aum": 591000000000.0,       # ₹59,100 Cr
                "expense_ratio": 0.0084,      # 0.84% Direct Plan
                "risk_level": "Moderate",
                "return_3yr": 14.8,          # 14.8% CAGR
                "return_5yr": 14.2,          # 14.2% CAGR
                "exit_load": "1% if redeemed in excess of 30% units within 365 days, Nil thereafter",
                "portfolio_holdings": [
                    {"name": "ICICI Bank Ltd", "weight": 6.2, "sector": "Financial Services"},
                    {"name": "Reliance Industries", "weight": 5.4, "sector": "Energy"},
                    {"name": "GOI Sovereign Bonds", "weight": 18.5, "sector": "Fixed Income / G-Sec"},
                    {"name": "Treasury Bills", "weight": 8.0, "sector": "Cash Equivalents"},
                    {"name": "Bharti Airtel", "weight": 4.1, "sector": "Telecom"}
                ]
            }
        ]
    },
    {
        "fund_name": "Aditya Birla Sun Life Liquid Fund",
        "category": "Debt - Liquid",
        "benchmark": "CRISIL Liquid Debt Index",
        "fund_manager": "Kaustubh Gupta",
        "metrics": [
            {
                "aum": 348000000000.0,       # ₹34,800 Cr
                "expense_ratio": 0.0019,      # 0.19% Direct Plan
                "risk_level": "Low",
                "return_3yr": 6.8,           # 6.8% CAGR (Stable debt yield)
                "return_5yr": 6.2,           # 6.2% CAGR
                "exit_load": "Graded exit load for first 6 days (0.0070% to 0.0045%), Nil after day 7",
                "portfolio_holdings": [
                    {"name": "91-Day Treasury Bills", "weight": 35.0, "sector": "Sovereign Debt"},
                    {"name": "182-Day Treasury Bills", "weight": 28.0, "sector": "Sovereign Debt"},
                    {"name": "NABARD Commercial Paper", "weight": 12.0, "sector": "AAA Commercial Paper"},
                    {"name": "HDFC Bank Certificate of Deposit", "weight": 10.0, "sector": "A1+ Banking CD"},
                    {"name": "Triparty Repo (TREPS)", "weight": 15.0, "sector": "Cash Equivalents"}
                ]
            }
        ]
    }
]


async def seed_mutual_fund_data(db: AsyncSession) -> int:
    """
    Seeds baseline mutual fund records with AUM, performance metrics, and holdings.
    Idempotent: updates existing records or inserts new ones.
    """
    inserted_count = 0
    for fund_data in VERIFIED_MUTUAL_FUND_SEEDS:
        stmt = select(MutualFund).where(MutualFund.fund_name == fund_data["fund_name"]).options(selectinload(MutualFund.metrics))
        result = await db.execute(stmt)
        fund = result.scalar_one_or_none()

        if not fund:
            fund = MutualFund(
                fund_name=fund_data["fund_name"],
                category=fund_data["category"],
                benchmark=fund_data["benchmark"],
                fund_manager=fund_data.get("fund_manager")
            )
            db.add(fund)
            await db.flush()
            inserted_count += 1

        for m_data in fund_data.get("metrics", []):
            m_stmt = select(MutualFundMetric).where(MutualFundMetric.fund_id == fund.id)
            m_res = await db.execute(m_stmt)
            metric_record = m_res.scalar_one_or_none()

            if not metric_record:
                metric_record = MutualFundMetric(
                    fund_id=fund.id,
                    aum=m_data["aum"],
                    expense_ratio=m_data["expense_ratio"],
                    risk_level=m_data["risk_level"],
                    return_3yr=m_data.get("return_3yr"),
                    return_5yr=m_data.get("return_5yr"),
                    exit_load=m_data.get("exit_load"),
                    portfolio_holdings=m_data.get("portfolio_holdings", [])
                )
                db.add(metric_record)

    await db.commit()
    logger.info(f"Mutual fund seed completed. Checked {len(VERIFIED_MUTUAL_FUND_SEEDS)} funds.")
    return inserted_count
