from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from backend.app.rag.retriever import RetrievedChunk


class CitationItem(BaseModel):
    """Verifiable source citation grounded in retrieved document chunks or audited database records."""
    document_name: str
    page_number: Union[int, str] = 1
    section: str = "General"
    excerpt: str
    relevance_score: Optional[float] = None


class CitationEngine:
    """
    Handles context formatting with citation tags and builds verifiable
    citation payloads strictly from retrieved document chunks.
    Guarantees no fabricated citations.
    """

    @staticmethod
    def format_context_for_llm(chunks: List[RetrievedChunk]) -> str:
        """
        Formats retrieved chunks into a cleanly structured context block
        with distinct source boundaries, page numbers, and section names.
        """
        if not chunks:
            return "NO RELEVANT FINANCIAL DOCUMENTS FOUND."

        formatted_blocks = []
        for i, chunk in enumerate(chunks, 1):
            block = (
                f"--- [SOURCE {i}] ---\n"
                f"Document: {chunk.document_name}\n"
                f"Page: {chunk.page_number}\n"
                f"Section: {chunk.section}\n"
                f"Company: {chunk.company_name} (FY {chunk.financial_year})\n"
                f"Content:\n{chunk.content}\n"
            )
            formatted_blocks.append(block)

        return "\n".join(formatted_blocks)

    @staticmethod
    def build_citations(
        chunks: List[RetrievedChunk],
        max_citations: int = 4
    ) -> List[CitationItem]:
        """
        Extracts verified citations directly from the retrieved chunks that formed
        the context, deduplicating identical page/section references.
        """
        seen_keys = set()
        citations: List[CitationItem] = []

        for chunk in chunks:
            key = (chunk.document_name, chunk.page_number, chunk.section)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            # Generate a clean, readable excerpt (strip context header if present)
            raw_content = chunk.content
            if "\n" in raw_content and raw_content.startswith("[Document:"):
                # Omit first line context header for the UI display excerpt
                lines = raw_content.split("\n", 1)
                display_content = lines[1].strip() if len(lines) > 1 else raw_content
            else:
                display_content = raw_content.strip()

            snippet = display_content[:200] + ("..." if len(display_content) > 200 else "")

            citations.append(
                CitationItem(
                    document_name=chunk.document_name,
                    page_number=chunk.page_number,
                    section=chunk.section,
                    excerpt=snippet,
                    relevance_score=chunk.relevance_score
                )
            )

            if len(citations) >= max_citations:
                break

        return citations
