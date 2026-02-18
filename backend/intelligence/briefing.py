"""
Pre-meeting briefing system.

User provides context (who they're meeting, what it's about), and the agent
searches the knowledge base for relevant history:
  - Past meetings with the same people
  - Related projects and their current state
  - Open action items involving those people/projects
  - Unresolved threads from past meetings
  - Relevant decisions and their outcomes

Generates a structured briefing document.
"""

import json
import logging
from typing import Optional

from backend.config.settings import settings
from backend.intelligence.llm import llm_client
from backend.storage.vector_store import vector_store
from backend.storage.database import get_db
from backend.models.meeting import (
    Meeting, MeetingAnalysis, ActionItem, MeetingStatus,
)
from backend.models.knowledge import Person, Project, Topic, PersonMeeting, ProjectMeeting
from backend.knowledge.graph import knowledge_graph as kg
from backend.knowledge.entities import find_person_by_name, find_project_by_name

logger = logging.getLogger(__name__)

BRIEFING_PROMPT = """You are LIME's pre-meeting briefing engine. Prepare a concise, actionable briefing for the user.

<meeting_context>
Participants: {participants}
Topic/Purpose: {purpose}
</meeting_context>

<past_meetings_with_these_people>
{past_meetings}
</past_meetings_with_these_people>

<open_action_items>
{open_actions}
</open_action_items>

<related_project_info>
{project_info}
</related_project_info>

<relevant_decisions>
{decisions}
</relevant_decisions>

<semantically_related_content>
{related_content}
</semantically_related_content>

Generate a pre-meeting briefing. Return a JSON object with this exact structure:
{{
  "briefing_summary": "2-3 sentence overview of what the user should know going in",
  "key_context": [
    {{
      "title": "Brief title",
      "detail": "Important context the user might have forgotten",
      "source": "Where this information came from (past meeting date, etc.)",
      "priority": "high|medium|low"
    }}
  ],
  "open_threads": [
    {{
      "description": "An unresolved thread or follow-up relevant to this meeting",
      "from_meeting": "When/where this thread originated",
      "suggested_action": "What the user might want to bring up or follow up on"
    }}
  ],
  "action_items_to_follow_up": [
    {{
      "description": "Action item that should be checked on",
      "owner": "Who owns it",
      "from_meeting": "When it was assigned"
    }}
  ],
  "suggested_questions": [
    "Questions the user might want to ask during this meeting"
  ],
  "confidence": 0.0
}}

Rules:
- Focus on actionable intelligence, not generic advice
- Priority should reflect how important it is for the user to know before the meeting
- Only include items with clear relevance to this meeting's participants and purpose
- If there's very little context available, say so honestly and keep the briefing short
- Set confidence based on how much relevant context was available (low if sparse, high if rich)"""

SYSTEM_PROMPT = """You are LIME's pre-meeting briefing engine. You help the user walk into meetings prepared by surfacing relevant history, open threads, and things they might have forgotten.
Be concise and actionable. Return valid JSON only."""


def generate_briefing(
    participants: list[str],
    purpose: str = "",
    meeting_id: Optional[str] = None,
) -> dict:
    """
    Generate a pre-meeting briefing based on participants and purpose.

    Returns a structured briefing dict.
    """
    logger.info(
        f"Generating briefing for meeting with: {', '.join(participants)}, "
        f"purpose: {purpose[:60]}"
    )

    # Gather context
    past_meetings = _get_past_meetings_with_people(participants)
    open_actions = _get_open_action_items(participants)
    project_info = _get_related_projects(participants, purpose)
    decisions = _get_relevant_decisions(participants, purpose)
    related_content = _get_semantically_related(participants, purpose)

    prompt = BRIEFING_PROMPT.format(
        participants=", ".join(participants),
        purpose=purpose or "Not specified",
        past_meetings=past_meetings or "No past meetings with these participants found",
        open_actions=open_actions or "No open action items found",
        project_info=project_info or "No related projects found",
        decisions=decisions or "No relevant decisions found",
        related_content=related_content or "No related content found",
    )

    try:
        raw = llm_client.generate(prompt, SYSTEM_PROMPT)
        result = _parse_json(raw)
    except Exception as e:
        logger.error(f"Briefing generation failed: {e}")
        result = {
            "briefing_summary": "Could not generate briefing due to a processing error.",
            "key_context": [],
            "open_threads": [],
            "action_items_to_follow_up": [],
            "suggested_questions": [],
            "confidence": 0.0,
        }

    logger.info(
        f"Briefing generated: {len(result.get('key_context', []))} context items, "
        f"{len(result.get('open_threads', []))} open threads"
    )
    return result


