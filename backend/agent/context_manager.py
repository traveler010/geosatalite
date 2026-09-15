"""
SatQuery AI — Agent Context Manager

Maintains session memory, spatial coordinate context, and conversation history.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.core.logging import get_logger
from backend.database.models import ChatMessageRecord, SessionRecord
from backend.services.session_service import SessionService

logger = get_logger("agent.context")


class AgentContextManager:
    """Manages active session context across queries."""

    def __init__(self, db: Session, session_id: str):
        self.db = db
        self.session_id = session_id

    def get_active_context(self) -> Dict[str, Any]:
        """Retrieve current session context dictionary for prompt injection."""
        session = SessionService.get_session(self.db, self.session_id)
        if not session:
            return {"session_id": self.session_id}

        recent_messages = (
            self.db.query(ChatMessageRecord)
            .filter(ChatMessageRecord.session_id == self.session_id)
            .order_by(ChatMessageRecord.created_at.desc())
            .limit(4)
            .all()
        )

        history = [{"role": m.role, "content": m.content} for m in reversed(recent_messages)]

        return {
            "session_id": self.session_id,
            "title": session.title,
            "location": session.location_name,
            "latitude": session.latitude,
            "longitude": session.longitude,
            "recent_turns": history,
            "image_count": len(session.images),
        }

    def record_turn(self, user_query: str, assistant_answer: str, reasoning: Optional[str] = None) -> None:
        SessionService.record_chat_message(self.db, self.session_id, "user", user_query)
        SessionService.record_chat_message(self.db, self.session_id, "assistant", assistant_answer, reasoning=reasoning)
