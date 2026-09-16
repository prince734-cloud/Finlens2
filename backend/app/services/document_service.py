import os
from pathlib import Path
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.models import Document, DocumentChunk
from backend.app.rag.chunking import FinancialChunk, FinancialRecursiveChunker
from backend.app.rag.hybrid_search import hybrid_search_engine
from backend.app.rag.loader import FinancialPDFLoader
from backend.app.rag.retriever import RetrievedChunk, retriever
from backend.app.utils.logger import logger


class DocumentService:
    """
    Orchestration service coordinating document parsing, recursive chunking,
    vector store indexing, and relational synchronization.
    """

    def __init__(self):
        self.loader = FinancialPDFLoader()
        self.chunker = FinancialRecursiveChunker()

    async def process_document(
        self,
        document_id: str,
        db: AsyncSession
    ) -> Document:
        """
        Executes end-to-end processing for an uploaded document:
        1. Parse pages and detect financial sections
        2. Recursively chunk while preserving table rows and page boundaries
        3. Index dense embeddings into ChromaDB
        4. Persist chunk records into relational database
        5. Update document status to 'indexed'
        """
        stmt = select(Document).where(Document.id == document_id)
        result = await db.execute(stmt)
        doc = result.scalar_one_or_none()

        if not doc:
            raise ValueError(f"Document with ID {document_id} not found.")

        doc.status = "processing"
        await db.commit()
        await db.refresh(doc)

        try:
            logger.info(f"Beginning pipeline for document '{doc.filename}' (ID: {doc.id})...")

            # 1. Parse PDF pages
            pages = self.loader.load_pdf(doc.file_path)
            if not pages:
                raise ValueError("No extractable text found in PDF document.")

            # 2. Chunk pages with metadata
            chunks: List[FinancialChunk] = self.chunker.chunk_pages(
                pages=pages,
                document_id=doc.id,
                document_name=doc.filename,
                document_type=doc.document_type,
                company_name=doc.company_name,
                financial_year=doc.financial_year
            )

            # 3. Index into ChromaDB vector store and BM25 sparse index
            retriever.add_chunks(chunks)
            bm25_chunks = [
                RetrievedChunk(
                    id=c.id,
                    content=c.content,
                    document_id=doc.id,
                    document_name=doc.filename,
                    company_name=doc.company_name or "Unknown Company",
                    financial_year=doc.financial_year or 2024,
                    page_number=c.page_number,
                    section=c.section,
                    relevance_score=1.0,
                    metadata=c.metadata
                )
                for c in chunks
            ]
            hybrid_search_engine.bm25_index.add_chunks(bm25_chunks)

            # 4. Save relational chunk records for traceability
            for chunk in chunks:
                rel_chunk = DocumentChunk(
                    id=chunk.id,
                    document_id=doc.id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    page_number=chunk.page_number,
                    section=chunk.section,
                    chunk_metadata=chunk.metadata,
                    vector_id=chunk.id
                )
                db.add(rel_chunk)

            # 5. Update document record
            doc.status = "indexed"
            doc.chunk_count = len(chunks)
            await db.commit()
            await db.refresh(doc)

            logger.info(
                f"Document '{doc.filename}' successfully indexed with {len(chunks)} chunks."
            )
            return doc

        except Exception as e:
            logger.error(f"Failed to process document {document_id}: {e}", exc_info=True)
            doc.status = "failed"
            await db.commit()
            raise

    async def delete_document(
        self,
        document_id: str,
        db: AsyncSession
    ) -> bool:
        """
        Deletes a document from the filesystem, the ChromaDB vector collection,
        and the relational database.
        """
        stmt = select(Document).where(Document.id == document_id)
        result = await db.execute(stmt)
        doc = result.scalar_one_or_none()

        if not doc:
            return False

        # Remove from vector store and BM25 index
        retriever.delete_by_document_id(document_id)
        hybrid_search_engine.bm25_index.remove_by_document_id(document_id)

        # Remove physical file
        if os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
            except OSError as e:
                logger.warning(f"Could not remove file on disk {doc.file_path}: {e}")

        # Remove from database (cascades to document_chunks)
        await db.delete(doc)
        await db.commit()
        return True


# Export singleton service
document_service = DocumentService()
