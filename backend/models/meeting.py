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
