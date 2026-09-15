"""
SatQuery AI — Session-Aware AI Chat API Endpoints

Provides REST endpoints for Phase 9:
- Multi-turn conversational chat grounded in session images and specialist analysis.
- Cached analysis retrieval (zero redundant vision/raster computation).
- Dynamic provider resolution (Ollama, DeepSeek, LocalLLM fallback).
- Chat message history retrieval.
- Session analysis cache introspection.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.services.chatbot_service import answer_session_chat
from backend.services.context_manager import SessionContextManager
from backend.services.session_service import SessionService

router = APIRouter(prefix="/api/sessions", tags=["Session-Aware AI Chat"])


class SessionChatRequest(BaseModel):
    message: str = Field(..., description="User question or follow-up instruction")
    preferred_provider: Optional[str] = Field(
        default=None,
        description="Optional preferred provider: 'ollama', 'deepseek', or 'local_llm'",
    )
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=4096, ge=1, le=8192)


class SessionChatResponse(BaseModel):
    success: bool
    session_id: str
    query_id: str
    answer: str
    reasoning: Optional[str] = None
    model: str
    provider: str
    used_cached_analysis: bool
    cache_reason: str
    latency_ms: float
    history_length: int


@router.post(
    "/{session_id}/chat",
    response_model=SessionChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a message to the session-aware AI assistant",
)
async def session_chat(
    session_id: str,
    payload: SessionChatRequest,
    db: Session = Depends(get_db),
):
    """
    Execute a multi-turn conversation turn for the specified session.

    The chat engine adheres strictly to the rule:
    'The chat must answer using cached analysis unless a new model is required.'

    Prior findings from VQA, scene captioning, change detection, and Optical+SAR
    fusion are injected into the grounding prompt without re-running vision models.
    """
    # Verify session exists
    session = SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    res = await answer_session_chat(
        session_id=session_id,
        prompt=payload.message,
        db=db,
        preferred_provider=payload.preferred_provider,
        temperature=payload.temperature or 0.7,
        max_tokens=payload.max_tokens or 4096,
    )

    return res


@router.get(
    "/{session_id}/chat/history",
    status_code=status.HTTP_200_OK,
    summary="Get multi-turn conversation history for a session",
)
async def get_chat_history(
    session_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Retrieve chronological multi-turn chat messages recorded for this session."""
    session = SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    records = SessionService.get_session_chat_history(db, session_id, limit=limit)
    messages = [
        {
            "id": r.id,
            "role": r.role,
            "content": r.content,
            "reasoning": r.reasoning,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]

    return {
        "session_id": session_id,
        "total_messages": len(messages),
        "messages": messages,
    }


@router.get(
    "/{session_id}/cache",
    status_code=status.HTTP_200_OK,
    summary="Get cached analysis facts and metadata for a session",
)
async def get_session_cache(
    session_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve structured facts, image metadata, and cached specialist analysis
    outputs currently compiled in this session's context manager.
    """
    session = SessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )

    facts = SessionContextManager.get_session_facts(session_id, db)
    return facts
