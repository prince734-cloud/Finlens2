import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.database.connection import get_db
from backend.app.database.models import ChatHistory
from backend.app.rag.analyst_service import REGULATORY_DISCLAIMER, unified_analyst
from backend.app.rag.citations import CitationItem
from backend.app.utils.logger import logger

router = APIRouter(prefix="/chat", tags=["AI Financial Analyst"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Financial research question")
    session_id: Optional[str] = Field(None, description="Client session identifier")
    document_id: Optional[str] = Field(None, description="Optional document filter")
    company_name: Optional[str] = Field(None, description="Optional company filter")


class ChatResponse(BaseModel):
    answer: str
    query_type: str = "document_rag"
    citations: List[CitationItem] = []
    session_id: str
    disclaimer: str = REGULATORY_DISCLAIMER


class ChatMessageItem(BaseModel):
    id: str
    role: str
    query_type: Optional[str] = None
    message: str
    citations: List[Dict[str, Any]] = []
    created_at: str


class ChatSessionSummary(BaseModel):
    session_id: str
    last_message: str
    message_count: int
    query_type: Optional[str] = None
    last_active: str


@router.post("", response_model=ChatResponse)
async def query_analyst(payload: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Synchronous analyst query endpoint:
    Classifies intent across Document RAG, Company Research, Mutual Fund Analytics,
    Deterministic Recommendations, and Financial Concepts.
    Synthesizes fact-grounded response with verifiable citations and persists turn.
    """
    session_id = payload.session_id or str(uuid.uuid4())
    query = payload.message.strip()

    logger.info(f"Received query for session {session_id}: '{query[:80]}...'")

    answer, intent, citations, disclaimer = await unified_analyst.execute_turn(
        query=query,
        session_id=session_id,
        db=db,
        document_id=payload.document_id,
        company_name=payload.company_name
    )

    return ChatResponse(
        answer=answer,
        query_type=intent.value,
        citations=citations,
        session_id=session_id,
        disclaimer=disclaimer
    )


@router.post("/stream")
async def stream_analyst(payload: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Server-Sent Events (SSE) streaming endpoint:
    Streams real-time tokens with event headers:
    - 'intent': Detected query category & extracted entities
    - 'token': Incremental synthesized words
    - 'citations': Verified source citations
    - 'done': Final execution payload and regulatory disclaimer
    """
    session_id = payload.session_id or str(uuid.uuid4())
    query = payload.message.strip()

    logger.info(f"Initiating SSE stream for session {session_id}: '{query[:80]}...'")

    generator = unified_analyst.stream_turn(
        query=query,
        session_id=session_id,
        db=db,
        document_id=payload.document_id,
        company_name=payload.company_name
    )

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/sessions", response_model=List[ChatSessionSummary])
async def list_sessions(db: AsyncSession = Depends(get_db)):
    """
    Retrieves distinct chat sessions with latest message preview and message count.
    """
    try:
        # Group by session_id to get message count and last message
        subq = (
            select(
                ChatHistory.session_id,
                func.count(ChatHistory.id).label("message_count"),
                func.max(ChatHistory.created_at).label("last_active")
            )
            .group_by(ChatHistory.session_id)
            .subquery()
        )

        stmt = (
            select(ChatHistory, subq.c.message_count)
            .join(
                subq,
                (ChatHistory.session_id == subq.c.session_id) &
                (ChatHistory.created_at == subq.c.last_active)
            )
            .order_by(subq.c.last_active.desc())
        )

        result = await db.execute(stmt)
        rows = result.all()

        summaries = []
        seen_sessions = set()
        for chat_record, count in rows:
            if chat_record.session_id in seen_sessions:
                continue
            seen_sessions.add(chat_record.session_id)
            summaries.append(
                ChatSessionSummary(
                    session_id=chat_record.session_id,
                    last_message=chat_record.message[:120],
                    message_count=count,
                    query_type=chat_record.query_type,
                    last_active=chat_record.created_at.isoformat() if chat_record.created_at else ""
                )
            )
        return summaries
    except Exception as e:
        logger.error(f"Error fetching chat sessions: {e}")
        return []


@router.get("/sessions/{session_id}", response_model=List[ChatMessageItem])
async def get_session_messages(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieves full chronological message history for a specific conversation session.
    """
    stmt = (
        select(ChatHistory)
        .where(ChatHistory.session_id == session_id)
        .order_by(ChatHistory.created_at.asc())
    )
    result = await db.execute(stmt)
    records = list(result.scalars().all())

    return [
        ChatMessageItem(
            id=r.id,
            role=r.role,
            query_type=r.query_type,
            message=r.message,
            citations=r.citations or [],
            created_at=r.created_at.isoformat() if r.created_at else ""
        )
        for r in records
    ]


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    Deletes all conversation history for a specific session.
    """
    stmt = delete(ChatHistory).where(ChatHistory.session_id == session_id)
    result = await db.execute(stmt)
    await db.commit()

    return {
        "status": "success",
        "session_id": session_id,
        "deleted_count": result.rowcount
    }
