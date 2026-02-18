"""
Insight generation — surfaces things the user might not have thought of.

Generates:
  - Implications of decisions discussed
  - Dependencies or conflicts with known information
  - Patterns across recent meetings
  - Questions the user should be asking
  - Risks or opportunities not explicitly mentioned
"""

import json
import logging
from typing import Optional

from backend.intelligence.llm import llm_client
from backend.storage.vector_store import vector_store
from backend.storage.database import get_db
from backend.models.meeting import MeetingAnalysis, Meeting
from backend.knowledge.graph import knowledge_graph as kg

logger = logging.getLogger(__name__)

INSIGHT_GENERATION_PROMPT = """You are an insight engine for a cognitive meeting companion. Your job is to surface things the user might not have thought of during or after this meeting.

<transcript>
{transcript}
</transcript>

<meeting_summary>
{summary}
</meeting_summary>

<connections_detected>
{connections}
</connections_detected>

<recent_meeting_context>
{recent_context}
</recent_meeting_context>

<knowledge_graph_context>
{kg_context}
</knowledge_graph_context>

Generate insights that go beyond what was explicitly discussed. Think about:
1. Implications of decisions made or discussed
2. Dependencies that might not be obvious
3. Risks or opportunities not mentioned
4. Patterns you see across this and recent meetings
5. Questions the user should consider asking next
6. Things that were conspicuously NOT discussed but probably should have been

Return a JSON object with this exact structure:
{{
  "insights": [
    {{
      "type": "implication|dependency|risk|opportunity|pattern|question|gap",
      "title": "Brief title for the insight",
      "description": "Detailed explanation of the insight",
      "reasoning": "Why this insight matters or how you arrived at it",
      "related_to": "What part of the meeting or knowledge base this relates to",
      "priority": "high|medium|low",
      "confidence": 0.0
    }}
  ]
}}

Rules:
- Generate 3-8 insights, prioritizing quality over quantity
- Each insight should be genuinely useful, not obvious
- Set confidence 0.0-1.0 based on how grounded the insight is in the evidence
- Higher confidence for insights directly supported by transcript + context
- Lower confidence for speculative but potentially valuable insights
- Priority should reflect how actionable or important the insight is
- Don't repeat what's already in the summary or connections"""

SYSTEM_PROMPT = """You are LIME's insight engine — a cognitive companion that helps users see what they might have missed.
You surface non-obvious connections, implications, and patterns. Be genuinely insightful, not generic.
Return valid JSON only."""


def generate_insights(
    meeting_id: str,
    transcript: str,
    summary: str = "",
    connections: Optional[dict] = None,
) -> list[dict]:
    """
    Generate insights for a meeting based on transcript, summary, and existing knowledge.

    Returns a list of insight dicts with: type, title, description, reasoning,
    related_to, priority, confidence.
    """
    logger.info(f"Generating insights for meeting {meeting_id[:8]}...")

    # Get recent meeting context for pattern detection
    recent_context = _get_recent_meeting_context(meeting_id)

    # Get knowledge graph context
    kg_context = _get_knowledge_graph_context()

    # Format connections for the prompt
    connections_text = _format_connections(connections) if connections else "None detected"

    prompt = INSIGHT_GENERATION_PROMPT.format(
        transcript=transcript[:20000],  # Cap to avoid token limits
        summary=summary[:2000],
        connections=connections_text[:3000],
        recent_context=recent_context[:3000],
        kg_context=kg_context[:2000],
    )

    try:
        raw = llm_client.generate(prompt, SYSTEM_PROMPT)
        result = _parse_json(raw)
        insights = result.get("insights", [])
    except Exception as e:
        logger.error(f"Insight generation failed: {e}")
        insights = []

    logger.info(f"Generated {len(insights)} insights for meeting {meeting_id[:8]}")
    return insights


def _get_recent_meeting_context(exclude_meeting_id: str, limit: int = 5) -> str:
    """Get summaries of recent meetings for pattern detection."""
    with get_db() as db:
        recent = (
            db.query(Meeting)
            .filter(
                Meeting.id != exclude_meeting_id,
                Meeting.status == "complete",
            )
            .order_by(Meeting.started_at.desc())
            .limit(limit)
            .all()
        )

        if not recent:
            return "No previous meetings recorded yet."

        parts = []
        for m in recent:
            analysis = (
                db.query(MeetingAnalysis)
                .filter(MeetingAnalysis.meeting_id == m.id)
                .first()
            )
            if analysis:
                title = m.title or "Untitled"
                date = m.started_at.strftime("%Y-%m-%d") if m.started_at else "unknown"
                parts.append(
                    f"[{title} - {date}]: {analysis.executive_summary[:300]}"
                )

        return "\n\n".join(parts) if parts else "No analyzed meetings found."


def _get_knowledge_graph_context() -> str:
    """Summarize the knowledge graph for the LLM."""
    stats = kg.stats()
    if stats["total_nodes"] == 0:
        return "Knowledge graph is empty — this is an early meeting."

    parts = [f"Knowledge graph: {stats['total_nodes']} entities, {stats['total_edges']} relationships"]

    people = kg.get_entities_by_type("person")
    if people:
        parts.append(f"Known people: {', '.join(p['label'] for p in people[:20])}")

    projects = kg.get_entities_by_type("project")
    if projects:
        parts.append(f"Known projects: {', '.join(p['label'] for p in projects[:20])}")

    topics = kg.get_entities_by_type("topic")
    if topics:
        parts.append(f"Known topics: {', '.join(t['label'] for t in topics[:20])}")

    return "\n".join(parts)


def _format_connections(connections: dict) -> str:
    """Format connection detection results for the insight prompt."""
    parts = []

    people = connections.get("people_referenced", [])
    if people:
        parts.append("People referenced: " + ", ".join(
            f"{p['name']} ({p.get('context', '')})" for p in people
        ))

    projects = connections.get("projects_referenced", [])
    if projects:
        parts.append("Projects referenced: " + ", ".join(
            f"{p['name']} ({p.get('context', '')})" for p in projects
        ))

    links = connections.get("past_meeting_links", [])
    if links:
        parts.append("Past meeting links:")
        for link in links:
            parts.append(f"  - {link.get('description', '')}")

    contradictions = connections.get("contradictions", [])
    if contradictions:
        parts.append("Contradictions detected:")
        for c in contradictions:
            parts.append(f"  - {c.get('description', '')}")

    return "\n".join(parts) if parts else "None"


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        first_newline = raw.index("\n")
        last_fence = raw.rfind("```")
        if last_fence > first_newline:
            raw = raw[first_newline + 1:last_fence].strip()
    return json.loads(raw)
