"""
SatQuery AI — Session Management Service

Handles relational persistence for sessions, uploaded images, geospatial metadata,
analysis results, chat history, and observable execution logs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.core.logging import get_logger
from backend.database.models import (
    AnalysisResultRecord,
    ChatMessageRecord,
    ExecutionLogRecord,
    ImageRecord,
    MetadataRecord,
    SessionRecord,
)

logger = get_logger("services.session")


class SessionService:
    """Provides high-level CRUD operations for SatQuery analysis sessions."""

    @staticmethod
    def create_session(
        db: Session,
        title: Optional[str] = "New Satellite Session",
        location_name: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> SessionRecord:
        record = SessionRecord(
            title=title,
            location_name=location_name,
            latitude=latitude,
            longitude=longitude,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        logger.info(f"Created session {record.id} ({record.title})")
        return record

    @staticmethod
    def get_session(db: Session, session_id: str) -> Optional[SessionRecord]:
        return db.query(SessionRecord).filter(SessionRecord.id == session_id).first()

    @staticmethod
    def list_sessions(db: Session, limit: int = 50, offset: int = 0) -> List[SessionRecord]:
        return db.query(SessionRecord).order_by(SessionRecord.created_at.desc()).offset(offset).limit(limit).all()

    @staticmethod
    def delete_session(db: Session, session_id: str) -> bool:
        session = db.query(SessionRecord).filter(SessionRecord.id == session_id).first()
        if session:
            db.delete(session)
            db.commit()
            return True
        return False

    @staticmethod
    def get_image(db: Session, image_id: str) -> Optional[ImageRecord]:
        return db.query(ImageRecord).filter(ImageRecord.id == image_id).first()

    @staticmethod
    def add_image_to_session(
        db: Session,
        session_id: str,
        filename: str,
        file_path: str,
        file_size_bytes: int,
        mime_type: str,
        format_type: str,
        metadata_dict: Dict[str, Any],
        preview_path: Optional[str] = None,
    ) -> ImageRecord:
        # Ensure session exists
        session = db.query(SessionRecord).filter(SessionRecord.id == session_id).first()
        if not session:
            session = SessionRecord(id=session_id, title=f"Session for {filename}")
            db.add(session)
            db.flush()

        img_record = ImageRecord(
            session_id=session_id,
            filename=filename,
            file_path=file_path,
            file_size_bytes=file_size_bytes,
            mime_type=mime_type,
            format=format_type,
            preview_path=preview_path,
        )
        db.add(img_record)
        db.flush()

        # Add detailed metadata record
        meta_record = MetadataRecord(
            image_id=img_record.id,
            crs=metadata_dict.get("crs"),
            crs_epsg=metadata_dict.get("crs_epsg"),
            bounds_native=metadata_dict.get("bounds_native"),
            bounds_wgs84=metadata_dict.get("bounds_wgs84"),
            resolution_x=metadata_dict.get("resolution_x"),
            resolution_y=metadata_dict.get("resolution_y"),
            width=metadata_dict.get("width", 0),
            height=metadata_dict.get("height", 0),
            band_count=metadata_dict.get("band_count", 3),
            band_names=metadata_dict.get("band_names"),
            data_type=metadata_dict.get("data_type"),
            is_geotiff=metadata_dict.get("is_geotiff", False),
            is_multispectral=metadata_dict.get("is_multispectral", False),
            raw_tags=metadata_dict.get("raw_tags"),
        )
        db.add(meta_record)

        # Update session coordinates if available
        if metadata_dict.get("bounds_wgs84"):
            b = metadata_dict["bounds_wgs84"]
            session.latitude = (b["min_lat"] + b["max_lat"]) / 2.0
            session.longitude = (b["min_lon"] + b["max_lon"]) / 2.0

        db.commit()
        db.refresh(img_record)
        logger.info(f"Registered image '{filename}' ({img_record.id}) to session {session_id}")
        return img_record

    @staticmethod
    def record_analysis_result(
        db: Session,
        session_id: str,
        query_id: str,
        task_type: str,
        tool_used: str,
        confidence: float,
        answer: str,
        reasoning: Optional[str] = None,
        evidence_json: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResultRecord:
        record = AnalysisResultRecord(
            session_id=session_id,
            query_id=query_id,
            task_type=task_type,
            tool_used=tool_used,
            confidence=confidence,
            answer=answer,
            reasoning=reasoning,
            evidence_json=evidence_json,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def record_chat_message(
        db: Session,
        session_id: str,
        role: str,
        content: str,
        reasoning: Optional[str] = None,
    ) -> ChatMessageRecord:
        msg = ChatMessageRecord(
            session_id=session_id,
            role=role,
            content=content,
            reasoning=reasoning,
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg

    @staticmethod
    def get_session_images(db: Session, session_id: str) -> List[ImageRecord]:
        return db.query(ImageRecord).filter(ImageRecord.session_id == session_id).order_by(ImageRecord.created_at.asc()).all()

    @staticmethod
    def get_session_chat_history(
        db: Session,
        session_id: str,
        limit: int = 50,
    ) -> List[ChatMessageRecord]:
        return (
            db.query(ChatMessageRecord)
            .filter(ChatMessageRecord.session_id == session_id)
            .order_by(ChatMessageRecord.created_at.asc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_session_analysis_history(
        db: Session,
        session_id: str,
        limit: int = 50,
    ) -> List[AnalysisResultRecord]:
        return (
            db.query(AnalysisResultRecord)
            .filter(AnalysisResultRecord.session_id == session_id)
            .order_by(AnalysisResultRecord.created_at.asc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def record_execution_log(
        db: Session,
        session_id: str,
        query_id: str,
        step_index: int,
        action: str,
        status: str,
        duration_ms: float,
        details_json: Optional[Dict[str, Any]] = None,
    ) -> ExecutionLogRecord:
        log = ExecutionLogRecord(
            session_id=session_id,
            query_id=query_id,
            step_index=step_index,
            action=action,
            status=status,
            duration_ms=duration_ms,
            details_json=details_json,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

