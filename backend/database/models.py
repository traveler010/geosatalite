"""
SatQuery AI — SQLAlchemy Relational Models

Defines the 6 core persistence entities:
1. sessions
2. images
3. metadata
4. analysis_results
5. chat_messages
6. execution_logs
"""

from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from backend.database.session import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class SessionRecord(Base):
    """Analysis Session entity tracking context and associated data."""

    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=True, default="New Satellite Session")
    location_name = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    images = relationship("ImageRecord", back_populates="session", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResultRecord", back_populates="session", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessageRecord", back_populates="session", cascade="all, delete-orphan")
    execution_logs = relationship("ExecutionLogRecord", back_populates="session", cascade="all, delete-orphan")


class ImageRecord(Base):
    """Image metadata referencing filesystem storage path."""

    __tablename__ = "images"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)  # Local filesystem path (never store binary blob in SQLite)
    file_size_bytes = Column(Integer, nullable=False, default=0)
    mime_type = Column(String(100), nullable=False, default="image/png")
    format = Column(String(50), nullable=False, default="PNG")  # GeoTIFF, TIFF, PNG, JPEG
    preview_path = Column(Text, nullable=True)  # Path to generated web PNG preview
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("SessionRecord", back_populates="images")
    metadata_record = relationship("MetadataRecord", back_populates="image", uselist=False, cascade="all, delete-orphan")


class MetadataRecord(Base):
    """Detailed geospatial and raster metadata extracted from imagery."""

    __tablename__ = "metadata"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    image_id = Column(String(36), ForeignKey("images.id", ondelete="CASCADE"), nullable=False, unique=True)
    crs = Column(String(255), nullable=True)  # WKT or authority string (e.g. EPSG:32643)
    crs_epsg = Column(Integer, nullable=True)  # Integer EPSG code (e.g. 4326, 32643)
    bounds_native = Column(JSON, nullable=True)  # [minx, miny, maxx, maxy] in native CRS
    bounds_wgs84 = Column(JSON, nullable=True)  # {"min_lat": ..., "min_lon": ..., "max_lat": ..., "max_lon": ...}
    resolution_x = Column(Float, nullable=True)  # Pixel scale in meters/degrees
    resolution_y = Column(Float, nullable=True)
    width = Column(Integer, nullable=False, default=0)
    height = Column(Integer, nullable=False, default=0)
    band_count = Column(Integer, nullable=False, default=3)
    band_names = Column(JSON, nullable=True)  # List of band descriptions
    data_type = Column(String(50), nullable=True, default="uint8")
    is_geotiff = Column(Boolean, nullable=False, default=False)
    is_multispectral = Column(Boolean, nullable=False, default=False)
    raw_tags = Column(JSON, nullable=True)  # Raw driver and TIFF metadata tags
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    image = relationship("ImageRecord", back_populates="metadata_record")


class AnalysisResultRecord(Base):
    """Persisted query outputs, answers, confidence scores, and visual evidence."""

    __tablename__ = "analysis_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    query_id = Column(String(64), nullable=False, index=True)
    task_type = Column(String(50), nullable=False)  # vqa, captioning, grounding, change_detection, optical_sar
    tool_used = Column(String(100), nullable=False)
    confidence = Column(Float, nullable=False, default=0.0)
    answer = Column(Text, nullable=False)
    reasoning = Column(Text, nullable=True)
    evidence_json = Column(JSON, nullable=True)  # Bounding boxes, change masks, land cover classes
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("SessionRecord", back_populates="analysis_results")


class ChatMessageRecord(Base):
    """Multi-turn conversation history tied to an analysis session."""

    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("SessionRecord", back_populates="chat_messages")


class ExecutionLogRecord(Base):
    """Step-by-step observable execution trace for auditing and grading."""

    __tablename__ = "execution_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    query_id = Column(String(64), nullable=False, index=True)
    step_index = Column(Integer, nullable=False, default=0)
    action = Column(String(100), nullable=False)  # input_validation, task_routing, model_inference, etc.
    status = Column(String(30), nullable=False, default="SUCCESS")  # SUCCESS, FAILED
    duration_ms = Column(Float, nullable=False, default=0.0)
    details_json = Column(JSON, nullable=True)  # Observable summary, parameters passed, outputs
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("SessionRecord", back_populates="execution_logs")
