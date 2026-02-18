"""
REST endpoints for knowledge graph entities: people, projects, decisions, topics.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from backend.storage.database import get_db_session
from backend.models.knowledge import (
    ProjectStatus, DecisionStatus, RelationType,
)
from backend.knowledge import entities
from backend.knowledge.graph import knowledge_graph

router = APIRouter(prefix="/api/knowledge")


# ── Schemas ───────────────────────────────────────────────────────────────────

class PersonCreate(BaseModel):
    name: str
    role: Optional[str] = None
    organization: Optional[str] = None
    notes: Optional[str] = None
    speaker_id: Optional[str] = None


class PersonUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    organization: Optional[str] = None
    notes: Optional[str] = None
    speaker_id: Optional[str] = None


class PersonOut(BaseModel):
    id: str
    name: str
    role: Optional[str]
    organization: Optional[str]
    notes: Optional[str]
    speaker_id: Optional[str]
    first_seen: str
    last_seen: str


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    status: Optional[str] = "active"


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class ProjectOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    status: str
    created_at: str
    updated_at: str


class DecisionCreate(BaseModel):
    summary: str
    context: Optional[str] = None
    status: Optional[str] = "proposed"
    confidence: Optional[float] = None
    meeting_id: Optional[str] = None
    project_id: Optional[str] = None
    owner_id: Optional[str] = None


class DecisionUpdate(BaseModel):
    summary: Optional[str] = None
    context: Optional[str] = None
    status: Optional[str] = None
    confidence: Optional[float] = None
    project_id: Optional[str] = None
    owner_id: Optional[str] = None


class DecisionOut(BaseModel):
    id: str
    summary: str
    context: Optional[str]
    status: str
    confidence: Optional[float]
    made_at: str
    meeting_id: Optional[str]
    project_id: Optional[str]
    owner_id: Optional[str]


class TopicCreate(BaseModel):
    name: str
    description: Optional[str] = None


class TopicUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class TopicOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    first_seen: str
    last_seen: str


class RelationCreate(BaseModel):
    source_id: str
    target_id: str
    relation: str
    meeting_id: Optional[str] = ""
    weight: Optional[float] = 1.0


# ── People ────────────────────────────────────────────────────────────────────

@router.post("/people", response_model=PersonOut)
def create_person(req: PersonCreate, db: Session = Depends(get_db_session)):
    existing = entities.find_person_by_name(db, req.name)
    if existing:
        raise HTTPException(409, f"Person '{req.name}' already exists (id: {existing.id})")
    person = entities.create_person(
        db, req.name,
        role=req.role or "",
        organization=req.organization or "",
        notes=req.notes or "",
        speaker_id=req.speaker_id,
    )
    return _person_out(person)


@router.get("/people", response_model=list[PersonOut])
def list_people(limit: int = 100, offset: int = 0, db: Session = Depends(get_db_session)):
    return [_person_out(p) for p in entities.list_people(db, limit, offset)]


@router.get("/people/{person_id}", response_model=PersonOut)
def get_person(person_id: str, db: Session = Depends(get_db_session)):
    person = entities.get_person(db, person_id)
    if not person:
        raise HTTPException(404, "Person not found")
    return _person_out(person)


@router.patch("/people/{person_id}", response_model=PersonOut)
def update_person(person_id: str, req: PersonUpdate, db: Session = Depends(get_db_session)):
    person = entities.update_person(db, person_id, **req.model_dump(exclude_none=True))
    if not person:
        raise HTTPException(404, "Person not found")
    return _person_out(person)


@router.get("/people/{person_id}/connections")
def get_person_connections(person_id: str):
    return entities.get_entity_connections(person_id)


# ── Projects ──────────────────────────────────────────────────────────────────

@router.post("/projects", response_model=ProjectOut)
def create_project(req: ProjectCreate, db: Session = Depends(get_db_session)):
    existing = entities.find_project_by_name(db, req.name)
    if existing:
        raise HTTPException(409, f"Project '{req.name}' already exists (id: {existing.id})")
    status = ProjectStatus(req.status) if req.status else ProjectStatus.active
    project = entities.create_project(db, req.name, description=req.description or "", status=status)
    return _project_out(project)


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(limit: int = 100, offset: int = 0, db: Session = Depends(get_db_session)):
    return [_project_out(p) for p in entities.list_projects(db, limit, offset)]


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db_session)):
    project = entities.get_project(db, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return _project_out(project)


@router.patch("/projects/{project_id}", response_model=ProjectOut)
def update_project(project_id: str, req: ProjectUpdate, db: Session = Depends(get_db_session)):
    update_fields = req.model_dump(exclude_none=True)
    if "status" in update_fields:
        update_fields["status"] = ProjectStatus(update_fields["status"])
    project = entities.update_project(db, project_id, **update_fields)
    if not project:
        raise HTTPException(404, "Project not found")
    return _project_out(project)


@router.get("/projects/{project_id}/connections")
def get_project_connections(project_id: str):
    return entities.get_entity_connections(project_id)


# ── Decisions ─────────────────────────────────────────────────────────────────

@router.post("/decisions", response_model=DecisionOut)
def create_decision(req: DecisionCreate, db: Session = Depends(get_db_session)):
    status = DecisionStatus(req.status) if req.status else DecisionStatus.proposed
    decision = entities.create_decision(
        db, req.summary,
        context=req.context or "",
        status=status,
        confidence=req.confidence,
        meeting_id=req.meeting_id,
        project_id=req.project_id,
        owner_id=req.owner_id,
    )
    return _decision_out(decision)


@router.get("/decisions", response_model=list[DecisionOut])
def list_decisions(
    meeting_id: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db_session),
):
    return [
        _decision_out(d)
        for d in entities.list_decisions(db, meeting_id, project_id, limit, offset)
    ]


@router.get("/decisions/{decision_id}", response_model=DecisionOut)
def get_decision(decision_id: str, db: Session = Depends(get_db_session)):
    decision = entities.get_decision(db, decision_id)
    if not decision:
        raise HTTPException(404, "Decision not found")
    return _decision_out(decision)


@router.patch("/decisions/{decision_id}", response_model=DecisionOut)
def update_decision(decision_id: str, req: DecisionUpdate, db: Session = Depends(get_db_session)):
    update_fields = req.model_dump(exclude_none=True)
    if "status" in update_fields:
        update_fields["status"] = DecisionStatus(update_fields["status"])
    decision = entities.update_decision(db, decision_id, **update_fields)
    if not decision:
        raise HTTPException(404, "Decision not found")
    return _decision_out(decision)


# ── Topics ────────────────────────────────────────────────────────────────────

@router.post("/topics", response_model=TopicOut)
def create_topic(req: TopicCreate, db: Session = Depends(get_db_session)):
    existing = entities.find_topic_by_name(db, req.name)
    if existing:
        raise HTTPException(409, f"Topic '{req.name}' already exists (id: {existing.id})")
    topic = entities.create_topic(db, req.name, description=req.description or "")
    return _topic_out(topic)


@router.get("/topics", response_model=list[TopicOut])
def list_topics(limit: int = 100, offset: int = 0, db: Session = Depends(get_db_session)):
    return [_topic_out(t) for t in entities.list_topics(db, limit, offset)]


@router.get("/topics/{topic_id}", response_model=TopicOut)
def get_topic(topic_id: str, db: Session = Depends(get_db_session)):
    topic = entities.get_topic(db, topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")
    return _topic_out(topic)


@router.patch("/topics/{topic_id}", response_model=TopicOut)
def update_topic(topic_id: str, req: TopicUpdate, db: Session = Depends(get_db_session)):
    topic = entities.update_topic(db, topic_id, **req.model_dump(exclude_none=True))
    if not topic:
        raise HTTPException(404, "Topic not found")
    return _topic_out(topic)


@router.get("/topics/{topic_id}/connections")
def get_topic_connections(topic_id: str):
    return entities.get_entity_connections(topic_id)


# ── Relations & Graph ─────────────────────────────────────────────────────────

@router.post("/relations")
def create_relation(req: RelationCreate):
    try:
        relation = RelationType(req.relation)
    except ValueError:
        valid = [r.value for r in RelationType]
        raise HTTPException(400, f"Invalid relation: {req.relation}. Valid: {valid}")
    ok = entities.add_relation(req.source_id, req.target_id, relation, req.meeting_id or "", req.weight or 1.0)
    if not ok:
        raise HTTPException(404, "One or both entities not found in the graph. Create them first.")
    return {"status": "created", "source": req.source_id, "target": req.target_id, "relation": req.relation}


@router.get("/graph")
def get_graph():
    """Full knowledge graph data (nodes + edges)."""
    return knowledge_graph.export()


@router.get("/graph/stats")
def graph_stats():
    return knowledge_graph.stats()


@router.get("/graph/meeting/{meeting_id}")
def meeting_graph(meeting_id: str):
    """Subgraph of entities referenced in a specific meeting."""
    return entities.get_meeting_graph(meeting_id)


# ── Serializers ───────────────────────────────────────────────────────────────

def _person_out(p) -> PersonOut:
    return PersonOut(
        id=p.id, name=p.name, role=p.role, organization=p.organization,
        notes=p.notes, speaker_id=p.speaker_id,
        first_seen=p.first_seen.isoformat() if p.first_seen else "",
        last_seen=p.last_seen.isoformat() if p.last_seen else "",
    )


def _project_out(p) -> ProjectOut:
    return ProjectOut(
        id=p.id, name=p.name, description=p.description,
        status=p.status.value if p.status else "active",
        created_at=p.created_at.isoformat() if p.created_at else "",
        updated_at=p.updated_at.isoformat() if p.updated_at else "",
    )


def _decision_out(d) -> DecisionOut:
    return DecisionOut(
        id=d.id, summary=d.summary, context=d.context,
        status=d.status.value if d.status else "proposed",
        confidence=d.confidence,
        made_at=d.made_at.isoformat() if d.made_at else "",
        meeting_id=d.meeting_id, project_id=d.project_id, owner_id=d.owner_id,
    )


def _topic_out(t) -> TopicOut:
    return TopicOut(
        id=t.id, name=t.name, description=t.description,
        first_seen=t.first_seen.isoformat() if t.first_seen else "",
        last_seen=t.last_seen.isoformat() if t.last_seen else "",
    )