def _get_past_meetings_with_people(participants: list[str]) -> str:
    """Find past meetings involving any of the named participants."""
    parts = []

    with get_db() as db:
        for name in participants:
            person = find_person_by_name(db, name)
            if not person:
                continue

            # Get meetings where this person was mentioned
            mentions = (
                db.query(PersonMeeting)
                .filter(PersonMeeting.person_id == person.id)
                .order_by(PersonMeeting.created_at.desc())
                .limit(5)
                .all()
            )

            for mention in mentions:
                meeting = db.get(Meeting, mention.meeting_id)
                if not meeting:
                    continue
                analysis = (
                    db.query(MeetingAnalysis)
                    .filter(MeetingAnalysis.meeting_id == meeting.id)
                    .first()
                )
                if analysis:
                    title = meeting.title or "Untitled"
                    date = meeting.started_at.strftime("%Y-%m-%d") if meeting.started_at else "unknown"
                    parts.append(
                        f"[{title} - {date}] (with {name})\n"
                        f"{analysis.executive_summary[:400]}"
                    )

    return "\n\n".join(parts[:10])


def _get_open_action_items(participants: list[str]) -> str:
    """Find action items owned by or related to the participants."""
    items = []

    with get_db() as db:
        for name in participants:
            actions = (
                db.query(ActionItem)
                .filter(ActionItem.owner.ilike(f"%{name}%"))
                .order_by(ActionItem.id.desc())
                .limit(10)
                .all()
            )
            for a in actions:
                items.append(
                    f"- [{a.priority}] {a.description} (owner: {a.owner}, "
                    f"deadline: {a.deadline or 'none'})"
                )

    return "\n".join(items[:15])


def _get_related_projects(participants: list[str], purpose: str) -> str:
    """Find projects associated with the participants or purpose."""
    parts = []

    with get_db() as db:
        for name in participants:
            person = find_person_by_name(db, name)
            if not person:
                continue

            # Check knowledge graph for project connections
            neighbors = kg.get_neighbors(person.id)
            for neighbor in neighbors:
                if neighbor.get("entity_type") == "project":
                    project = db.get(Project, neighbor["id"])
                    if project:
                        parts.append(
                            f"- {project.name} ({project.status.value if project.status else 'active'}): "
                            f"{project.description or 'No description'}"
                        )

        # Also search by purpose text
        if purpose:
            project = find_project_by_name(db, purpose)
            if project:
                parts.append(
                    f"- {project.name} ({project.status.value if project.status else 'active'}): "
                    f"{project.description or 'No description'}"
                )

    return "\n".join(set(parts[:10]))


def _get_relevant_decisions(participants: list[str], purpose: str) -> str:
    """Find decisions involving participants or related to the purpose."""
    parts = []

    with get_db() as db:
        from backend.models.knowledge import Decision as KGDecision
        for name in participants:
            person = find_person_by_name(db, name)
            if not person:
                continue

            decisions = (
                db.query(KGDecision)
                .filter(KGDecision.owner_id == person.id)
                .order_by(KGDecision.made_at.desc())
                .limit(5)
                .all()
            )
            for d in decisions:
                status = d.status.value if d.status else "proposed"
                parts.append(
                    f"- [{status}] {d.summary} (context: {d.context or 'none'})"
                )

    return "\n".join(parts[:10])


def _get_semantically_related(participants: list[str], purpose: str) -> str:
    """Use ChromaDB to find semantically related past content."""
    query = f"Meeting with {', '.join(participants)}. {purpose}"

    results = vector_store.search_summaries(query=query, n_results=5)

    if not results:
        return ""

    parts = []
    for r in results:
        if r.get("relevance", 0) < 0.3:
            continue
        parts.append(
            f"[Relevance: {r['relevance']}] {r.get('text', '')[:300]}"
        )

    return "\n\n".join(parts[:5])


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        first_newline = raw.index("\n")
        last_fence = raw.rfind("```")
        if last_fence > first_newline:
            raw = raw[first_newline + 1:last_fence].strip()
    return json.loads(raw)
