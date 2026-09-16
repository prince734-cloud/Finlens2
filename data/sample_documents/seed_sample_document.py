"""
Seeds the Apple FY2024 sample financial report into the FinAdvisor platform,
executing parsing, recursive chunking, ChromaDB vector indexing, and DB sync.
"""
import asyncio
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select

from backend.app.database.connection import init_db, AsyncSessionLocal
from backend.app.database.models import Document
from backend.app.services.document_service import document_service
from data.sample_documents.create_sample_report import create_apple_sample_report


async def seed():
    await init_db()
    pdf_path = Path(__file__).resolve().parent / "Apple_Inc_FY2024_Annual_Report.pdf"
    if not pdf_path.exists():
        print(f"Creating sample PDF at {pdf_path}...")
        create_apple_sample_report(str(pdf_path))

    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Document).where(Document.filename == pdf_path.name))
        existing = res.scalar_one_or_none()
        if existing and existing.status == "indexed":
            print(f"Document already seeded: {existing.id} ({existing.chunk_count} chunks indexed).")
            return

        if not existing:
            doc = Document(
                filename=pdf_path.name,
                file_path=str(pdf_path),
                file_size_bytes=pdf_path.stat().st_size,
                document_type="annual_report",
                company_name="Apple Inc.",
                financial_year=2024,
                status="uploaded",
                chunk_count=0
            )
            db.add(doc)
            await db.commit()
            await db.refresh(doc)
        else:
            doc = existing

        print(f"Indexing document: {doc.id}...")
        processed = await document_service.process_document(doc.id, db)
        print(f"Successfully processed! Status: {processed.status} | Total Chunks: {processed.chunk_count}")


if __name__ == "__main__":
    asyncio.run(seed())
