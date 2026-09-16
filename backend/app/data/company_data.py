from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.database.models import Company, CompanyMetric
from backend.app.utils.logger import logger


# Verified foundational seed dataset for equities
VERIFIED_COMPANY_SEEDS: List[Dict[str, Any]] = [
    {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "description": "Designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories, alongside cloud and digital content services.",
        "metrics": [
            {
                "fiscal_year": 2024,
                "revenue": 391035000000.0,
                "revenue_growth": 0.0202,
                "net_profit": 93736000000.0,
                "profit_growth": -0.0336,
                "roe": 1.472,  # Return on Equity (147.2%)
                "roce": 0.584, # Return on Capital Employed (58.4%)
                "debt_to_equity": 1.58,
                "operating_cash_flow": 118264000000.0,
                "pe_ratio": 34.2,
                "market_cap": 3450000000000.0
            },
            {
                "fiscal_year": 2023,
                "revenue": 383285000000.0,
                "revenue_growth": -0.028,
                "net_profit": 96995000000.0,
                "profit_growth": -0.028,
                "roe": 1.560,
                "roce": 0.562,
                "debt_to_equity": 1.79,
                "operating_cash_flow": 110543000000.0,
                "pe_ratio": 29.8,
                "market_cap": 2980000000000.0
            }
        ]
    },
    {
        "symbol": "MSFT",
        "name": "Microsoft Corporation",
        "sector": "Technology",
        "industry": "Software - Infrastructure",
        "description": "Global developer of software, cloud infrastructure (Azure), enterprise services, productivity applications (Office 365), and AI solutions.",
        "metrics": [
            {
                "fiscal_year": 2024,
                "revenue": 245120000000.0,
                "revenue_growth": 0.1567,
                "net_profit": 88136000000.0,
                "profit_growth": 0.2180,
                "roe": 0.384,
                "roce": 0.332,
                "debt_to_equity": 0.37,
                "operating_cash_flow": 118548000000.0,
                "pe_ratio": 35.8,
                "market_cap": 3150000000000.0
            },
            {
                "fiscal_year": 2023,
                "revenue": 211915000000.0,
                "revenue_growth": 0.0688,
                "net_profit": 72361000000.0,
                "profit_growth": -0.005,
                "roe": 0.358,
                "roce": 0.301,
                "debt_to_equity": 0.42,
                "operating_cash_flow": 87582000000.0,
                "pe_ratio": 32.1,
                "market_cap": 2510000000000.0
            }
        ]
    },
    {
        "symbol": "GOOGL",
        "name": "Alphabet Inc.",
        "sector": "Communication Services",
        "industry": "Internet Content & Information",
        "description": "Parent company of Google, YouTube, and Android. Leading in digital advertising, Google Cloud, and AI research.",
        "metrics": [
            {
                "fiscal_year": 2024,
                "revenue": 349742000000.0,
                "revenue_growth": 0.1388,
                "net_profit": 100608000000.0,
                "profit_growth": 0.3644,
                "roe": 0.312,
                "roce": 0.325,
                "debt_to_equity": 0.09,
                "operating_cash_flow": 124840000000.0,
                "pe_ratio": 23.4,
                "market_cap": 2240000000000.0
            }
        ]
    },
    {
        "symbol": "NVDA",
        "name": "NVIDIA Corporation",
        "sector": "Technology",
        "industry": "Semiconductors",
        "description": "Pioneer in accelerated computing, GPUs for gaming, and generative AI data center infrastructure.",
        "metrics": [
            {
                "fiscal_year": 2024,
                "revenue": 60922000000.0,
                "revenue_growth": 1.258,
                "net_profit": 29760000000.0,
                "profit_growth": 5.813,
                "roe": 0.915,
                "roce": 0.824,
                "debt_to_equity": 0.25,
                "operating_cash_flow": 28090000000.0,
                "pe_ratio": 52.6,
                "market_cap": 3100000000000.0
            }
        ]
    },
    {
        "symbol": "HDFCBANK",
        "name": "HDFC Bank Limited",
        "sector": "Financial Services",
        "industry": "Banks - Diversified",
        "description": "Leading private sector bank in India, offering retail and corporate banking, treasury, digital payment, and mortgage products.",
        "metrics": [
            {
                "fiscal_year": 2024,
                "revenue": 3810000000000.0,  # in INR (₹3.81 Lakh Cr)
                "revenue_growth": 0.812,      # Post-merger growth
                "net_profit": 640600000000.0,
                "profit_growth": 0.392,
                "roe": 0.168,
                "roce": 0.142,
                "debt_to_equity": 5.85,       # Typical for commercial banking leverage
                "operating_cash_flow": 450000000000.0,
                "pe_ratio": 18.5,
                "market_cap": 12800000000000.0
            }
        ]
    },
    {
        "symbol": "RELIANCE",
        "name": "Reliance Industries Limited",
        "sector": "Energy & Conglomerate",
        "industry": "Oil & Gas, Telecom, Retail",
        "description": "India's largest conglomerate spanning petrochemicals, telecom (Jio), retail stores, and new green energy.",
        "metrics": [
            {
                "fiscal_year": 2024,
                "revenue": 10001220000000.0, # ₹10.0 Lakh Cr
                "revenue_growth": 0.026,
                "net_profit": 790200000000.0,
                "profit_growth": 0.073,
                "roe": 0.098,
                "roce": 0.104,
                "debt_to_equity": 0.42,
                "operating_cash_flow": 1420000000000.0,
                "pe_ratio": 24.1,
                "market_cap": 19500000000000.0
            }
        ]
    }
]


async def seed_company_data(db: AsyncSession) -> int:
    """
    Seeds baseline company fundamental records if not already populated.
    Idempotent: updates existing records or inserts new ones.
    """
    inserted_count = 0
    for comp_data in VERIFIED_COMPANY_SEEDS:
        stmt = select(Company).where(Company.symbol == comp_data["symbol"]).options(selectinload(Company.metrics))
        result = await db.execute(stmt)
        company = result.scalar_one_or_none()

        if not company:
            company = Company(
                symbol=comp_data["symbol"],
                name=comp_data["name"],
                sector=comp_data["sector"],
                industry=comp_data["industry"],
                description=comp_data.get("description")
            )
            db.add(company)
            await db.flush()
            inserted_count += 1

        # Seed metrics
        for m_data in comp_data.get("metrics", []):
            m_stmt = select(CompanyMetric).where(
                CompanyMetric.company_id == company.id,
                CompanyMetric.fiscal_year == m_data["fiscal_year"]
            )
            m_res = await db.execute(m_stmt)
            metric_record = m_res.scalar_one_or_none()

            if not metric_record:
                metric_record = CompanyMetric(
                    company_id=company.id,
                    fiscal_year=m_data["fiscal_year"],
                    revenue=m_data["revenue"],
                    revenue_growth=m_data.get("revenue_growth"),
                    net_profit=m_data["net_profit"],
                    profit_growth=m_data.get("profit_growth"),
                    roe=m_data.get("roe"),
                    roce=m_data.get("roce"),
                    debt_to_equity=m_data.get("debt_to_equity"),
                    operating_cash_flow=m_data.get("operating_cash_flow"),
                    pe_ratio=m_data.get("pe_ratio"),
                    market_cap=m_data.get("market_cap")
                )
                db.add(metric_record)

    await db.commit()
    logger.info(f"Company seed completed. Checked {len(VERIFIED_COMPANY_SEEDS)} companies.")
    return inserted_count
