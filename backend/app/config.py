import os
import json
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Immediately load environment variables from .env file
load_dotenv()

# Base directory of FinLens project
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env file."""
    
    # Application Info
    APP_NAME: str = "FinLens — AI Financial Intelligence & Investment Research Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production" if os.getenv("PORT") else "development")
    
    # Server configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
    )

    @property
    def cors_origins(self) -> List[str]:
        """Return CORS origins from either JSON or comma-separated settings."""
        value = self.CORS_ORIGINS.strip()
        if not value:
            return []
        if value.startswith("["):
            parsed = json.loads(value)
            return [str(origin).strip() for origin in parsed if str(origin).strip()]
        return [origin.strip() for origin in value.split(",") if origin.strip()]
    
    # Database Configuration
    # Defaults to a local SQLite database for instant zero-dependency testing,
    # or PostgreSQL when DATABASE_URL is set to postgresql+asyncpg://...
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        f"sqlite+aiosqlite:///{BASE_DIR / 'finlens.db'}"
    )
    
    # Vector Store Backend ('chroma' or 'pgvector')
    VECTOR_STORE_BACKEND: str = "chroma"
    CHROMA_PERSIST_DIR: str = str(BASE_DIR / "data" / "chroma_db")
    
    # Upload and Data Directories
    UPLOAD_DIR: str = str(BASE_DIR / "data" / "uploads")
    ANNUAL_REPORTS_DIR: str = str(BASE_DIR / "data" / "annual_reports")
    MUTUAL_FUNDS_DIR: str = str(BASE_DIR / "data" / "mutual_funds")
    
    # LLM Settings
    LLM_PROVIDER: str = "groq"  # Options: 'groq', 'mistral', 'anthropic', 'gemini'
    LLM_TEMPERATURE: float = 0.1  # Low temperature for factual financial queries
    LLM_MAX_TOKENS: int = 2048

    # API Keys
    HF_TOKEN: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
    
    MISTRAL_API_KEY: Optional[str] = None
    MISTRAL_MODEL: str = os.getenv("MISTRAL_MODEL", "ministral-14b-latest")
    
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    # Embedding & Reranker models
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "huggingface")  # Options: 'huggingface', 'mistral'
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    MISTRAL_EMBEDDING_MODEL: str = os.getenv("MISTRAL_EMBEDDING_MODEL", "mistral-embed")
    RERANKER_MODEL_NAME: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    # RAG Settings
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 150
    TOP_K_RETRIEVAL: int = 5
    TOP_K_RERANKED: int = 3
    
    model_config = SettingsConfigDict(
        env_file=(
            str(BASE_DIR / ".env"),
            str(BASE_DIR.parent / "finance-rag-project" / "finance-rag-project" / ".env"),
            str(BASE_DIR.parent / ".env")
        ),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

# Ensure critical directories exist
for folder in [settings.UPLOAD_DIR, settings.CHROMA_PERSIST_DIR, settings.ANNUAL_REPORTS_DIR, settings.MUTUAL_FUNDS_DIR]:
    Path(folder).mkdir(parents=True, exist_ok=True)
