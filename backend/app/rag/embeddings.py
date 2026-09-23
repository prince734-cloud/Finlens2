import hashlib
import math
import re
import threading
from typing import Any, List, Optional

from langchain_core.embeddings import Embeddings

from backend.app.config import settings
from backend.app.utils.logger import logger


class LightweightEmbeddings(Embeddings):
    """
    Deterministic zero-RAM 384-d normalized embedding vector.
    Uses n-gram feature hashing and financial term weighting.
    Consumes 0 MB of model RAM, requires 0 external dependencies, and works completely offline.
    """

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def _embed_single(self, text: str) -> List[float]:
        vec = [0.0] * self.dimension
        clean_text = text.lower().strip()
        if not clean_text:
            return vec

        words = re.findall(r"[a-z0-9$%\.,]+", clean_text)
        synonyms = {
            "turnover": "sales",
            "revenue": "sales",
            "revenues": "sales",
            "earnings": "income",
            "profit": "income",
            "profits": "income",
            "expenditure": "costs",
            "expense": "costs",
            "expenses": "costs",
            "debt": "liabilities",
            "borrowing": "liabilities",
        }

        for w in words:
            canonical = synonyms.get(w, w)
            h = int(hashlib.md5(f"w_{canonical}".encode("utf-8")).hexdigest()[:8], 16)
            sign = 1.0 if (int(hashlib.sha1(f"w_{canonical}".encode("utf-8")).hexdigest()[:8], 16) % 2 == 0) else -1.0
            vec[h % self.dimension] += 3.0 * sign

            if len(w) >= 3:
                for i in range(len(w) - 2):
                    gram = w[i:i+3]
                    hg = int(hashlib.md5(f"g_{gram}".encode("utf-8")).hexdigest()[:8], 16)
                    sg = 1.0 if (int(hashlib.sha1(f"g_{gram}".encode("utf-8")).hexdigest()[:8], 16) % 2 == 0) else -1.0
                    vec[hg % self.dimension] += 1.0 * sg

        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0.0:
            vec = [round(x / norm, 6) for x in vec]
        return vec

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_single(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed_single(text)


class HFAPIEmbeddings(Embeddings):
    """
    Zero-RAM Cloud Embeddings via Hugging Face Serverless Inference API.
    Calls Hugging Face endpoint for 'sentence-transformers/all-MiniLM-L6-v2' via HTTP.
    Generates exact 384-d normalized vectors with 0 MB local RAM footprint.
    Gracefully falls back to LightweightEmbeddings if offline or rate-limited.
    """

    def __init__(self, api_url: Optional[str] = None, token: Optional[str] = None, dimension: int = 384):
        self.api_url = api_url or settings.HF_INFERENCE_URL
        self.token = settings.HF_TOKEN if token is None else token
        self.dimension = dimension
        self._fallback = LightweightEmbeddings(dimension=dimension)

    def _get_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if not self.token:
            return self._fallback.embed_documents(texts)
        try:
            import httpx
            with httpx.Client(timeout=12.0) as client:
                res = client.post(
                    self.api_url,
                    headers=self._get_headers(),
                    json={"inputs": texts, "options": {"wait_for_model": True}}
                )
                if res.status_code == 200:
                    data = res.json()
                    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                        return data
                logger.warning(
                    f"HF Inference API returned status {res.status_code} ({res.text[:120]}). "
                    "Using deterministic lightweight embedding fallback."
                )
        except Exception as e:
            logger.warning(
                f"HF Inference API request failed ({e}). "
                "Using deterministic lightweight embedding fallback."
            )
        return self._fallback.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        clean = text.strip() if text.strip() else "financial query"
        if not self.token:
            return self._fallback.embed_query(clean)
        results = self.embed_documents([clean])
        return results[0] if results else self._fallback.embed_query(clean)


class GeminiEmbeddings(Embeddings):
    """
    Zero-RAM Cloud Embeddings via Google Gemini text-embedding-004 API.
    Consumes 0 MB local RAM and supports free tier (1,500 requests/minute).
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_EMBEDDING_MODEL
        self.dimension = 768
        self._fallback = LightweightEmbeddings(dimension=self.dimension)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts or not self.api_key:
            return self._fallback.embed_documents(texts)
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            result = client.models.embed_content(
                model=self.model,
                contents=texts
            )
            embeddings = []
            if hasattr(result, "embeddings") and result.embeddings:
                for emb in result.embeddings:
                    embeddings.append(emb.values)
                return embeddings
        except Exception as e:
            logger.warning(f"Gemini embedding API call failed ({e}). Falling back to lightweight.")
        return self._fallback.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        res = self.embed_documents([text])
        return res[0] if res else self._fallback.embed_query(text)


class EmbeddingService:
    """
    Multi-provider Singleton Embedding Service optimized for low-memory environments (<= 512MB RAM).
    Supported Providers:
    - 'hf_api' (Default): Hugging Face Serverless Inference API (384-d, 0 MB local RAM)
    - 'gemini': Google Gemini text-embedding-004 (768-d, 0 MB local RAM)
    - 'mistral': Mistral AI mistral-embed (1024-d, 0 MB local RAM)
    - 'lightweight': Deterministic feature-hashed embeddings (384-d, 0 MB RAM, offline)
    - 'huggingface': Local PyTorch transformer (only used if LOW_MEMORY_MODE=False and torch is installed)
    """

    _instance: Optional["EmbeddingService"] = None
    _lock = threading.Lock()

    def __init__(self, model_name: Optional[str] = None, provider: Optional[str] = None):
        self.provider = (provider or settings.EMBEDDING_PROVIDER).lower()
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self._embeddings: Optional[Embeddings] = None
        self._dimension: int = 384

    @classmethod
    def get_instance(
        cls, 
        model_name: Optional[str] = None,
        provider: Optional[str] = None
    ) -> "EmbeddingService":
        """Thread-safe lazy singleton access to avoid reloading models across requests."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(model_name=model_name, provider=provider)
        return cls._instance

    def _ensure_model_loaded(self):
        """Loads configured Embeddings model via provider specification."""
        if self._embeddings is not None:
            return

        with self._lock:
            if self._embeddings is not None:
                return

            logger.info(f"Initializing EmbeddingService with provider: '{self.provider}'...")

            # 1. Hugging Face Serverless API (0 MB RAM, 384-dim, with automatic lightweight fallback)
            if self.provider in ("hf_api", "huggingface_api", "hf", "auto"):
                self._embeddings = HFAPIEmbeddings(
                    api_url=settings.HF_INFERENCE_URL,
                    token=settings.HF_TOKEN,
                    dimension=384
                )
                self._dimension = 384
                logger.info("HFAPIEmbeddings initialized (0 MB RAM, automatic lightweight fallback active).")
                return

            # 2. Google Gemini API (0 MB RAM, 768-dim)
            if self.provider in ("gemini", "google"):
                if settings.GEMINI_API_KEY:
                    self._embeddings = GeminiEmbeddings(
                        api_key=settings.GEMINI_API_KEY,
                        model=settings.GEMINI_EMBEDDING_MODEL
                    )
                    self._dimension = 768
                    logger.info("GeminiEmbeddings initialized (0 MB RAM).")
                    return
                else:
                    logger.warning("GEMINI_API_KEY not set. Falling back to hf_api.")
                    self.provider = "hf_api"
                    self._embeddings = HFAPIEmbeddings(token=settings.HF_TOKEN, dimension=384)
                    self._dimension = 384
                    return

            # 3. Mistral AI API (0 MB RAM, 1024-dim)
            if self.provider == "mistral" and settings.MISTRAL_API_KEY:
                try:
                    from langchain_mistralai import MistralAIEmbeddings
                    from pydantic import SecretStr
                    self._embeddings = MistralAIEmbeddings(
                        model=settings.MISTRAL_EMBEDDING_MODEL,
                        api_key=SecretStr(settings.MISTRAL_API_KEY)
                    )
                    self._dimension = 1024
                    logger.info("MistralAIEmbeddings initialized (0 MB RAM).")
                    return
                except Exception as e:
                    logger.warning(f"Failed to initialize MistralAIEmbeddings ({e}). Falling back to hf_api.")

            # 4. Pure offline lightweight deterministic embeddings (0 MB RAM)
            if self.provider == "lightweight":
                self._embeddings = LightweightEmbeddings(dimension=384)
                self._dimension = 384
                logger.info("LightweightEmbeddings initialized (0 MB RAM).")
                return

            # 5. Local HuggingFace / PyTorch (High RAM) - Only if LOW_MEMORY_MODE is disabled
            if not settings.LOW_MEMORY_MODE:
                try:
                    from langchain_huggingface import HuggingFaceEmbeddings
                    logger.info(f"Loading local PyTorch HuggingFaceEmbeddings: {self.model_name}...")
                    model_kwargs = {}
                    if settings.HF_TOKEN:
                        model_kwargs["token"] = settings.HF_TOKEN
                    self._embeddings = HuggingFaceEmbeddings(
                        model_name=self.model_name,
                        model_kwargs=model_kwargs,
                        encode_kwargs={"normalize_embeddings": True}
                    )
                    test_vec = self._embeddings.embed_query("financial verification")
                    self._dimension = len(test_vec)
                    logger.info(f"Local HuggingFaceEmbeddings loaded. Dimension: {self._dimension}")
                    return
                except Exception as e:
                    logger.warning(
                        f"Could not load local HuggingFace model ({e}). "
                        "Falling back to zero-RAM HFAPIEmbeddings."
                    )

            # Default safe fallback for low-memory free-tier
            self._embeddings = HFAPIEmbeddings(
                api_url=settings.HF_INFERENCE_URL,
                token=settings.HF_TOKEN,
                dimension=384
            )
            self._dimension = 384
            logger.info("Initialized default zero-RAM HFAPIEmbeddings.")

    @property
    def langchain_embeddings(self) -> Any:
        """Exposes the underlying LangChain Embeddings model directly."""
        self._ensure_model_loaded()
        assert self._embeddings is not None
        return self._embeddings

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generates dense vector embeddings for a list of document chunks."""
        if not texts:
            return []
        self._ensure_model_loaded()
        assert self._embeddings is not None
        clean_texts = [t if t.strip() else " " for t in texts]
        return self._embeddings.embed_documents(clean_texts)

    def embed_query(self, query: str) -> List[float]:
        """Generates a dense vector embedding for a user query."""
        self._ensure_model_loaded()
        assert self._embeddings is not None
        clean_query = query.strip() if query.strip() else "financial query"
        return self._embeddings.embed_query(clean_query)

    @property
    def dimension(self) -> int:
        self._ensure_model_loaded()
        return self._dimension


# Export default singleton instance
embedding_service = EmbeddingService.get_instance()
