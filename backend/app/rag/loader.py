import os
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import pymupdf as fitz
from backend.app.utils.logger import logger


@dataclass
class DocumentPage:
    """Represents a single parsed page from a financial document."""
    page_number: int  # 1-indexed
    text: str
    section: str = "General"
    tables: List[List[List[str]]] = field(default_factory=list)


class FinancialPDFLoader:
    """
    High-fidelity PDF document parser specifically designed for financial filings,
    annual reports, and investment prospectuses.
    
    Key capabilities:
    1. Page-by-page extraction with 1-based page numbering for precise citations.
    2. Dynamic financial section header detection (e.g., Item 1A Risk Factors, MD&A, Financial Statements).
    3. State-machine tracking so subsequent pages inherit active section context.
    4. Unicode normalization (hyphens, ligatures, non-breaking spaces).
    5. Recurring header/footer and page-number artifact suppression.
    """

    # Regex patterns for identifying standard financial report section headers
    SECTION_PATTERNS = [
        re.compile(r"^(item\s+\d+[a-z]?[\.:\s\-]+[^\n]+)", re.IGNORECASE),
        re.compile(r"^(consolidated statements? of (?:operations|income|cash flows|comprehensive income|financial position|balance sheets?)[^\n]*)", re.IGNORECASE),
        re.compile(r"^(notes to (?:consolidated )?financial statements[^\n]*)", re.IGNORECASE),
        re.compile(r"^(management(?:'s)? discussion and analysis[^\n]*)", re.IGNORECASE),
        re.compile(r"^(risk factors[^\n]*)", re.IGNORECASE),
        re.compile(r"^(business overview|company overview|executive summary[^\n]*)", re.IGNORECASE),
        re.compile(r"^(financial highlights|performance overview[^\n]*)", re.IGNORECASE),
        re.compile(r"^(report of independent registered public accounting firm[^\n]*)", re.IGNORECASE),
        re.compile(r"^(portfolio composition|asset allocation|scheme performance[^\n]*)", re.IGNORECASE),
    ]

    # Patterns for running headers, footers, and page numbers
    FOOTER_PATTERNS = [
        re.compile(r"^\s*(?:page\s+)?\d+\s*(?:of\s+\d+)?\s*$", re.IGNORECASE),
        re.compile(r"^\s*\|\s*\d+\s*\|\s*$"),
        re.compile(r"^\s*form\s+10-[kq]\s*\|\s*page\s+\d+\s*$", re.IGNORECASE),
    ]

    def __init__(self, remove_footers: bool = True):
        self.remove_footers = remove_footers

    def clean_text(self, text: str) -> str:
        """
        Normalizes unicode characters, cleans line breaks and excessive whitespace
        while preserving tabular layouts.
        """
        if not text:
            return ""

        # Normalize unicode (NFKC replaces ligatures like 'fi', 'fl', special spaces)
        text = unicodedata.normalize("NFKC", text)

        # Replace non-standard whitespace and special dashes
        text = text.replace("\xa0", " ")
        text = text.replace("\u2013", "-").replace("\u2014", "-")
        text = text.replace("\u2018", "'").replace("\u2019", "'")
        text = text.replace("\u201c", '"').replace("\u201d", '"')

        # Split into lines for line-level filtering
        raw_lines = text.splitlines()
        cleaned_lines = []

        for line in raw_lines:
            stripped = line.strip()
            if not stripped:
                cleaned_lines.append("")
                continue

            # Suppress isolated page number footers
            if self.remove_footers and any(pat.match(stripped) for pat in self.FOOTER_PATTERNS):
                continue

            cleaned_lines.append(stripped)

        # Recombine while collapsing 3+ consecutive newlines into 2
        result = "\n".join(cleaned_lines)
        result = re.sub(r"\n{3,}", "\n\n", result)
        return result.strip()

    def detect_section(self, text: str, default_section: str) -> str:
        """
        Scans lines at the beginning of a page to detect prominent section titles.
        If a new section header is found, returns it; otherwise retains current section.
        """
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        
        # Check first 8 lines of the page for section headers
        for line in lines[:8]:
            for pattern in self.SECTION_PATTERNS:
                match = pattern.search(line)
                if match:
                    detected = match.group(1).strip()
                    # Clean punctuation at ends
                    detected = re.sub(r"[\.:\-_]+$", "", detected).strip()
                    if len(detected) < 120:  # Avoid matching entire paragraphs
                        return detected

        return default_section

    def load_pdf(self, file_path: str) -> List[DocumentPage]:
        """
        Parses a PDF document into a sequence of DocumentPage objects with
        page numbers, cleaned text, and detected financial sections.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        logger.info(f"Extracting financial text from PDF: {path.name}")
        pages: List[DocumentPage] = []
        current_section = "General Overview"

        doc = fitz.open(file_path)
        try:
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                page_num = page_idx + 1  # 1-indexed for citations
                raw_text = str(page.get_text("text") or "")

                # Clean text
                cleaned_text = self.clean_text(raw_text)
                if not cleaned_text:
                    logger.debug(f"Page {page_num} in {path.name} has no text (scanned or blank).")
                    continue

                # Detect active section or carry over from previous page
                current_section = self.detect_section(cleaned_text, default_section=current_section)

                pages.append(
                    DocumentPage(
                        page_number=page_num,
                        text=cleaned_text,
                        section=current_section,
                        tables=[]
                    )
                )

            logger.info(f"Successfully loaded {len(pages)} pages from {path.name}")
            return pages
        finally:
            doc.close()
