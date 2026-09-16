import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.database.models import Document, FinancialKPI
from backend.app.rag.hybrid_search import hybrid_search_engine
from backend.app.rag.retriever import RetrievedChunk
from backend.app.services.llm_service import llm_service
from backend.app.utils.logger import logger


# =====================================================================
# Pydantic Schemas for Structured KPI Extraction
# =====================================================================

class FinancialKPIModel(BaseModel):
    """
    Structured financial KPI model representing primary quantitative metrics
    and qualitative factors extracted from company annual reports (10-K / reports).
    """
    company: str = Field("Unknown Company", description="Legal company name (e.g., 'Apple Inc.')")
    financial_year: int = Field(2024, description="Fiscal year of reporting (e.g., 2024)")
    currency: str = Field("USD", description="Currency symbol or 3-letter ISO code (e.g., 'USD', 'INR')")
    
    # Income Statement Metrics
    revenue: Optional[float] = Field(
        None, 
        description="Total revenue / net sales in absolute currency value (e.g., 391035000000.0)"
    )
    net_income: Optional[float] = Field(
        None, 
        description="Net income / net earnings after tax in absolute currency value"
    )
    operating_income: Optional[float] = Field(
        None, 
        description="Operating income / operating profit / EBIT in absolute currency value"
    )
    
    # Cash Flow & Balance Sheet Metrics
    operating_cash_flow: Optional[float] = Field(
        None, 
        description="Net cash provided by operating activities in absolute currency value"
    )
    total_assets: Optional[float] = Field(
        None, 
        description="Total assets from the consolidated balance sheet"
    )
    total_liabilities: Optional[float] = Field(
        None, 
        description="Total liabilities from the consolidated balance sheet"
    )
    
    # Growth Rates (Expressed as decimals, e.g. 0.082 for 8.2%)
    revenue_growth: Optional[float] = Field(
        None, 
        description="Year-over-year revenue growth rate as a decimal (e.g. 0.082 = 8.2%, -0.025 = -2.5%)"
    )
    net_income_growth: Optional[float] = Field(
        None, 
        description="Year-over-year net income growth rate as a decimal"
    )
    
    # Qualitative Drivers & Risks
    growth_drivers: List[str] = Field(
        default_factory=list, 
        description="Top 3 to 5 major strategic business drivers, products, or service segments driving growth"
    )
    risk_factors: List[str] = Field(
        default_factory=list, 
        description="Top 3 to 5 key operational, market, geopolitical, or competitive risk factors"
    )

    model_config = ConfigDict(extra="ignore")


class KPIExtractionResult(BaseModel):
    """Result envelope for an extraction operation, including metadata and citations."""
    document_id: str
    document_name: str
    kpi: FinancialKPIModel
    extracted_from_pages: List[int] = Field(default_factory=list)
    confidence_score: float = 1.0
    extraction_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(from_attributes=True)


# =====================================================================
# Financial Number Normalizer
# =====================================================================

def normalize_financial_number(raw_val: Any) -> Optional[float]:
    """
    Normalizes human-formatted financial string values into standard floats.
    Examples:
      - "$391,035M" or "391035 million" -> 391035000000.0
      - "$112.5B" -> 112500000000.0
      - "8.2%" -> 0.082
      - "(5,200)" -> -5200.0 (accounting negative)
    """
    if raw_val is None:
        return None
    if isinstance(raw_val, (int, float)):
        return float(raw_val)

    val_str = str(raw_val).strip()
    if not val_str or val_str.lower() in ("n/a", "none", "null", "—", "-"):
        return None

    # Handle accounting brackets: (1,234) -> -1234
    is_negative = False
    if val_str.startswith("(") and val_str.endswith(")"):
        is_negative = True
        val_str = val_str[1:-1].strip()
    elif val_str.startswith("-"):
        is_negative = True
        val_str = val_str[1:].strip()

    # Handle percentage
    is_percentage = "%" in val_str

    # Clean characters
    val_str = val_str.replace("$", "").replace("₹", "").replace("€", "").replace("£", "").replace(",", "")
    val_str = val_str.replace("%", "").strip()

    multiplier = 1.0
    val_lower = val_str.lower()
    if "billion" in val_lower or val_lower.endswith("b"):
        multiplier = 1e9
        val_str = re.sub(r"[^\d.]", "", val_str)
    elif "million" in val_lower or val_lower.endswith("m"):
        multiplier = 1e6
        val_str = re.sub(r"[^\d.]", "", val_str)
    elif "trillion" in val_lower or val_lower.endswith("t"):
        multiplier = 1e12
        val_str = re.sub(r"[^\d.]", "", val_str)
    elif "thousand" in val_lower or val_lower.endswith("k"):
        multiplier = 1e3
        val_str = re.sub(r"[^\d.]", "", val_str)
    elif "cr" in val_lower or "crore" in val_lower:
        multiplier = 1e7
        val_str = re.sub(r"[^\d.]", "", val_str)
    else:
        val_str = re.sub(r"[^\d.]", "", val_str)

    try:
        num = float(val_str) * multiplier
        if is_percentage:
            num = round(num / 100.0, 6)
        else:
            num = round(num, 4)
        return -num if is_negative else num
    except (ValueError, TypeError):
        return None


