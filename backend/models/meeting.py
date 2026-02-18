from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text,
    DateTime, ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid

from backend.storage.database import Base


def generate_id():
    return str(uuid.uuid4())


class MeetingStatus(str, enum.Enum):
    recording = "recording"
    processing = "processing"
    complete = "complete"
    failed = "failed"


class AudioSource(str, enum.Enum):
    microphone = "microphone"
    system = "system"
    both = "both"


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(String, primary_key=True, default=generate_id)
    title = Column(String, nullable=True)
    status = Column(SAEnum(MeetingStatus), default=MeetingStatus.recording, nullable=False)
    audio_source = Column(SAEnum(AudioSource), default=AudioSource.microphone, nullable=False)

    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)

    raw_audio_path = Column(String, nullable=True)
    compressed_audio_path = Column(String, nullable=True)
    audio_compressed = Column(Boolean, default=False)

    # Relationships
    segments = relationship("TranscriptSegment", back_populates="meeting", cascade="all, delete-orphan")
    speakers = relationship("MeetingSpeaker", back_populates="meeting", cascade="all, delete-orphan")
    analysis = relationship("MeetingAnalysis", back_populates="meeting", uselist=False, cascade="all, delete-orphan")


class Speaker(Base):
    __tablename__ = "speakers"

    id = Column(String, primary_key=True, default=generate_id)
    label = Column(String, nullable=False)           # "Speaker 1", "Marco", etc.
    name = Column(String, nullable=True)             # User-assigned name
    voice_profile_path = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    meetings = relationship("MeetingSpeaker", back_populates="speaker")
    segments = relationship("TranscriptSegment", back_populates="speaker")


class MeetingSpeaker(Base):
    """Maps speakers to meetings (many-to-many)."""
    __tablename__ = "meeting_speakers"

    id = Column(String, primary_key=True, default=generate_id)
    meeting_id = Column(String, ForeignKey("meetings.id"), nullable=False)
    speaker_id = Column(String, ForeignKey("speakers.id"), nullable=False)
    diarization_label = Column(String, nullable=False)  # e.g. "SPEAKER_00"

    meeting = relationship("Meeting", back_populates="speakers")
    speaker = relationship("Speaker", back_populates="meetings")


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id = Column(String, primary_key=True, default=generate_id)
    meeting_id = Column(String, ForeignKey("meetings.id"), nullable=False)
    speaker_id = Column(String, ForeignKey("speakers.id"), nullable=True)

    start_time = Column(Float, nullable=False)    # seconds from meeting start
    end_time = Column(Float, nullable=False)
    text = Column(Text, nullable=False)
    language = Column(String, nullable=True)      # detected language code
    confidence = Column(Float, nullable=True)     # 0.0 - 1.0
    is_low_confidence = Column(Boolean, default=False)

    # Source tracking
    transcription_source = Column(String, default="local")  # "local" | "deepgram" | "assemblyai"

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    meeting = relationship("Meeting", back_populates="segments")
    speaker = relationship("Speaker", back_populates="segments")


class MeetingAnalysis(Base):
    __tablename__ = "meeting_analyses"

    id = Column(String, primary_key=True, default=generate_id)
    meeting_id = Column(String, ForeignKey("meetings.id"), nullable=False, unique=True)

    executive_summary = Column(Text, nullable=False, default="")
    meeting_type = Column(String, nullable=True)       # standup, planning, review, etc.
    sentiment = Column(String, nullable=True)           # positive, neutral, mixed, tense
    overall_confidence = Column(Float, nullable=False, default=0.0)
    llm_provider = Column(String, nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=False)
    processing_duration_seconds = Column(Float, nullable=True)

    # Connection detection results (JSON)
    connections_data = Column(Text, nullable=True)
    # Generated insights (JSON array)
    insights_data = Column(Text, nullable=True)

    meeting = relationship("Meeting", back_populates="analysis")
    action_items = relationship("ActionItem", back_populates="analysis", cascade="all, delete-orphan")
    decisions = relationship("AnalysisDecision", back_populates="analysis", cascade="all, delete-orphan")
    topics = relationship("TopicSegment", back_populates="analysis", cascade="all, delete-orphan")
    corrections = relationship("UserCorrection", back_populates="analysis", cascade="all, delete-orphan")


class ActionItem(Base):
    __tablename__ = "action_items"

    id = Column(String, primary_key=True, default=generate_id)
    analysis_id = Column(String, ForeignKey("meeting_analyses.id"), nullable=False)

    description = Column(Text, nullable=False)
    owner = Column(String, nullable=True)
    deadline = Column(String, nullable=True)
    priority = Column(String, default="medium")         # high, medium, low
    confidence = Column(Float, default=0.5)
    source_quote = Column(Text, nullable=True)
    source_start_time = Column(Float, nullable=True)
    source_end_time = Column(Float, nullable=True)

    analysis = relationship("MeetingAnalysis", back_populates="action_items")


class AnalysisDecision(Base):
    __tablename__ = "analysis_decisions"

    id = Column(String, primary_key=True, default=generate_id)
    analysis_id = Column(String, ForeignKey("meeting_analyses.id"), nullable=False)

    description = Column(Text, nullable=False)
    context = Column(Text, nullable=True)
    participants = Column(Text, nullable=True)          # JSON array of names
    confidence = Column(Float, default=0.5)
    source_quote = Column(Text, nullable=True)
    source_start_time = Column(Float, nullable=True)
    source_end_time = Column(Float, nullable=True)

    analysis = relationship("MeetingAnalysis", back_populates="decisions")


class TopicSegment(Base):
    __tablename__ = "topic_segments"

    id = Column(String, primary_key=True, default=generate_id)
    analysis_id = Column(String, ForeignKey("meeting_analyses.id"), nullable=False)

    title = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    start_time = Column(Float, nullable=False, default=0.0)
    end_time = Column(Float, nullable=False, default=0.0)
    order_index = Column(Integer, nullable=False, default=0)
    confidence = Column(Float, default=0.5)
    related_segment_ids = Column(Text, nullable=True)   # JSON array of indices

    analysis = relationship("MeetingAnalysis", back_populates="topics")


class UserCorrection(Base):
    """Tracks user corrections and edits as learning signals."""
    __tablename__ = "user_corrections"

    id = Column(String, primary_key=True, default=generate_id)
    analysis_id = Column(String, ForeignKey("meeting_analyses.id"), nullable=True)
    meeting_id = Column(String, ForeignKey("meetings.id"), nullable=False)

    correction_type = Column(String, nullable=False)
    # "transcript" | "summary" | "action_item" | "decision" | "topic" | "insight"
    target_id = Column(String, nullable=True)           # ID of the item corrected
    field_name = Column(String, nullable=True)           # Which field was changed
    original_value = Column(Text, nullable=True)
    corrected_value = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    analysis = relationship("MeetingAnalysis", back_populates="corrections")
    meeting = relationship("Meeting", backref="corrections")
