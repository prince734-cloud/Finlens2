import uuid
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.app.config import settings
from backend.app.rag.loader import DocumentPage
from backend.app.utils.logger import logger


@dataclass
class FinancialChunk:
    """Represents a single semantic chunk enriched with financial metadata."""
    id: str
    content: str
    document_id: str
    document_name: str
    document_type: str
    company_name: str
    financial_year: int
    page_number: int
    section: str
    chunk_index: int
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FinancialRecursiveChunker:
    """
    Financial document chunker utilizing LangChain's RecursiveCharacterTextSplitter
    augmented with financial delimiters and contextual header injection.
    
    Why this is critical for financial RAG:
    - Tables, metric statements, and footnotes stay intact with domain separators.
    - Adding contextual headers ([Company | Year | Section | Page]) prevents 
      anaphoric ambiguity ('the Company's net sales increased 6%') during dense vector retrieval.
    - Never splits across page boundaries, preserving exact citation provenance.
    """

    DEFAULT_SEPARATORS = [
        "\n\n",   # Double newlines (paragraphs, distinct table blocks)
        "\n",     # Single newlines (table rows, list items)
        ".\n",    # Sentence terminator followed by newline
        ". ",     # Sentence terminator
        "; ",     # Clause boundary
        ", ",     # Sub-clause boundary
        " ",      # Word boundary
        ""        # Fallback character
    ]

    def __init__(
        self,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
        add_context_header: bool = True
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.add_context_header = add_context_header
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.DEFAULT_SEPARATORS,
            keep_separator=True,
            length_function=len
        )

    def _split_text(self, text: str, separators: Optional[List[str]] = None) -> List[str]:
        """Splits text using LangChain's RecursiveCharacterTextSplitter."""
        if not text or not text.strip():
            return []
        if separators and separators != self.DEFAULT_SEPARATORS:
            custom_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=separators,
                keep_separator=True,
                length_function=len
            )
            return custom_splitter.split_text(text)
        return self._splitter.split_text(text)

    def chunk_pages(
        self,
        pages: List[DocumentPage],
        document_id: str,
        document_name: str,
        document_type: str = "annual_report",
        company_name: Optional[str] = None,
        financial_year: Optional[int] = None
    ) -> List[FinancialChunk]:
        """
        Chunks parsed document pages into a sequence of rich FinancialChunk objects.
        Page boundaries are respected (chunks do not cross across different pages),
        ensuring 100% accurate page citations.
        """
        resolved_company = company_name or document_name.replace(".pdf", "").replace("_", " ")
        resolved_year = financial_year or 2024
        chunks: List[FinancialChunk] = []
        global_chunk_idx = 0

        for page in pages:
            raw_splits = self._split_text(page.text, self.DEFAULT_SEPARATORS)

            for split_text in raw_splits:
                cleaned_split = split_text.strip()
                if len(cleaned_split) < 25:
                    # Discard meaningless fragments (e.g. orphan bullet points or lone numbers)
                    continue

                # Context header for dense vector retrieval grounding
                if self.add_context_header:
                    header = (
                        f"[Document: {document_name} | Company: {resolved_company} | "
                        f"FY: {resolved_year} | Section: {page.section} | Page: {page.page_number}]\n"
                    )
                    content = header + cleaned_split
                else:
                    content = cleaned_split

                chunk_id = str(uuid.uuid4())
                meta = {
                    "document_id": document_id,
                    "document_name": document_name,
                    "document_type": document_type,
                    "company_name": resolved_company,
                    "financial_year": resolved_year,
                    "page_number": page.page_number,
                    "section": page.section,
                    "chunk_index": global_chunk_idx,
                }

                chunks.append(
                    FinancialChunk(
                        id=chunk_id,
                        content=content,
                        document_id=document_id,
                        document_name=document_name,
                        document_type=document_type,
                        company_name=resolved_company,
                        financial_year=resolved_year,
                        page_number=page.page_number,
                        section=page.section,
                        chunk_index=global_chunk_idx,
                        metadata=meta
                    )
                )
                global_chunk_idx += 1

        logger.info(
            f"Chunked document '{document_name}' into {len(chunks)} financial chunks "
            f"(target size={self.chunk_size}, overlap={self.chunk_overlap})."
        )
        return chunks
