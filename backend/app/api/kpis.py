from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.connection import get_db
from backend.app.database.models import Document, FinancialKPI
from backend.app.extraction.kpi_extractor import FinancialKPIModel, KPIExtractionResult, kpi_extractor
from backend.app.utils.logger import logger

router = APIRouter(prefix="/kpis", tags=["Financial KPI Extraction"])


# --- Response Schemas ---

class FinancialKPIResponse(BaseModel):
    id: str
    document_id: Optional[str] = None
    company_name: str
    financial_year: int
    currency: str
    revenue: Optional[float] = None
    net_income: Optional[float] = None
    operating_income: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    revenue_growth: Optional[float] = None
    net_income_growth: Optional[float] = None
    growth_drivers: List[str] = []
    risk_factors: List[str] = []
    extracted_at: str

    model_config = ConfigDict(from_attributes=True)


@router.post("/extract/{document_id}", response_model=KPIExtractionResult, status_code=status.HTTP_200_OK)
async def extract_document_kpis(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers structured financial KPI extraction for an uploaded document.
    Executes targeted section retrieval, LLM schema-constrained generation, 
    number normalization, and database storage.
    """
    # Check document exists
    stmt = select(Document).where(Document.id == document_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")

    if doc.status != "indexed" and doc.chunk_count == 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Document '{doc.filename}' is not indexed yet. Please process the document first."
        )

    try:
        extraction_result = await kpi_extractor.extract_kpis_for_document(
            document_id=document_id,
            db=db
        )
        return extraction_result
    except Exception as e:
        logger.error(f"KPI extraction failed for document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"KPI extraction error: {str(e)}")


@router.get("/{document_id}", response_model=FinancialKPIResponse)
async def get_document_kpis(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieves stored structured KPIs for a given document."""
    stmt = select(FinancialKPI).where(FinancialKPI.document_id == document_id)
    result = await db.execute(stmt)
    kpi = result.scalar_one_or_none()
    if not kpi:
        raise HTTPException(
            status_code=404, 
            detail=f"No extracted KPIs found for document '{document_id}'."
        )
    
    return FinancialKPIResponse(
        id=kpi.id,
        document_id=kpi.document_id,
        company_name=kpi.company_name,
        financial_year=kpi.financial_year,
        currency=kpi.currency or "USD",
        revenue=kpi.revenue,
        net_income=kpi.net_income,
        operating_income=kpi.operating_income,
        operating_cash_flow=kpi.operating_cash_flow,
        total_assets=kpi.total_assets,
        total_liabilities=kpi.total_liabilities,
        revenue_growth=kpi.revenue_growth,
        net_income_growth=kpi.net_income_growth,
        growth_drivers=kpi.growth_drivers or [],
        risk_factors=kpi.risk_factors or [],
        extracted_at=kpi.extracted_at.isoformat() if kpi.extracted_at else ""
    )


@router.get("", response_model=List[FinancialKPIResponse])
async def list_all_kpis(
    db: AsyncSession = Depends(get_db)
):
    """Lists all extracted company KPIs across all documents in the database."""
    stmt = select(FinancialKPI).order_by(FinancialKPI.extracted_at.desc())
    result = await db.execute(stmt)
    records = result.scalars().all()
    
    return [
        FinancialKPIResponse(
            id=k.id,
            document_id=k.document_id,
            company_name=k.company_name,
            financial_year=k.financial_year,
            currency=k.currency or "USD",
            revenue=k.revenue,
            net_income=k.net_income,
            operating_income=k.operating_income,
            operating_cash_flow=k.operating_cash_flow,
            total_assets=k.total_assets,
            total_liabilities=k.total_liabilities,
            revenue_growth=k.revenue_growth,
            net_income_growth=k.net_income_growth,
            growth_drivers=k.growth_drivers or [],
            risk_factors=k.risk_factors or [],
            extracted_at=k.extracted_at.isoformat() if k.extracted_at else ""
        )
        for k in records
    ]
