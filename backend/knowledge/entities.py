"""
CRUD operations for knowledge graph entities.

Every create/update also syncs the entity into the NetworkX graph so the
relational DB and the graph stay consistent.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.knowledge import (
    Person, Project, Decision, Topic,
    PersonMeeting, ProjectMeeting, TopicMeeting,
    ProjectStatus, DecisionStatus, RelationType,
)
from backend.knowledge.graph import knowledge_graph as kg

logger = logging.getLogger(__name__)


# ── People ────────────────────────────────────────────────────────────────────

def create_person(
    db: Session,
    name: str,
    role: str = "",
    organization: str = "",
    notes: str = "",
    speaker_id: Optional[str] = None,
) -> Person:
    person = Person(
        name=name,
        role=role or None,
        organization=organization or None,
        notes=notes or None,
        speaker_id=speaker_id,
    )
    db.add(person)
    db.flush()
    kg.add_entity(person.id, "person", person.name)
    logger.info(f"Person created: {name} ({person.id[:8]})")
    return person


def update_person(db: Session, person_id: str, **fields) -> Optional[Person]:
    person = db.get(Person, person_id)
    if not person:
        return None
    for key, value in fields.items():
        if hasattr(person, key) and value is not None:
            setattr(person, key, value)
    person.last_seen = datetime.now(timezone.utc)
    db.flush()
    kg.add_entity(person.id, "person", person.name)
    return person


def get_person(db: Session, person_id: str) -> Optional[Person]:
    return db.get(Person, person_id)


def find_person_by_name(db: Session, name: str) -> Optional[Person]:
    return db.query(Person).filter(Person.name.ilike(name)).first()


def list_people(db: Session, limit: int = 100, offset: int = 0) -> list[Person]:
    return (
        db.query(Person)
        .order_by(Person.last_seen.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def link_person_to_meeting(
    db: Session, person_id: str, meeting_id: str, role_in_meeting: str = "attendee"
):
    existing = (
        db.query(PersonMeeting)
        .filter_by(person_id=person_id, meeting_id=meeting_id)
        .first()
    )
    if not existing:
        db.add(PersonMeeting(
            person_id=person_id,
            meeting_id=meeting_id,
            role_in_meeting=role_in_meeting,
        ))
        db.flush()


# ── Projects ──────────────────────────────────────────────────────────────────

def create_project(
    db: Session,
    name: str,
    description: str = "",
    status: ProjectStatus = ProjectStatus.active,
) -> Project:
    project = Project(
        name=name,
        description=description or None,
        status=status,
    )
    db.add(project)
    db.flush()
    kg.add_entity(project.id, "project", project.name)
    logger.info(f"Project created: {name} ({project.id[:8]})")
    return project


def update_project(db: Session, project_id: str, **fields) -> Optional[Project]:
    project = db.get(Project, project_id)
    if not project:
        return None
    for key, value in fields.items():
        if hasattr(project, key) and value is not None:
            setattr(project, key, value)
    db.flush()
    kg.add_entity(project.id, "project", project.name)
    return project


def get_project(db: Session, project_id: str) -> Optional[Project]:
    return db.get(Project, project_id)


def find_project_by_name(db: Session, name: str) -> Optional[Project]:
    return db.query(Project).filter(Project.name.ilike(name)).first()


def list_projects(db: Session, limit: int = 100, offset: int = 0) -> list[Project]:
    return (
        db.query(Project)
        .order_by(Project.updated_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def link_project_to_meeting(db: Session, project_id: str, meeting_id: str):
    existing = (
        db.query(ProjectMeeting)
        .filter_by(project_id=project_id, meeting_id=meeting_id)
        .first()
    )
    if not existing:
        db.add(ProjectMeeting(project_id=project_id, meeting_id=meeting_id))
        db.flush()


# ── Decisions ─────────────────────────────────────────────────────────────────

def create_decision(
    db: Session,
    summary: str,
    context: str = "",
    status: DecisionStatus = DecisionStatus.proposed,
    confidence: Optional[float] = None,
    meeting_id: Optional[str] = None,
    project_id: Optional[str] = None,
    owner_id: Optional[str] = None,
) -> Decision:
    decision = Decision(
        summary=summary,
        context=context or None,
        status=status,
        confidence=confidence,
        meeting_id=meeting_id,
        project_id=project_id,
        owner_id=owner_id,
    )
    db.add(decision)
    db.flush()
    kg.add_entity(decision.id, "decision", summary[:80])

    # Auto-link to project and meeting in graph
    if project_id:
        kg.add_relation(decision.id, project_id, RelationType.impacts, meeting_id=meeting_id or "")
    if owner_id:
        kg.add_relation(owner_id, decision.id, RelationType.mentions, meeting_id=meeting_id or "")

    logger.info(f"Decision created: {summary[:60]} ({decision.id[:8]})")
    return decision


def update_decision(db: Session, decision_id: str, **fields) -> Optional[Decision]:
    decision = db.get(Decision, decision_id)
    if not decision:
        return None
    for key, value in fields.items():
        if hasattr(decision, key) and value is not None:
            setattr(decision, key, value)
    db.flush()
    kg.add_entity(decision.id, "decision", decision.summary[:80])
    return decision


def get_decision(db: Session, decision_id: str) -> Optional[Decision]:
    return db.get(Decision, decision_id)


def list_decisions(
    db: Session,
    meeting_id: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Decision]:
    q = db.query(Decision)
    if meeting_id:
        q = q.filter(Decision.meeting_id == meeting_id)
    if project_id:
        q = q.filter(Decision.project_id == project_id)
    return q.order_by(Decision.made_at.desc()).offset(offset).limit(limit).all()


# ── Topics ────────────────────────────────────────────────────────────────────

def create_topic(db: Session, name: str, description: str = "") -> Topic:
    topic = Topic(name=name, description=description or None)
    db.add(topic)
    db.flush()
    kg.add_entity(topic.id, "topic", topic.name)
    logger.info(f"Topic created: {name} ({topic.id[:8]})")
    return topic


def update_topic(db: Session, topic_id: str, **fields) -> Optional[Topic]:
    topic = db.get(Topic, topic_id)
    if not topic:
        return None
    for key, value in fields.items():
        if hasattr(topic, key) and value is not None:
            setattr(topic, key, value)
    topic.last_seen = datetime.now(timezone.utc)
    db.flush()
    kg.add_entity(topic.id, "topic", topic.name)
    return topic


def get_topic(db: Session, topic_id: str) -> Optional[Topic]:
    return db.get(Topic, topic_id)


def find_topic_by_name(db: Session, name: str) -> Optional[Topic]:
    return db.query(Topic).filter(Topic.name.ilike(name)).first()


def list_topics(db: Session, limit: int = 100, offset: int = 0) -> list[Topic]:
    return (
        db.query(Topic)
        .order_by(Topic.last_seen.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def link_topic_to_meeting(db: Session, topic_id: str, meeting_id: str):
    existing = (
        db.query(TopicMeeting)
        .filter_by(topic_id=topic_id, meeting_id=meeting_id)
        .first()
    )
    if not existing:
        db.add(TopicMeeting(topic_id=topic_id, meeting_id=meeting_id))
        db.flush()


# ── Cross-Entity Relations ────────────────────────────────────────────────────

def add_relation(
    source_id: str,
    target_id: str,
    relation: RelationType,
    meeting_id: str = "",
    weight: float = 1.0,
) -> bool:
    """Add a typed relationship between any two entities in the graph."""
    return kg.add_relation(source_id, target_id, relation, meeting_id=meeting_id, weight=weight)


def get_entity_connections(entity_id: str) -> list[dict]:
    """Get all relationships for an entity."""
    return kg.get_connections(entity_id)


def get_entity_neighbors(entity_id: str, relation: Optional[RelationType] = None) -> list[dict]:
    """Get neighboring entities, optionally filtered by relation type."""
    return kg.get_neighbors(entity_id, relation)


def get_meeting_graph(meeting_id: str) -> dict:
    """Get the subgraph of entities referenced in a specific meeting."""
    return kg.get_subgraph_for_meeting(meeting_id)