# =====================================================================
# Core KPI Extractor Service
# =====================================================================

class FinancialKPIExtractor:
    """
    Extracts structured financial KPIs from annual reports and 10-K filings.
    
    Architecture:
    1. Targeted Retrieval: Uses Hybrid Search (Dense + BM25) to isolate:
       - Operations / Income Statement chunks
       - Balance Sheet chunks
       - Cash Flow chunks
       - MD&A / Risk Factors chunks
    2. Context Formatting with page & section citations
    3. Structured Prompting requiring strict JSON conforming to FinancialKPIModel
    4. Data Validation and Normalization
    5. Persistence to PostgreSQL / Database
    """

    TARGET_QUERIES = [
        ("operations", "Consolidated Statements of Operations total net sales revenue operating income net income diluted earnings per share"),
        ("balance_sheet", "Consolidated Balance Sheets total assets current assets total liabilities current liabilities stockholders equity"),
        ("cash_flows", "Consolidated Statements of Cash Flows cash generated by operating activities capital expenditures free cash flow"),
        ("risks_drivers", "Item 1A Risk Factors key strategic growth drivers business performance product services segment foreign currency risk")
    ]

    async def extract_kpis_for_document(
        self,
        document_id: str,
        db: AsyncSession
    ) -> KPIExtractionResult:
        """
        Executes targeted extraction on an uploaded document and persists to database.
        """
        # 1. Fetch document record
        stmt = select(Document).where(Document.id == document_id)
        result = await db.execute(stmt)
        doc = result.scalar_one_or_none()

        if not doc:
            raise ValueError(f"Document with ID '{document_id}' not found.")

        logger.info(f"Starting KPI extraction for '{doc.filename}' (Company: {doc.company_name})...")

        # 2. Targeted Multi-Section Retrieval
        retrieved_chunks: List[RetrievedChunk] = []
        seen_chunk_ids = set()
        pages_referenced = set()

        for category, query in self.TARGET_QUERIES:
            try:
                # Query hybrid search filtered strictly to this document
                chunks = hybrid_search_engine.search(
                    query=query,
                    top_k=3,
                    where={"document_id": document_id}
                )
                for c in chunks:
                    if c.id not in seen_chunk_ids:
                        seen_chunk_ids.add(c.id)
                        retrieved_chunks.append(c)
                        pages_referenced.add(c.page_number)
            except Exception as e:
                logger.warning(f"Error during targeted retrieval for category '{category}': {e}")

        if not retrieved_chunks:
            # Fallback to general retrieval if section queries yielded nothing
            retrieved_chunks = hybrid_search_engine.search(
                query="Financial statements summary revenue net income assets liabilities risks",
                top_k=6,
                where={"document_id": document_id}
            )
            for c in retrieved_chunks:
                pages_referenced.add(c.page_number)

        if not retrieved_chunks:
            raise ValueError(f"No indexed text found for document '{doc.filename}'. Please index first.")

        # 3. Format context with explicit section and page headers
        context_blocks = []
        for c in retrieved_chunks:
            context_blocks.append(
                f"--- [Page {c.page_number} | Section: {c.section}] ---\n{c.content}"
            )
        combined_context = "\n\n".join(context_blocks)

        # 4. Construct Structured Prompt
        system_instruction = (
            "You are a CFA-level quantitative financial analyst specializing in 10-K and financial report extraction.\n"
            "Your objective is to extract verifiable, structured Key Performance Indicators (KPIs) from the provided financial report excerpts.\n\n"
            "CRITICAL RULES:\n"
            "1. Output MUST be a single, valid JSON object conforming strictly to the schema provided.\n"
            "2. Extract EXACT absolute numbers where possible. If the table states figures are 'in millions', multiply by 1,000,000.\n"
            "3. If a metric (e.g. total assets) is not found in the context, set it to null. NEVER fabricate or invent figures.\n"
            "4. Express growth rates as decimals (e.g. +8.2% -> 0.082, -4.5% -> -0.045).\n"
            "5. Extract 3-5 concise, specific growth drivers and 3-5 distinct major risk factors mentioned in the text.\n"
            "6. DO NOT wrap JSON in conversational text or markdown other than standard ```json ... ``` tags."
        )

        extraction_prompt = f"""
TARGET COMPANY: {doc.company_name or 'Auto-detect'}
REPORTING YEAR: {doc.financial_year or 2024}

JSON SCHEMA REQUIREMENT:
{{
  "company": "string (Company Name)",
  "financial_year": integer (e.g. 2024),
  "currency": "string (e.g. USD, INR)",
  "revenue": number or null (absolute total net sales/revenue),
  "net_income": number or null (absolute net income),
  "operating_income": number or null (absolute operating income),
  "operating_cash_flow": number or null (absolute operating cash flow),
  "total_assets": number or null (absolute total assets),
  "total_liabilities": number or null (absolute total liabilities),
  "revenue_growth": number or null (decimal e.g. 0.082),
  "net_income_growth": number or null (decimal e.g. -0.034),
  "growth_drivers": ["driver 1", "driver 2", ...],
  "risk_factors": ["risk 1", "risk 2", ...]
}}

DOCUMENT CONTEXT:
{combined_context}

Extract the financial KPIs strictly according to the context:
"""

        # 5. Call LLM for Structured Extraction
        response_text = await llm_service.generate_grounded_answer(
            query="Extract the financial KPIs in strict JSON according to the schema.",
            formatted_context=combined_context,
            custom_system_prompt=system_instruction
        )

        # 6. Parse and Validate JSON
        parsed_kpi = self._parse_json_response(
            response_text=response_text,
            fallback_company=doc.company_name or "Unknown Company",
            fallback_year=doc.financial_year or 2024
        )

        # 7. Normalize all financial fields
        parsed_kpi.revenue = normalize_financial_number(parsed_kpi.revenue)
        parsed_kpi.net_income = normalize_financial_number(parsed_kpi.net_income)
        parsed_kpi.operating_income = normalize_financial_number(parsed_kpi.operating_income)
        parsed_kpi.operating_cash_flow = normalize_financial_number(parsed_kpi.operating_cash_flow)
        parsed_kpi.total_assets = normalize_financial_number(parsed_kpi.total_assets)
        parsed_kpi.total_liabilities = normalize_financial_number(parsed_kpi.total_liabilities)
        parsed_kpi.revenue_growth = normalize_financial_number(parsed_kpi.revenue_growth)
        parsed_kpi.net_income_growth = normalize_financial_number(parsed_kpi.net_income_growth)

        # 8. Persist Extracted KPIs to Database (Upsert)
        await self._save_kpis_to_db(
            document_id=doc.id,
            kpi_data=parsed_kpi,
            db=db
        )

        logger.info(f"Successfully extracted and persisted KPIs for '{doc.filename}' (Revenue: {parsed_kpi.revenue})")

        return KPIExtractionResult(
            document_id=doc.id,
            document_name=doc.filename,
            kpi=parsed_kpi,
            extracted_from_pages=sorted(list(pages_referenced)),
            confidence_score=0.95
        )

    def _parse_json_response(
        self,
        response_text: str,
        fallback_company: str,
        fallback_year: int
    ) -> FinancialKPIModel:
        """Extracts and parses JSON object from LLM response with fallback repair."""
        clean_text = response_text.strip()
        
        # Remove markdown code fences if present
        if "```json" in clean_text:
            clean_text = clean_text.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_text:
            clean_text = clean_text.split("```")[1].split("```")[0].strip()

        # Find first '{' and last '}'
        start_idx = clean_text.find("{")
        end_idx = clean_text.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = clean_text[start_idx : end_idx + 1]
        else:
            json_str = clean_text

        try:
            data = json.loads(json_str)
            if isinstance(data, dict):
                # Normalize common LLM key naming variations
                if not data.get("company"):
                    data["company"] = data.get("company_name") or fallback_company
                if not data.get("financial_year"):
                    data["financial_year"] = data.get("fiscal_year") or fallback_year
                if data.get("revenue") is None:
                    data["revenue"] = data.get("total_revenue") or data.get("net_sales")
                if data.get("net_income") is None:
                    data["net_income"] = data.get("net_profit") or data.get("profit_after_tax")
                if data.get("operating_income") is None:
                    data["operating_income"] = data.get("operating_profit") or data.get("ebit")
                if data.get("operating_cash_flow") is None:
                    data["operating_cash_flow"] = data.get("cash_flow_from_operations") or data.get("operating_cashflow")
                return FinancialKPIModel.model_validate(data)
        except Exception as e:
            logger.warning(f"Standard JSON parse failed: {e}. Attempting regex recovery...")

        return self._regex_repair_kpi(response_text, fallback_company, fallback_year)

    def _regex_repair_kpi(
        self,
        text: str,
        fallback_company: str,
        fallback_year: int
    ) -> FinancialKPIModel:
        """Heuristic fallback extraction in case the LLM produced slight JSON syntax anomalies."""
        def extract_float(*field_names: str) -> Optional[float]:
            for field_name in field_names:
                pattern = rf'"{field_name}"\s*:\s*([0-9.,-]+)'
                m = re.search(pattern, text, re.IGNORECASE)
                if m:
                    res = normalize_financial_number(m.group(1))
                    if res is not None:
                        return res
            return None

        def extract_list(field_name: str) -> List[str]:
            pattern = rf'"{field_name}"\s*:\s*\[(.*?)\]'
            m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if m:
                items = re.findall(r'"([^"]+)"', m.group(1))
                return [it.strip() for it in items if it.strip()]
            return []

        return FinancialKPIModel(
            company=fallback_company,
            financial_year=fallback_year,
            currency="USD",
            revenue=extract_float("revenue", "total_revenue", "net_sales"),
            net_income=extract_float("net_income", "net_profit", "profit_after_tax"),
            operating_income=extract_float("operating_income", "operating_profit", "ebit"),
            operating_cash_flow=extract_float("operating_cash_flow", "cash_flow_from_operations"),
            total_assets=extract_float("total_assets"),
            total_liabilities=extract_float("total_liabilities"),
            revenue_growth=extract_float("revenue_growth"),
            net_income_growth=extract_float("net_income_growth"),
            growth_drivers=extract_list("growth_drivers"),
            risk_factors=extract_list("risk_factors")
        )

    async def _save_kpis_to_db(
        self,
        document_id: str,
        kpi_data: FinancialKPIModel,
        db: AsyncSession
    ) -> FinancialKPI:
        """Upserts financial KPIs into the relational PostgreSQL / SQLite table."""
        stmt = select(FinancialKPI).where(FinancialKPI.document_id == document_id)
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()

        if record:
            record.company_name = kpi_data.company
            record.financial_year = kpi_data.financial_year
            record.revenue = kpi_data.revenue
            record.net_income = kpi_data.net_income
            record.operating_income = kpi_data.operating_income
            record.operating_cash_flow = kpi_data.operating_cash_flow
            record.total_assets = kpi_data.total_assets
            record.total_liabilities = kpi_data.total_liabilities
            record.revenue_growth = kpi_data.revenue_growth
            record.net_income_growth = kpi_data.net_income_growth
            record.growth_drivers = kpi_data.growth_drivers
            record.risk_factors = kpi_data.risk_factors
            record.currency = kpi_data.currency
            record.extracted_at = datetime.now(timezone.utc)
        else:
            record = FinancialKPI(
                document_id=document_id,
                company_name=kpi_data.company,
                financial_year=kpi_data.financial_year,
                revenue=kpi_data.revenue,
                net_income=kpi_data.net_income,
                operating_income=kpi_data.operating_income,
                operating_cash_flow=kpi_data.operating_cash_flow,
                total_assets=kpi_data.total_assets,
                total_liabilities=kpi_data.total_liabilities,
                revenue_growth=kpi_data.revenue_growth,
                net_income_growth=kpi_data.net_income_growth,
                growth_drivers=kpi_data.growth_drivers,
                risk_factors=kpi_data.risk_factors,
                currency=kpi_data.currency,
                extracted_at=datetime.now(timezone.utc)
            )
            db.add(record)

        await db.commit()
        await db.refresh(record)
        return record


# Global singleton instance
kpi_extractor = FinancialKPIExtractor()
