"""
PostMeetingPipeline — orchestrates LLM analysis after a recording stops.

Loads transcript segments, runs LLM calls sequentially, detects connections,
generates insights, stores embeddings in ChromaDB, persists structured results,
and records learning signals to the memory store.
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from backend.config.settings import settings
from backend.storage.database import get_db
from backend.models.meeting import (
    Meeting, MeetingStatus, TranscriptSegment,
    MeetingAnalysis, ActionItem, AnalysisDecision, TopicSegment,
)
from backend.intelligence.llm import llm_client, LLMError
from backend.intelligence.prompts import (
    SYSTEM_PROMPT,
    EXECUTIVE_SUMMARY_PROMPT,
    ACTION_ITEMS_PROMPT,
    DECISIONS_PROMPT,
    TOPIC_SEGMENTATION_PROMPT,
)
from backend.intelligence.connections import detect_connections
from backend.intelligence.insights import generate_insights
from backend.storage.vector_store import vector_store
from backend.learning.memory import memory as mem_store, SignalType

logger = logging.getLogger(__name__)

# Approximate token limit for transcript before chunking (chars, ~4 chars/token)
MAX_TRANSCRIPT_CHARS = 60_000


class PipelineError(Exception):
    pass


def _format_transcript(segments: list) -> str:
    lines = []
    for seg in segments:
        speaker = "Unknown"
        if seg.speaker:
            speaker = seg.speaker.name or seg.speaker.label
        timestamp = f"[{seg.start_time:.1f}s - {seg.end_time:.1f}s]"
        lines.append(f"{timestamp} {speaker}: {seg.text}")
    return "\n".join(lines)


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        first_newline = raw.index("\n")
        last_fence = raw.rfind("```")
        if last_fence > first_newline:
            raw = raw[first_newline + 1:last_fence].strip()
    return json.loads(raw)


def _compute_confidence(
    transcript_segments: list,
    llm_response: dict,
    item_key: Optional[str] = None,
) -> float:
    if not transcript_segments:
        return 0.0

    # Base confidence from transcript quality
    avg_confidence = sum(
        (s.confidence or 0.5) for s in transcript_segments
    ) / len(transcript_segments)

    low_conf_ratio = sum(
        1 for s in transcript_segments if s.is_low_confidence
    ) / len(transcript_segments)

    transcript_quality = avg_confidence * (1.0 - low_conf_ratio * 0.3)

    # LLM response completeness
    response_score = 1.0
    if item_key and item_key in llm_response:
        items = llm_response[item_key]
        if isinstance(items, list) and len(items) == 0:
            response_score = 0.5  # Empty results reduce confidence

    return round(min(1.0, transcript_quality * response_score), 2)


def _chunk_transcript(transcript: str) -> list[str]:
    if len(transcript) <= MAX_TRANSCRIPT_CHARS:
        return [transcript]

    chunks = []
    lines = transcript.split("\n")
    current_chunk: list[str] = []
    current_len = 0

    for line in lines:
        if current_len + len(line) > MAX_TRANSCRIPT_CHARS and current_chunk:
            chunks.append("\n".join(current_chunk))
            # Keep last few lines for context overlap
            overlap = current_chunk[-5:]
            current_chunk = overlap
            current_len = sum(len(l) for l in overlap)
        current_chunk.append(line)
        current_len += len(line)

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


class PostMeetingPipeline:

    def process(self, meeting_id: str) -> Optional[str]:
        """
        Run full post-meeting analysis. Returns the MeetingAnalysis ID on success.
        Sets meeting status to 'processing' at start, 'complete' on success, 'failed' on error.
        """
        start_time = time.time()
        logger.info(f"Pipeline starting for meeting: {meeting_id}")

        # Set status to processing
        with get_db() as db:
            meeting = db.get(Meeting, meeting_id)
            if not meeting:
                raise PipelineError(f"Meeting not found: {meeting_id}")
            meeting.status = MeetingStatus.processing

        try:
            # Load transcript segments
            with get_db() as db:
                segments = (
                    db.query(TranscriptSegment)
                    .filter(TranscriptSegment.meeting_id == meeting_id)
                    .order_by(TranscriptSegment.start_time)
                    .all()
                )
                # Eagerly load speaker relationships
                for seg in segments:
                    _ = seg.speaker

                if not segments:
                    logger.warning(f"No transcript segments for meeting: {meeting_id}")
                    self._set_status(meeting_id, MeetingStatus.complete)
                    return None

                transcript = _format_transcript(segments)
                segment_count = len(segments)

                # Prepare segment data for ChromaDB
                segment_dicts = [
                    {
                        "id": seg.id,
                        "text": seg.text,
                        "start_time": seg.start_time,
                        "end_time": seg.end_time,
                        "speaker": (seg.speaker.name or seg.speaker.label) if seg.speaker else "Unknown",
                    }
                    for seg in segments
                ]

            logger.info(
                f"Loaded {segment_count} segments, "
                f"{len(transcript)} chars of transcript"
            )

            # Handle long transcripts by chunking
            chunks = _chunk_transcript(transcript)
            if len(chunks) > 1:
                logger.info(f"Transcript split into {len(chunks)} chunks")

            # Use last chunk for summary (most likely to have conclusions)
            # Use full transcript for extraction tasks
            summary_transcript = chunks[-1] if len(chunks) > 1 else transcript

            # Phase 1: Core analysis (LLM calls)
            summary_data = self._run_summary(summary_transcript)
            actions_data = self._run_action_items(transcript)
            decisions_data = self._run_decisions(transcript)
            topics_data = self._run_topics(transcript)

            # Phase 2: Store embeddings in ChromaDB
            self._store_embeddings(meeting_id, segment_dicts, summary_data, topics_data)

            # Phase 3: Connection detection (uses ChromaDB + knowledge graph)
            connections_data = self._run_connections(meeting_id, transcript)

            # Phase 4: Insight generation (uses connections + knowledge graph)
            insights_data = self._run_insights(
                meeting_id, transcript,
                summary_data.get("summary", ""),
                connections_data,
            )

            # Compute overall confidence
            with get_db() as db:
                segments_for_conf = (
                    db.query(TranscriptSegment)
                    .filter(TranscriptSegment.meeting_id == meeting_id)
                    .all()
                )
                overall_confidence = _compute_confidence(
                    segments_for_conf, summary_data
                )

            processing_duration = time.time() - start_time

            # Persist results
            analysis_id = self._persist_results(
                meeting_id=meeting_id,
                summary_data=summary_data,
                actions_data=actions_data,
                decisions_data=decisions_data,
                topics_data=topics_data,
                connections_data=connections_data,
                insights_data=insights_data,
                overall_confidence=overall_confidence,
                processing_duration=processing_duration,
            )

            # Record learning signals
            self._record_learning_signals(
                meeting_id, actions_data, decisions_data, topics_data
            )

            # Set status to complete
            self._set_status(meeting_id, MeetingStatus.complete)

            logger.info(
                f"Pipeline complete for meeting {meeting_id} "
                f"({processing_duration:.1f}s, confidence: {overall_confidence:.0%})"
            )
            return analysis_id

        except Exception as e:
            logger.error(f"Pipeline failed for meeting {meeting_id}: {e}")
            self._set_status(meeting_id, MeetingStatus.failed)
            raise

    def _run_summary(self, transcript: str) -> dict:
        prompt = EXECUTIVE_SUMMARY_PROMPT.format(transcript=transcript)
        raw = llm_client.generate(prompt, SYSTEM_PROMPT)
        try:
            return _parse_json(raw)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse summary response: {e}")
            return {"summary": raw, "meeting_type": "general", "sentiment": "neutral"}

    def _run_action_items(self, transcript: str) -> dict:
        prompt = ACTION_ITEMS_PROMPT.format(transcript=transcript)
        raw = llm_client.generate(prompt, SYSTEM_PROMPT)
        try:
            return _parse_json(raw)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse action items response: {e}")
            return {"action_items": []}

    def _run_decisions(self, transcript: str) -> dict:
        prompt = DECISIONS_PROMPT.format(transcript=transcript)
        raw = llm_client.generate(prompt, SYSTEM_PROMPT)
        try:
            return _parse_json(raw)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse decisions response: {e}")
            return {"decisions": []}

    def _run_topics(self, transcript: str) -> dict:
        prompt = TOPIC_SEGMENTATION_PROMPT.format(transcript=transcript)
        raw = llm_client.generate(prompt, SYSTEM_PROMPT)
        try:
            return _parse_json(raw)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse topics response: {e}")
            return {"topics": []}

    def _run_connections(self, meeting_id: str, transcript: str) -> dict:
        try:
            return detect_connections(meeting_id, transcript)
        except Exception as e:
            logger.error(f"Connection detection failed: {e}")
            return {
                "people_referenced": [],
                "projects_referenced": [],
                "topics_referenced": [],
                "past_meeting_links": [],
                "contradictions": [],
                "open_threads": [],
            }

    def _run_insights(
        self,
        meeting_id: str,
        transcript: str,
        summary: str,
        connections: dict,
    ) -> list[dict]:
        try:
            return generate_insights(meeting_id, transcript, summary, connections)
        except Exception as e:
            logger.error(f"Insight generation failed: {e}")
            return []

    def _store_embeddings(
        self,
        meeting_id: str,
        segment_dicts: list[dict],
        summary_data: dict,
        topics_data: dict,
    ):
        """Store transcript segments and summaries in ChromaDB."""
        try:
            # Store transcript segments
            vector_store.add_segments(meeting_id, segment_dicts)

            # Store executive summary
            summary_text = summary_data.get("summary", "")
            if summary_text:
                vector_store.add_summary(
                    meeting_id, "executive", summary_text,
                    metadata={
                        "meeting_type": summary_data.get("meeting_type", "general"),
                    },
                )

            # Store topic summaries
            for i, topic in enumerate(topics_data.get("topics", [])):
                topic_text = f"{topic.get('title', '')}: {topic.get('summary', '')}"
                if topic_text.strip(": "):
                    vector_store.add_summary(
                        meeting_id, f"topic_{i}", topic_text,
                        metadata={"topic_title": topic.get("title", "")},
                    )

            logger.info(f"Embeddings stored for meeting {meeting_id[:8]}")
        except Exception as e:
            logger.warning(f"Failed to store embeddings: {e}")

    def _persist_results(
        self,
        meeting_id: str,
        summary_data: dict,
        actions_data: dict,
        decisions_data: dict,
        topics_data: dict,
        connections_data: dict,
        insights_data: list[dict],
        overall_confidence: float,
        processing_duration: float,
    ) -> str:
        with get_db() as db:
            # Delete any existing analysis for this meeting
            existing = (
                db.query(MeetingAnalysis)
                .filter(MeetingAnalysis.meeting_id == meeting_id)
                .first()
            )
            if existing:
                db.delete(existing)
                db.flush()

            analysis = MeetingAnalysis(
                meeting_id=meeting_id,
                executive_summary=summary_data.get("summary", ""),
                meeting_type=summary_data.get("meeting_type", "general"),
                sentiment=summary_data.get("sentiment", "neutral"),
                overall_confidence=overall_confidence,
                llm_provider=llm_client.active_provider,
                processed_at=datetime.now(timezone.utc),
                processing_duration_seconds=processing_duration,
                connections_data=json.dumps(connections_data),
                insights_data=json.dumps(insights_data),
            )
            db.add(analysis)
            db.flush()
            analysis_id = analysis.id

            # Action items
            for item in actions_data.get("action_items", []):
                db.add(ActionItem(
                    analysis_id=analysis_id,
                    description=item.get("description", ""),
                    owner=item.get("owner"),
                    deadline=item.get("deadline"),
                    priority=item.get("priority", "medium"),
                    confidence=item.get("confidence", 0.5),
                    source_quote=item.get("source_quote", ""),
                    source_start_time=item.get("source_start_time"),
                    source_end_time=item.get("source_end_time"),
                ))

            # Decisions
            for dec in decisions_data.get("decisions", []):
                participants = dec.get("participants", [])
                db.add(AnalysisDecision(
                    analysis_id=analysis_id,
                    description=dec.get("description", ""),
                    context=dec.get("context", ""),
                    participants=json.dumps(participants) if participants else None,
                    confidence=dec.get("confidence", 0.5),
                    source_quote=dec.get("source_quote", ""),
                    source_start_time=dec.get("source_start_time"),
                    source_end_time=dec.get("source_end_time"),
                ))

            # Topics
            for i, topic in enumerate(topics_data.get("topics", [])):
                related = topic.get("related_topic_indices", [])
                db.add(TopicSegment(
                    analysis_id=analysis_id,
                    title=topic.get("title", ""),
                    summary=topic.get("summary", ""),
                    start_time=topic.get("start_time", 0.0),
                    end_time=topic.get("end_time", 0.0),
                    order_index=i,
                    confidence=topic.get("confidence", 0.5),
                    related_segment_ids=json.dumps(related) if related else None,
                ))

            return analysis_id

    def _record_learning_signals(
        self,
        meeting_id: str,
        actions_data: dict,
        decisions_data: dict,
        topics_data: dict,
    ):
        try:
            # Extract person names from action items and decisions
            people = set()
            for item in actions_data.get("action_items", []):
                if item.get("owner"):
                    people.add(item["owner"])
            for dec in decisions_data.get("decisions", []):
                for p in dec.get("participants", []):
                    people.add(p)

            for person in people:
                mem_store.record_person(
                    name=person,
                    context="Mentioned in meeting analysis",
                    meeting_id=meeting_id,
                )

            # Record topic vocabulary
            for topic in topics_data.get("topics", []):
                title = topic.get("title", "")
                if title:
                    mem_store.record_vocabulary(
                        term=title,
                        context="Meeting topic",
                        meeting_id=meeting_id,
                    )

        except Exception as e:
            # Learning signals are non-critical — don't fail the pipeline
            logger.warning(f"Failed to record learning signals: {e}")

    def _set_status(self, meeting_id: str, status: MeetingStatus):
        with get_db() as db:
            meeting = db.get(Meeting, meeting_id)
            if meeting:
                meeting.status = status


# Module-level singleton
pipeline = PostMeetingPipeline()
