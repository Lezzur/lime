"""
Connection detection — links current meeting content to past meetings and known entities.

Detects:
  - References to known people, projects, topics in the knowledge graph
  - Links to past meetings discussing similar topics (via ChromaDB semantic search)
  - Contradictions with previously recorded information
  - Unresolved threads from past meetings that are relevant
"""

import json
import logging
from typing import Optional

from backend.config.settings import settings
from backend.intelligence.llm import llm_client
from backend.knowledge.graph import knowledge_graph as kg
from backend.knowledge.entities import (
    find_person_by_name, find_project_by_name, find_topic_by_name,
    link_person_to_meeting, link_project_to_meeting, link_topic_to_meeting,
)
from backend.storage.vector_store import vector_store
from backend.storage.database import get_db
from backend.models.meeting import Meeting, MeetingAnalysis

logger = logging.getLogger(__name__)

CONNECTION_DETECTION_PROMPT = """Analyze the following meeting transcript and identify connections to known context.

<transcript>
{transcript}
</transcript>

<known_people>
{known_people}
</known_people>

<known_projects>
{known_projects}
</known_projects>

<known_topics>
{known_topics}
</known_topics>

<past_meeting_context>
{past_context}
</past_meeting_context>

Return a JSON object with this exact structure:
{{
  "people_referenced": [
    {{
      "name": "Name as it appears in known_people or new name",
      "is_known": true,
      "context": "How they were referenced in this meeting",
      "confidence": 0.0
    }}
  ],
  "projects_referenced": [
    {{
      "name": "Project name",
      "is_known": true,
      "context": "How the project was referenced",
      "confidence": 0.0
    }}
  ],
  "topics_referenced": [
    {{
      "name": "Topic name",
      "is_known": true,
      "context": "How the topic was discussed",
      "confidence": 0.0
    }}
  ],
  "past_meeting_links": [
    {{
      "description": "What connects this meeting to a past discussion",
      "related_context": "Relevant excerpt from past meeting context",
      "confidence": 0.0
    }}
  ],
  "contradictions": [
    {{
      "current_statement": "What was said in this meeting",
      "past_statement": "What was previously recorded",
      "description": "Nature of the contradiction",
      "confidence": 0.0
    }}
  ],
  "open_threads": [
    {{
      "description": "An unresolved thread from past meetings relevant to this one",
      "source": "Where this thread was identified",
      "confidence": 0.0
    }}
  ]
}}

Rules:
- Only flag contradictions if there is a clear conflict, not just different emphasis
- Set confidence 0.0-1.0 based on how certain you are
- is_known should be true if the person/project/topic matches something in the provided known lists
- For open_threads, only include threads that are clearly relevant to this meeting's content
- If past_meeting_context is empty, skip past_meeting_links and contradictions"""

SYSTEM_PROMPT = """You are LIME's connection detection engine. You identify links between the current meeting and the user's existing knowledge base.
Be precise — only flag connections you're confident about. Return valid JSON only."""


def detect_connections(
    meeting_id: str,
    transcript: str,
) -> dict:
    """
    Detect connections between a meeting transcript and existing knowledge.

    Returns a dict with: people_referenced, projects_referenced, topics_referenced,
    past_meeting_links, contradictions, open_threads.
    """
    logger.info(f"Detecting connections for meeting {meeting_id[:8]}...")

    # Gather known entities from the knowledge graph
    known_people = _get_known_people()
    known_projects = _get_known_projects()
    known_topics = _get_known_topics()

    # Search for related past meetings via ChromaDB
    past_context = _get_past_meeting_context(transcript, meeting_id)

    # Build the prompt
    prompt = CONNECTION_DETECTION_PROMPT.format(
        transcript=transcript[:30000],  # Cap transcript length
        known_people=known_people or "None known yet",
        known_projects=known_projects or "None known yet",
        known_topics=known_topics or "None known yet",
        past_context=past_context or "No past meetings found",
    )

    try:
        raw = llm_client.generate(prompt, SYSTEM_PROMPT)
        result = _parse_json(raw)
    except Exception as e:
        logger.error(f"Connection detection LLM call failed: {e}")
        result = _empty_result()

    # Auto-link detected entities to the meeting in the knowledge graph
    _link_entities_to_meeting(meeting_id, result)

    connection_count = (
        len(result.get("people_referenced", []))
        + len(result.get("projects_referenced", []))
        + len(result.get("past_meeting_links", []))
        + len(result.get("contradictions", []))
    )
    logger.info(f"Detected {connection_count} connections for meeting {meeting_id[:8]}")

    return result


