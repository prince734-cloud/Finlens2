import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.types import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


def get_utc_now() -> datetime:
    """Returns current UTC timestamp."""
    return datetime.now(timezone.utc)


class User(Base):
    """User entity representing an investor or platform user."""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    # Relationships
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    profile: Mapped[Optional["InvestmentProfile"]] = relationship("InvestmentProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    chat_messages: Mapped[List["ChatHistory"]] = relationship("ChatHistory", back_populates="user", cascade="all, delete-orphan")


class Document(Base):
    """Uploaded financial document (annual report, factsheet, 10-K, etc.)."""
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False, default="annual_report")  # annual_report, factsheet, 10k, other
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    financial_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), default="uploaded")  # uploaded, processing, indexed, failed
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    upload_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="documents")
    chunks: Mapped[List["DocumentChunk"]] = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    kpis: Mapped[List["FinancialKPI"]] = relationship("FinancialKPI", back_populates="document")


class DocumentChunk(Base):
    """Semantic chunk from an uploaded document with rich metadata."""
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    chunk_metadata: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    vector_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")


class FinancialKPI(Base):
    """Structured financial KPIs extracted from company annual reports."""
    __tablename__ = "financial_kpis"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    financial_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    
    # Financial metrics
    revenue: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    net_income: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    operating_income: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    operating_cash_flow: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_assets: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_liabilities: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    revenue_growth: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    net_income_growth: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Qualitative structured factors
    growth_drivers: Mapped[List[str]] = mapped_column(JSON, default=list)
    risk_factors: Mapped[List[str]] = mapped_column(JSON, default=list)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    # Relationships
    document: Mapped[Optional["Document"]] = relationship("Document", back_populates="kpis")


class InvestmentProfile(Base):
    """User investment profile and risk parameters."""
    __tablename__ = "investment_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    investment_amount: Mapped[float] = mapped_column(Float, nullable=False)
    monthly_investment_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0.0)
    risk_tolerance: Mapped[str] = mapped_column(String(20), nullable=False)  # 'Low', 'Moderate', 'High'
    investment_horizon: Mapped[str] = mapped_column(String(20), nullable=False)  # 'Short', 'Medium', 'Long'
    goal: Mapped[str] = mapped_column(String(50), nullable=False)  # 'Wealth creation', 'Capital preservation', 'Income', 'Other'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="profile")


class Company(Base):
    """Company profile in the financial research data layer."""
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    sector: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    industry: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    # Relationships
    metrics: Mapped[List["CompanyMetric"]] = relationship("CompanyMetric", back_populates="company", cascade="all, delete-orphan")


class CompanyMetric(Base):
    """Historical and fundamental metrics for a company."""
    __tablename__ = "company_metrics"
    __table_args__ = (
        UniqueConstraint("company_id", "fiscal_year", name="uq_company_fiscal_year"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id: Mapped[str] = mapped_column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    revenue: Mapped[float] = mapped_column(Float, nullable=False)
    revenue_growth: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    net_profit: Mapped[float] = mapped_column(Float, nullable=False)
    profit_growth: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    roe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Return on Equity (%)
    roce: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Return on Capital Employed (%)
    debt_to_equity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    operating_cash_flow: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pe_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    market_cap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="metrics")


class MutualFund(Base):
    """Mutual fund profile in the financial research data layer."""
    __tablename__ = "mutual_funds"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    fund_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # 'Large Cap', 'Flexi Cap', 'Mid Cap', 'Debt'
    benchmark: Mapped[str] = mapped_column(String(255), nullable=False)
    fund_manager: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    launch_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    # Relationships
    metrics: Mapped[List["MutualFundMetric"]] = relationship("MutualFundMetric", back_populates="fund", cascade="all, delete-orphan")


class MutualFundMetric(Base):
    """Performance and portfolio holdings metrics for a mutual fund."""
    __tablename__ = "mutual_fund_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    fund_id: Mapped[str] = mapped_column(String(36), ForeignKey("mutual_funds.id", ondelete="CASCADE"), nullable=False, index=True)
    aum: Mapped[float] = mapped_column(Float, nullable=False)  # Assets Under Management
    expense_ratio: Mapped[float] = mapped_column(Float, nullable=False)  # % e.g. 0.0075 = 0.75%
    risk_level: Mapped[str] = mapped_column(String(50), nullable=False)  # 'Low', 'Moderate', 'High', 'Very High'
    return_3yr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # CAGR %
    return_5yr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # CAGR %
    exit_load: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    portfolio_holdings: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    # Relationships
    fund: Mapped["MutualFund"] = relationship("MutualFund", back_populates="metrics")


class ChatHistory(Base):
    """Logged multi-turn chat messages with citations and query intents."""
    __tablename__ = "chat_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # 'user', 'assistant'
    query_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 'document_rag', 'company_research', etc.
    message: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="chat_messages")
