import threading
from typing import TYPE_CHECKING, Any, List, Optional, Union

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_mistralai import MistralAIEmbeddings

from backend.app.config import settings
from backend.app.utils.logger import logger


class EmbeddingService:
    """
    Singleton Embedding Service supporting both local HuggingFaceEmbeddings
    (ultra-fast, 384-d, zero-latency, offline) and MistralAIEmbeddings
    (1024-d state-of-the-art semantic representations via Mistral API).
    """
    _instance: Optional["EmbeddingService"] = None
    _lock = threading.Lock()

    def __init__(self, model_name: Optional[str] = None, provider: Optional[str] = None):
        self.provider = (provider or settings.EMBEDDING_PROVIDER).lower()
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self._embeddings: Optional[Any] = None
        self._dimension: int = 384

    @classmethod
    def get_instance(
        cls, 
        model_name: Optional[str] = None,
        provider: Optional[str] = None
    ) -> "EmbeddingService":
        """Thread-safe lazy singleton access to avoid reloading weights across requests."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(model_name=model_name, provider=provider)
        return cls._instance

    def _ensure_model_loaded(self):
        """Loads configured Embeddings model via LangChain if not already cached."""
        if self._embeddings is None:
            with self._lock:
                if self._embeddings is None:
                    from langchain_huggingface import HuggingFaceEmbeddings
                    from langchain_mistralai import MistralAIEmbeddings
                    from pydantic import SecretStr

                    if self.provider == "mistral" and settings.MISTRAL_API_KEY:
                        try:
                            logger.info(
                                f"Loading MistralAIEmbeddings: {settings.MISTRAL_EMBEDDING_MODEL}..."
                            )
                            self._embeddings = MistralAIEmbeddings(
                                model=settings.MISTRAL_EMBEDDING_MODEL,
                                api_key=SecretStr(settings.MISTRAL_API_KEY)
                            )
                            test_vec = self._embeddings.embed_query("financial verification")
                            self._dimension = len(test_vec)
                            logger.info(f"MistralAIEmbeddings loaded successfully. Dimension: {self._dimension}")
                            return
                        except Exception as e:
                            logger.warning(
                                f"Failed to initialize MistralAIEmbeddings ({e}). "
                                "Falling back to local HuggingFaceEmbeddings."
                            )

                    # Default to local HuggingFaceEmbeddings
                    logger.info(f"Loading local LangChain HuggingFaceEmbeddings: {self.model_name}...")
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
                    logger.info(f"LangChain HuggingFaceEmbeddings loaded. Dimension: {self._dimension}")

    @property
    def langchain_embeddings(self) -> Any:
        """Exposes the underlying LangChain Embeddings model directly."""
        self._ensure_model_loaded()
        assert self._embeddings is not None
        return self._embeddings

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generates dense vector embeddings for a list of document chunks using LangChain."""
        if not texts:
            return []
        self._ensure_model_loaded()
        assert self._embeddings is not None
        clean_texts = [t if t.strip() else " " for t in texts]
        return self._embeddings.embed_documents(clean_texts)

    def embed_query(self, query: str) -> List[float]:
        """Generates a dense vector embedding for a user query using LangChain."""
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