def _get_known_people() -> str:
    people = kg.get_entities_by_type("person")
    if not people:
        return ""
    return "\n".join(f"- {p['label']}" for p in people[:50])


def _get_known_projects() -> str:
    projects = kg.get_entities_by_type("project")
    if not projects:
        return ""
    return "\n".join(f"- {p['label']}" for p in projects[:50])


def _get_known_topics() -> str:
    topics = kg.get_entities_by_type("topic")
    if not topics:
        return ""
    return "\n".join(f"- {t['label']}" for t in topics[:50])


def _get_past_meeting_context(transcript: str, exclude_meeting_id: str) -> str:
    """Search ChromaDB for related past meeting content."""
    # Use first ~2000 chars of transcript as query
    query = transcript[:2000]

    related = vector_store.find_related_meetings(
        query=query,
        exclude_meeting_id=exclude_meeting_id,
        n_results=3,
    )

    if not related:
        return ""

    context_parts = []
    for meeting_ref in related:
        mid = meeting_ref["meeting_id"]
        relevance = meeting_ref["relevance"]

        if relevance < 0.3:  # Skip low-relevance matches
            continue

        # Get the summary for this past meeting
        with get_db() as db:
            analysis = (
                db.query(MeetingAnalysis)
                .filter(MeetingAnalysis.meeting_id == mid)
                .first()
            )
            meeting = db.get(Meeting, mid)

            if analysis and meeting:
                title = meeting.title or "Untitled meeting"
                date = meeting.started_at.strftime("%Y-%m-%d") if meeting.started_at else "unknown date"
                context_parts.append(
                    f"[Past Meeting: {title} ({date}), relevance: {relevance}]\n"
                    f"{analysis.executive_summary[:500]}"
                )

    return "\n\n".join(context_parts)


def _link_entities_to_meeting(meeting_id: str, connections: dict):
    """Auto-link detected entities to the meeting in the DB and knowledge graph."""
    try:
        with get_db() as db:
            # Link known people
            for person_ref in connections.get("people_referenced", []):
                if person_ref.get("is_known") and person_ref.get("confidence", 0) >= 0.6:
                    person = find_person_by_name(db, person_ref["name"])
                    if person:
                        link_person_to_meeting(db, person.id, meeting_id, "mentioned")

            # Link known projects
            for project_ref in connections.get("projects_referenced", []):
                if project_ref.get("is_known") and project_ref.get("confidence", 0) >= 0.6:
                    project = find_project_by_name(db, project_ref["name"])
                    if project:
                        link_project_to_meeting(db, project.id, meeting_id)

            # Link known topics
            for topic_ref in connections.get("topics_referenced", []):
                if topic_ref.get("is_known") and topic_ref.get("confidence", 0) >= 0.6:
                    topic = find_topic_by_name(db, topic_ref["name"])
                    if topic:
                        link_topic_to_meeting(db, topic.id, meeting_id)

    except Exception as e:
        logger.warning(f"Failed to auto-link entities: {e}")


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        first_newline = raw.index("\n")
        last_fence = raw.rfind("```")
        if last_fence > first_newline:
            raw = raw[first_newline + 1:last_fence].strip()
    return json.loads(raw)


def _empty_result() -> dict:
    return {
        "people_referenced": [],
        "projects_referenced": [],
        "topics_referenced": [],
        "past_meeting_links": [],
        "contradictions": [],
        "open_threads": [],
    }
