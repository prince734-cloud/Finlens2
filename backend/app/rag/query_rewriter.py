"""
FinAdvisor Financial Query Rewriter & Decomposer.

Provides domain-specific query expansion and multi-intent query decomposition
for financial document RAG.

Capabilities:
1. Financial Term Expansion: Translates colloquialisms and financial acronyms
   (e.g., 'P&L', 'MD&A', 'top-line', '10-K') into the exact section headers and
   phrasings used in SEC filings and annual reports.
2. Query Decomposition: Detects multi-faceted questions combining distinct financial
   topics (e.g., performance metrics vs. risk factors) and splits them into
   independent, focused sub-queries for parallel retrieval.
"""

import re
from typing import Dict, List, Set

from backend.app.utils.logger import logger


# Financial synonym and section expansion mappings
FINANCIAL_EXPANSION_RULES: Dict[str, str] = {
    r"\bp&l\b": "Consolidated Statements of Operations Income Statement Profit and Loss",
    r"\bmd&a\b": "Item 7 Management's Discussion and Analysis of Financial Condition",
    r"\btop\s*line\b": "Revenue Net Sales Total Net Sales",
    r"\bbottom\s*line\b": "Net Income Net Earnings Net Profit",
    r"\bbalance\s*sheet\b": "Consolidated Balance Sheets Statements of Financial Position",
    r"\bcash\s*flow\b": "Consolidated Statements of Cash Flows Operating Cash Flow",
    r"\brisk\s*factors?\b": "Item 1A Risk Factors Principal Risks and Uncertainties",
    r"\bsegment(?:s|al)?\b": "Segment Information Net Sales by Reportable Segment",
    r"\bdebt\b": "Total Debt Commercial Paper Term Debt Borrowings",
    r"\bmargin\b": "Gross Margin Operating Margin Profit Margin",
}

# Conjunction patterns for multi-part financial questions
COMPOUND_SPLIT_PATTERNS = [
    re.compile(r"\s+(?:and|as well as|also|along with)\s+(?:what|how|why|which|summarize|detail|describe|explain)\s+", re.IGNORECASE),
    re.compile(r"\s*;\s*"),
]


class FinancialQueryRewriter:
    """
    Analyzes, expands, and decomposes financial questions for optimized retrieval.
    """

    def __init__(self):
        self._expansion_rules = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in FINANCIAL_EXPANSION_RULES.items()
        ]

    def expand_terms(self, query: str) -> str:
        """
        Appends targeted financial terminology to a query if relevant acronyms
        or terms are present.
        """
        additions: Set[str] = set()
        for regex, expansion in self._expansion_rules:
            if regex.search(query):
                additions.add(expansion)

        if additions:
            expanded = f"{query.strip()} {' '.join(sorted(additions))}"
            return expanded
        return query

    def decompose(self, query: str) -> List[str]:
        """
        Decomposes compound questions into distinct sub-queries if multiple
        financial questions are joined together.
        
        Example:
        'What was Apple's 2024 revenue growth and what are its key supply chain risks?'
        -> [
            'What was Apple's 2024 revenue growth',
            'what are its key supply chain risks'
        ]
        """
        cleaned = query.strip()
        sub_queries: List[str] = []

        # Try splitting by compound question conjunctions
        for pattern in COMPOUND_SPLIT_PATTERNS:
            parts = pattern.split(cleaned)
            if len(parts) > 1 and all(len(p.strip()) > 10 for p in parts):
                sub_queries = [p.strip() for p in parts]
                break

        # Check for clause splitting by ' and ' if distinct financial themes appear
        if not sub_queries and " and " in cleaned.lower():
            # Check if one part is about revenue/sales and another about risks/factors
            lower = cleaned.lower()
            if ("revenue" in lower or "profit" in lower or "sales" in lower) and ("risk" in lower or "uncertaint" in lower):
                parts = re.split(r"\s+and\s+", cleaned, maxsplit=1, flags=re.IGNORECASE)
                if len(parts) == 2 and all(len(p.strip()) > 8 for p in parts):
                    sub_queries = [parts[0].strip(), parts[1].strip()]

        if not sub_queries:
            sub_queries = [cleaned]

        return sub_queries

    def rewrite_and_expand(self, query: str) -> List[str]:
        """
        Performs full query processing pipeline:
        1. Decomposes compound queries into sub-queries.
        2. Expands domain terms for each sub-query.
        3. Returns unique list of search queries to execute.
        """
        sub_queries = self.decompose(query)
        processed_queries: List[str] = []

        # Always include the original query first
        processed_queries.append(query.strip())

        for sq in sub_queries:
            expanded = self.expand_terms(sq)
            if expanded not in processed_queries:
                processed_queries.append(expanded)
            elif sq not in processed_queries:
                processed_queries.append(sq)

        logger.debug(f"Query rewriter processed '{query}' into {len(processed_queries)} retrieval queries.")
        return processed_queries


# Singleton instance
query_rewriter = FinancialQueryRewriter()
