"""
Knowledge graph entities — platform-level, not meeting-specific.

Entities:
  Person   — Anyone encountered in meetings or mentioned in context.
  Project  — A body of work, initiative, or ongoing effort.
  Decision — A concrete choice or agreement captured from a meeting.
  Topic    — A recurring subject or theme that surfaces across meetings.

These are first-class entities in the shared data platform.
LIME (meetings) is the first consumer; future tools will use the same entities.
"""

from sqlalchemy import (
    Column, String, Text, DateTime, Float, ForeignKey,
    Enum as SAEnum, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from backend.storage.database import Base
from backend.models.meeting import generate_id


# ── Enums ─────────────────────────────────────────────────────────────────────

class ProjectStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    completed = "completed"
    archived = "archived"


class DecisionStatus(str, enum.Enum):
    proposed = "proposed"
    confirmed = "confirmed"
    reversed = "reversed"


class RelationType(str, enum.Enum):
    """Edge types for the knowledge graph."""
    # Person ↔ Project
    works_on = "works_on"
    leads = "leads"
    stakeholder = "stakeholder"
    # Person ↔ Person
    works_with = "works_with"
    reports_to = "reports_to"
    # Person ↔ Topic
    discusses = "discusses"
    # Project ↔ Topic
    related_to = "related_to"
    # Decision ↔ Project
    impacts = "impacts"
    # Generic
    mentions = "mentions"


# ── Core Entities ─────────────────────────────────────────────────────────────

class Person(Base):
    __tablename__ = "people"

    id = Column(String, primary_key=True, default=generate_id)
    name = Column(String, nullable=False, unique=True)
    role = Column(String, nullable=True)
    organization = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Link to Speaker voice identity (optional)
    speaker_id = Column(String, ForeignKey("speakers.id"), nullable=True)
    speaker = relationship("Speaker", backref="person", uselist=False)

    # Relationships
    meeting_mentions = relationship("PersonMeeting", back_populates="person", cascade="all, delete-orphan")
    decisions_made = relationship("Decision", back_populates="owner", foreign_keys="Decision.owner_id")


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=generate_id)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    status = Column(SAEnum(ProjectStatus), default=ProjectStatus.active)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    decisions = relationship("Decision", back_populates="project")
    meeting_mentions = relationship("ProjectMeeting", back_populates="project", cascade="all, delete-orphan")


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(String, primary_key=True, default=generate_id)
    summary = Column(Text, nullable=False)
    context = Column(Text, nullable=True)
    status = Column(SAEnum(DecisionStatus), default=DecisionStatus.proposed)
    confidence = Column(Float, nullable=True)  # 0.0-1.0

    made_at = Column(DateTime(timezone=True), server_default=func.now())
    meeting_id = Column(String, ForeignKey("meetings.id"), nullable=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=True)
    owner_id = Column(String, ForeignKey("people.id"), nullable=True)

    # Relationships
    meeting = relationship("Meeting", backref="decisions")
    project = relationship("Project", back_populates="decisions")
    owner = relationship("Person", back_populates="decisions_made", foreign_keys=[owner_id])


class Topic(Base):
    __tablename__ = "topics"

    id = Column(String, primary_key=True, default=generate_id)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    meeting_mentions = relationship("TopicMeeting", back_populates="topic", cascade="all, delete-orphan")


# ── Junction Tables (Entity ↔ Meeting) ───────────────────────────────────────

class PersonMeeting(Base):
    """Tracks which people were mentioned/present in which meetings."""
    __tablename__ = "person_meetings"
    __table_args__ = (UniqueConstraint("person_id", "meeting_id"),)

    id = Column(String, primary_key=True, default=generate_id)
    person_id = Column(String, ForeignKey("people.id"), nullable=False)
    meeting_id = Column(String, ForeignKey("meetings.id"), nullable=False)
    role_in_meeting = Column(String, nullable=True)  # "attendee", "mentioned", etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    person = relationship("Person", back_populates="meeting_mentions")
    meeting = relationship("Meeting", backref="people_mentioned")


class ProjectMeeting(Base):
    """Tracks which projects were discussed in which meetings."""
    __tablename__ = "project_meetings"
    __table_args__ = (UniqueConstraint("project_id", "meeting_id"),)

    id = Column(String, primary_key=True, default=generate_id)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    meeting_id = Column(String, ForeignKey("meetings.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="meeting_mentions")
    meeting = relationship("Meeting", backref="projects_mentioned")


class TopicMeeting(Base):
    """Tracks which topics were discussed in which meetings."""
    __tablename__ = "topic_meetings"
    __table_args__ = (UniqueConstraint("topic_id", "meeting_id"),)

    id = Column(String, primary_key=True, default=generate_id)
    topic_id = Column(String, ForeignKey("topics.id"), nullable=False)
    meeting_id = Column(String, ForeignKey("meetings.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    topic = relationship("Topic", back_populates="meeting_mentions")
    meeting = relationship("Meeting", backref="topics_mentioned")
