import os
from typing import Any, List, Optional, cast
from pydantic import SecretStr

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_groq import ChatGroq
from langchain_mistralai import ChatMistralAI
from langchain_anthropic import ChatAnthropic

from backend.app.config import settings
from backend.app.utils.logger import logger


SYSTEM_FINANCIAL_RAG_PROMPT = """You are FinLens, an institutional-grade financial intelligence and investment research AI assistant.
Your responsibility is to provide precise, factual, evidence-grounded answers based STRICTLY on the retrieved financial document excerpts provided below.

CRITICAL INSTRUCTIONS & HALLUCINATION CONTROLS:
1. Grounding Rule: Answer ONLY using facts, figures, and statements directly present in the retrieved sources.
2. Anti-Hallucination: Never invent financial numbers, revenue figures, net income, percentages, or metrics.
3. Missing Data Policy: If the provided sources do NOT contain enough information to answer the question with certainty, state clearly and concisely:
   "Insufficient verified data in the uploaded documents to answer this question."
4. Source Attribution: Whenever you mention a financial metric or key insight, explicitly reference the source (Document name, Page number, and Section).
5. Regulatory Disclaimer: Present all analysis as educational research and analytical findings, never as personalized financial advice or guaranteed investment returns.
"""


class LLMService:
    """
    LangChain-powered multi-provider LLM gateway utilizing LCEL Runnables.
    Orchestrates ChatGroq, ChatMistralAI, and ChatAnthropic with automatic
    Runnable fallback chains for resilient institutional research.
    """

    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
        self._chain: Optional[Runnable] = None
        self._init_runnable_chain()

    def _build_model(self, prov: str):
        """Constructs an individual LangChain Chat Model for verified working providers."""
        prov = prov.lower()
        try:
            if prov == "groq" and settings.GROQ_API_KEY:
                return ChatGroq(
                    model=settings.GROQ_MODEL,
                    api_key=SecretStr(settings.GROQ_API_KEY),
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
            elif prov == "mistral" and settings.MISTRAL_API_KEY:
                mistral_cls: Any = ChatMistralAI
                return mistral_cls(
                    model=settings.MISTRAL_MODEL,
                    api_key=SecretStr(settings.MISTRAL_API_KEY),
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
        except Exception as e:
            logger.warning(f"Failed to instantiate LangChain model for '{prov}': {e}")
        return None

    def _init_runnable_chain(self):
        """Builds an LCEL (LangChain Expression Language) Runnable Chain with automatic fallbacks."""
        primary_model = self._build_model(self.provider)
        
        # Build fallback chain only from verified working providers
        fallback_candidates = [p for p in ["groq", "mistral"] if p != self.provider]
        fallback_models = []
        for cand in fallback_candidates:
            m = self._build_model(cand)
            if m is not None:
                fallback_models.append(m)

        if primary_model is None:
            if fallback_models:
                primary_model = fallback_models.pop(0)
            else:
                logger.error("No active LLM providers configured in settings.")
                self._chain = None
                return

        # Compose robust runnable model using LangChain with_fallbacks
        if fallback_models:
            robust_model = primary_model.with_fallbacks(fallback_models)
        else:
            robust_model = primary_model

        # Standard LangChain ChatPromptTemplate
        prompt = ChatPromptTemplate.from_messages([
            ("system", "{system_prompt}"),
            (
                "human",
                "=== RETRIEVED FINANCIAL SOURCES ===\n"
                "{context}\n\n"
                "=== USER QUERY ===\n"
                "{question}\n\n"
                "Provide a structured, fact-grounded response citing specific sources, pages, and sections:"
            )
        ])

        # LCEL Runnable Pipeline: Prompt -> Robust Model -> StrOutputParser
        self._chain = prompt | robust_model | StrOutputParser()
        logger.info(f"Initialized LangChain RAG Runnable pipeline (Primary: {self.provider})")

    @property
    def runnable_chain(self) -> Optional[Runnable]:
        """Exposes the underlying LangChain Runnable chain for streaming or custom execution."""
        return self._chain

    async def generate_grounded_answer(
        self,
        query: str,
        formatted_context: str,
        custom_system_prompt: Optional[str] = None
    ) -> str:
        """
        Executes the LangChain LCEL Runnable chain with strict financial grounding.
        """
        if self._chain is None:
            self._init_runnable_chain()
            if self._chain is None:
                return (
                    "Unable to generate response from LLM at this time. "
                    "No active LLM API keys configured."
                )

        system_prompt = custom_system_prompt or SYSTEM_FINANCIAL_RAG_PROMPT

        try:
            answer = await self._chain.ainvoke({
                "system_prompt": system_prompt,
                "context": formatted_context,
                "question": query
            })
            return str(answer)
        except Exception as e:
            logger.error(f"LangChain Runnable execution failed: {e}")
            return (
                f"Unable to generate response from LLM at this time. "
                f"Error encountered: {e}"
            )


# Export default LLM service
llm_service = LLMService()
