import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.database.connection import get_db
from backend.app.database.models import Document, DocumentChunk, FinancialKPI
from backend.app.extraction.kpi_extractor import kpi_extractor
from backend.app.services.document_service import document_service
from backend.app.utils.logger import logger

router = APIRouter(prefix="/documents", tags=["Financial Documents"])


class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_size_bytes: int
    document_type: str
    company_name: Optional[str] = None
    financial_year: Optional[int] = None
    status: str
    chunk_count: int
    has_kpis: bool = False
    kpi: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class ChunkResponse(BaseModel):
    id: str
    chunk_index: int
    page_number: int
    section: Optional[str] = "General"
    content: str
    chunk_metadata: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=List[DocumentResponse])
async def list_documents(db: AsyncSession = Depends(get_db)):
    """Lists all uploaded financial documents, indexing status, and KPI availability."""
    stmt = select(Document).order_by(Document.upload_date.desc())
    result = await db.execute(stmt)
    docs = result.scalars().all()

    # Query document IDs with extracted KPIs
    kpi_stmt = select(FinancialKPI.document_id).where(FinancialKPI.document_id.isnot(None))
    kpi_res = await db.execute(kpi_stmt)
    kpi_doc_ids = set(kpi_res.scalars().all())

    return [
        DocumentResponse(
            id=d.id,
            filename=d.filename,
            file_size_bytes=d.file_size_bytes,
            document_type=d.document_type,
            company_name=d.company_name,
            financial_year=d.financial_year,
            status=d.status,
            chunk_count=d.chunk_count,
            has_kpis=(d.id in kpi_doc_ids)
        )
        for d in docs
    ]


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form("annual_report"),
    company_name: Optional[str] = Form(None),
    financial_year: Optional[int] = Form(None),
    auto_process: bool = Query(True, description="Immediately index document into vector store"),
    db: AsyncSession = Depends(get_db)
):
    """
    Uploads a PDF financial document to the platform repository and triggers
    automatic parsing, recursive chunking, and ChromaDB vector indexing.
    """
    filename = file.filename or "uploaded_document.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF documents are supported.")

    upload_folder = Path(settings.UPLOAD_DIR)
    upload_folder.mkdir(parents=True, exist_ok=True)
    
    file_dest = upload_folder / filename
    try:
        with open(file_dest, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(status_code=500, detail="Could not write file to storage.")

    file_size = os.path.getsize(file_dest)

    # Guess company name if not explicitly provided
    resolved_company = company_name or filename.replace(".pdf", "").replace("_", " ")

    doc = Document(
        filename=filename,
        file_path=str(file_dest),
        file_size_bytes=file_size,
        document_type=document_type,
        company_name=resolved_company,
        financial_year=financial_year or 2024,
        status="uploaded",
        chunk_count=0
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    
    logger.info(f"Document registered in DB: {file.filename} (ID: {doc.id})")

    # Ingest document if requested and auto-extract KPIs
    kpi_dict = None
    has_kpis = False
    if auto_process:
        try:
            doc = await document_service.process_document(doc.id, db)
            # Automatically extract structured financial KPIs right after indexing
            try:
                kpi_result = await kpi_extractor.extract_kpis_for_document(doc.id, db)
                if kpi_result and kpi_result.kpi:
                    kpi_dict = kpi_result.kpi.model_dump()
                    has_kpis = True
            except Exception as kpi_err:
                logger.warning(f"Automatic KPI extraction during upload skipped or encountered error: {kpi_err}")
        except Exception as e:
            logger.error(f"Auto-processing failed for {doc.id}: {e}")

    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        file_size_bytes=doc.file_size_bytes,
        document_type=doc.document_type,
        company_name=doc.company_name,
        financial_year=doc.financial_year,
        status=doc.status,
        chunk_count=doc.chunk_count,
        has_kpis=has_kpis,
        kpi=kpi_dict
    )


@router.get("/{document_id}/chunks", response_model=List[ChunkResponse])
async def get_document_chunks(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieves all indexed semantic chunks and metadata for a given document."""
    stmt = (
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
    )
    result = await db.execute(stmt)
    chunks = result.scalars().all()
    if not chunks:
        # Check if document exists
        doc_stmt = select(Document).where(Document.id == document_id)
        doc_result = await db.execute(doc_stmt)
        if not doc_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Document not found.")
    return chunks


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: str, db: AsyncSession = Depends(get_db)):
    """Deletes a document from the disk, ChromaDB collection, and relational DB."""
    deleted = await document_service.delete_document(document_id, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found.")
    return None
