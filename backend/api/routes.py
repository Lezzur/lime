"""
FastAPI REST routes for LIME Phase 2.
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional
from pathlib import Path
from datetime import datetime, timezone
import json
import logging
import threading
import uuid
import shutil

from backend.config.settings import settings
from backend.storage.database import get_db_session
from backend.models.meeting import (
    Meeting, MeetingStatus, TranscriptSegment, Speaker,
    MeetingAnalysis, ActionItem, AnalysisDecision, TopicSegment,
    UserCorrection,
    AudioSource as ModelAudioSource,
)
from backend.audio.capture import AudioSource, list_audio_devices

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# Active sessions (meeting_id → MeetingSession)
_active_sessions: dict = {}

# Register active meetings as a busy signal for the consolidation scheduler
try:
    from backend.learning.scheduler import register_activity_indicator
    register_activity_indicator(lambda: len(_active_sessions) > 0)
except Exception:
    logger.warning("Could not register activity indicator with consolidation scheduler")


# ── Request / Response Models ─────────────────────────────────────────────────

class StartMeetingRequest(BaseModel):
    source: str = "microphone"    # "microphone" | "system"
    device_index: Optional[int] = None
    title: Optional[str] = None


class StartMeetingResponse(BaseModel):
    meeting_id: str
    status: str
    source: str


class StopMeetingResponse(BaseModel):
    meeting_id: str
    duration_seconds: float
    status: str


class MeetingSummary(BaseModel):
    id: str
    title: Optional[str]
    status: str
    audio_source: str
    started_at: str
    ended_at: Optional[str]
    duration_seconds: Optional[float]
    segment_count: int


class TranscriptSegmentOut(BaseModel):
    id: str
    start_time: float
    end_time: float
    text: str
    language: Optional[str]
    confidence: Optional[float]
    is_low_confidence: bool
    speaker: Optional[str]
    transcription_source: str


# ── Meeting Endpoints ─────────────────────────────────────────────────────────

@router.post("/meetings/start", response_model=StartMeetingResponse)
def start_meeting(req: StartMeetingRequest, db: Session = Depends(get_db_session)):
    from backend.audio.session import MeetingSession

    if req.source not in ("microphone", "system"):
        raise HTTPException(400, "source must be 'microphone' or 'system'")

    source = AudioSource.system if req.source == "system" else AudioSource.microphone
    session = MeetingSession(source=source, device_index=req.device_index)
    meeting_id = session.start()

    if req.title:
        meeting = db.get(Meeting, meeting_id)
        if meeting:
            meeting.title = req.title
            db.commit()

    _active_sessions[meeting_id] = session
    return StartMeetingResponse(meeting_id=meeting_id, status="recording", source=req.source)


@router.post("/meetings/{meeting_id}/stop", response_model=StopMeetingResponse)
def stop_meeting(meeting_id: str):
    session = _active_sessions.pop(meeting_id, None)
    if not session:
        raise HTTPException(404, f"No active recording for meeting_id: {meeting_id}")

    result = session.stop()
    return StopMeetingResponse(
        meeting_id=meeting_id,
        duration_seconds=result["duration_seconds"],
        status="processing",
    )


@router.get("/meetings/{meeting_id}/transcript", response_model=list[TranscriptSegmentOut])
def get_transcript(meeting_id: str, db: Session = Depends(get_db_session)):
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(404, "Meeting not found")

    segments = (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.meeting_id == meeting_id)
        .order_by(TranscriptSegment.start_time)
        .all()
    )

    results = []
    for seg in segments:
        speaker_name = None
        if seg.speaker:
            speaker_name = seg.speaker.name or seg.speaker.label
        results.append(TranscriptSegmentOut(
            id=seg.id,
            start_time=seg.start_time,
            end_time=seg.end_time,
            text=seg.text,
            language=seg.language,
            confidence=seg.confidence,
            is_low_confidence=seg.is_low_confidence,
            speaker=speaker_name,
            transcription_source=seg.transcription_source,
        ))
    return results


@router.get("/meetings", response_model=list[MeetingSummary])
def list_meetings(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db_session),
):
    meetings = (
        db.query(Meeting)
        .order_by(Meeting.started_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    results = []
    for m in meetings:
        results.append(MeetingSummary(
            id=m.id,
            title=m.title,
            status=m.status.value,
            audio_source=m.audio_source.value,
            started_at=m.started_at.isoformat(),
            ended_at=m.ended_at.isoformat() if m.ended_at else None,
            duration_seconds=m.duration_seconds,
            segment_count=len(m.segments),
        ))
    return results


@router.get("/meetings/{meeting_id}", response_model=MeetingSummary)
def get_meeting(meeting_id: str, db: Session = Depends(get_db_session)):
    """Get a single meeting by ID."""
    m = db.get(Meeting, meeting_id)
    if not m:
        raise HTTPException(404, "Meeting not found")
    return MeetingSummary(
        id=m.id,
        title=m.title,
        status=m.status.value,
        audio_source=m.audio_source.value,
        started_at=m.started_at.isoformat(),
        ended_at=m.ended_at.isoformat() if m.ended_at else None,
        duration_seconds=m.duration_seconds,
        segment_count=len(m.segments),
    )


@router.get("/devices")
def get_audio_devices():
    """List all available audio input devices."""
    return list_audio_devices()


@router.get("/meetings/active")
def get_active_meetings():
    """List all currently recording sessions."""
    return [
        {"meeting_id": mid, "elapsed_seconds": session._capture.elapsed_seconds}
        for mid, session in _active_sessions.items()
    ]


# ── Intelligence / Notes Endpoints ─────────────────────────────────────────────

class ActionItemOut(BaseModel):
    id: str
    description: str
    owner: Optional[str]
    deadline: Optional[str]
    priority: str
    confidence: float
    below_threshold: bool = False
    source_quote: Optional[str]
    source_start_time: Optional[float]
    source_end_time: Optional[float]


class DecisionOut(BaseModel):
    id: str
    description: str
    context: Optional[str]
    participants: Optional[list[str]]
    confidence: float
    below_threshold: bool = False
    source_quote: Optional[str]
    source_start_time: Optional[float]
    source_end_time: Optional[float]


class TopicSegmentOut(BaseModel):
    id: str
    title: str
    summary: Optional[str]
    start_time: float
    end_time: float
    order_index: int
    confidence: float
    below_threshold: bool = False
    related_segment_ids: Optional[list[int]]


class InsightOut(BaseModel):
    type: str
    title: str
    description: str
    reasoning: Optional[str]
    related_to: Optional[str]
    priority: str
    confidence: float
    below_threshold: bool = False


class ConnectionsOut(BaseModel):
    people_referenced: list[dict]
    projects_referenced: list[dict]
    topics_referenced: list[dict]
    past_meeting_links: list[dict]
    contradictions: list[dict]
    open_threads: list[dict]


class MeetingNotesOut(BaseModel):
    analysis_id: str
    meeting_id: str
    executive_summary: str
    meeting_type: Optional[str]
    sentiment: Optional[str]
    overall_confidence: float
    confidence_threshold: float
    llm_provider: Optional[str]
    processed_at: str
    processing_duration_seconds: Optional[float]
    action_items: list[ActionItemOut]
    decisions: list[DecisionOut]
    topics: list[TopicSegmentOut]
    connections: Optional[ConnectionsOut]
    insights: list[InsightOut]


class NotesEditRequest(BaseModel):
    executive_summary: Optional[str] = None
    action_items: Optional[list[dict]] = None
    decisions: Optional[list[dict]] = None


@router.post("/meetings/{meeting_id}/analyze")
def analyze_meeting(meeting_id: str, db: Session = Depends(get_db_session)):
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(404, "Meeting not found")
    if meeting.status == MeetingStatus.processing:
        raise HTTPException(409, "Meeting is already being processed")

    from backend.intelligence.pipeline import pipeline

    def _run():
        try:
            pipeline.process(meeting_id)
        except Exception as e:
            logger.error(f"Background analysis failed for {meeting_id}: {e}")

    thread = threading.Thread(target=_run, daemon=True, name=f"analyze-{meeting_id[:8]}")
    thread.start()

    return {"meeting_id": meeting_id, "status": "processing"}


@router.get("/meetings/{meeting_id}/notes", response_model=MeetingNotesOut)
def get_meeting_notes(meeting_id: str, db: Session = Depends(get_db_session)):
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(404, "Meeting not found")

    analysis = (
        db.query(MeetingAnalysis)
        .filter(MeetingAnalysis.meeting_id == meeting_id)
        .first()
    )
    if not analysis:
        raise HTTPException(404, "No analysis found for this meeting. Trigger analysis first via POST /analyze.")

    threshold = settings.confidence_badge_threshold

    action_items = [
        ActionItemOut(
            id=a.id,
            description=a.description,
            owner=a.owner,
            deadline=a.deadline,
            priority=a.priority,
            confidence=a.confidence,
            below_threshold=a.confidence < threshold,
            source_quote=a.source_quote,
            source_start_time=a.source_start_time,
            source_end_time=a.source_end_time,
        )
        for a in analysis.action_items
    ]

    decisions = []
    for d in analysis.decisions:
        participants = None
        if d.participants:
            try:
                participants = json.loads(d.participants)
            except (json.JSONDecodeError, TypeError):
                participants = [d.participants]
        decisions.append(DecisionOut(
            id=d.id,
            description=d.description,
            context=d.context,
            participants=participants,
            confidence=d.confidence,
            below_threshold=d.confidence < threshold,
            source_quote=d.source_quote,
            source_start_time=d.source_start_time,
            source_end_time=d.source_end_time,
        ))

    topics = []
    for t in sorted(analysis.topics, key=lambda x: x.order_index):
        related = None
        if t.related_segment_ids:
            try:
                related = json.loads(t.related_segment_ids)
            except (json.JSONDecodeError, TypeError):
                related = None
        topics.append(TopicSegmentOut(
            id=t.id,
            title=t.title,
            summary=t.summary,
            start_time=t.start_time,
            end_time=t.end_time,
            order_index=t.order_index,
            confidence=t.confidence,
            below_threshold=t.confidence < threshold,
            related_segment_ids=related,
        ))

    # Parse connections
    connections = None
    if analysis.connections_data:
        try:
            conn_data = json.loads(analysis.connections_data)
            connections = ConnectionsOut(**conn_data)
        except (json.JSONDecodeError, TypeError, ValueError):
            connections = None

    # Parse insights
    insights = []
    if analysis.insights_data:
        try:
            insights_raw = json.loads(analysis.insights_data)
            for ins in insights_raw:
                insights.append(InsightOut(
                    type=ins.get("type", "general"),
                    title=ins.get("title", ""),
                    description=ins.get("description", ""),
                    reasoning=ins.get("reasoning"),
                    related_to=ins.get("related_to"),
                    priority=ins.get("priority", "medium"),
                    confidence=ins.get("confidence", 0.5),
                    below_threshold=ins.get("confidence", 0.5) < threshold,
                ))
        except (json.JSONDecodeError, TypeError):
            insights = []

    return MeetingNotesOut(
        analysis_id=analysis.id,
        meeting_id=meeting_id,
        executive_summary=analysis.executive_summary,
        meeting_type=analysis.meeting_type,
        sentiment=analysis.sentiment,
        overall_confidence=analysis.overall_confidence,
        confidence_threshold=threshold,
        llm_provider=analysis.llm_provider,
        processed_at=analysis.processed_at.isoformat(),
        processing_duration_seconds=analysis.processing_duration_seconds,
        action_items=action_items,
        decisions=decisions,
        topics=topics,
        connections=connections,
        insights=insights,
    )


@router.patch("/meetings/{meeting_id}/notes")
def edit_meeting_notes(
    meeting_id: str,
    req: NotesEditRequest,
    db: Session = Depends(get_db_session),
):
    analysis = (
        db.query(MeetingAnalysis)
        .filter(MeetingAnalysis.meeting_id == meeting_id)
        .first()
    )
    if not analysis:
        raise HTTPException(404, "No analysis found for this meeting")

    from backend.learning.memory import memory as mem_store

    # Track specific field changes
    if req.executive_summary is not None:
        old_value = analysis.executive_summary
        analysis.executive_summary = req.executive_summary
        # Record granular correction
        db.add(UserCorrection(
            analysis_id=analysis.id,
            meeting_id=meeting_id,
            correction_type="summary",
            field_name="executive_summary",
            original_value=old_value[:500] if old_value else None,
            corrected_value=req.executive_summary[:500],
        ))
        mem_store.record_content_edit(
            f"User edited executive summary",
            meeting_id=meeting_id,
        )

    if req.action_items is not None:
        for item_edit in req.action_items:
            item_id = item_edit.get("id")
            if not item_id:
                continue
            action = db.get(ActionItem, item_id)
            if not action or action.analysis_id != analysis.id:
                continue
            for field in ("description", "owner", "deadline", "priority"):
                if field in item_edit and item_edit[field] is not None:
                    old_val = getattr(action, field)
                    setattr(action, field, item_edit[field])
                    db.add(UserCorrection(
                        analysis_id=analysis.id,
                        meeting_id=meeting_id,
                        correction_type="action_item",
                        target_id=item_id,
                        field_name=field,
                        original_value=str(old_val) if old_val else None,
                        corrected_value=str(item_edit[field]),
                    ))
            if item_edit.get("delete"):
                db.add(UserCorrection(
                    analysis_id=analysis.id,
                    meeting_id=meeting_id,
                    correction_type="action_item",
                    target_id=item_id,
                    field_name="_deleted",
                    original_value=action.description,
                ))
                db.delete(action)
                mem_store.record_content_deletion(
                    f"Action item: {action.description[:60]}",
                    meeting_id=meeting_id,
                )

    if req.decisions is not None:
        for dec_edit in req.decisions:
            dec_id = dec_edit.get("id")
            if not dec_id:
                continue
            decision = db.get(AnalysisDecision, dec_id)
            if not decision or decision.analysis_id != analysis.id:
                continue
            for field in ("description", "context"):
                if field in dec_edit and dec_edit[field] is not None:
                    old_val = getattr(decision, field)
                    setattr(decision, field, dec_edit[field])
                    db.add(UserCorrection(
                        analysis_id=analysis.id,
                        meeting_id=meeting_id,
                        correction_type="decision",
                        target_id=dec_id,
                        field_name=field,
                        original_value=str(old_val) if old_val else None,
                        corrected_value=str(dec_edit[field]),
                    ))
            if dec_edit.get("delete"):
                db.add(UserCorrection(
                    analysis_id=analysis.id,
                    meeting_id=meeting_id,
                    correction_type="decision",
                    target_id=dec_id,
                    field_name="_deleted",
                    original_value=decision.description,
                ))
                db.delete(decision)
                mem_store.record_content_deletion(
                    f"Decision: {decision.description[:60]}",
                    meeting_id=meeting_id,
                )

    mem_store.record_content_edit(
        f"User edited meeting notes for meeting {meeting_id[:8]}",
        meeting_id=meeting_id,
    )

    return {"meeting_id": meeting_id, "status": "updated"}


# ── Transcript Correction Endpoint ────────────────────────────────────────────

class TranscriptCorrectionRequest(BaseModel):
    segment_id: str
    corrected_text: str


@router.patch("/meetings/{meeting_id}/transcript/{segment_id}")
def correct_transcript_segment(
    meeting_id: str,
    segment_id: str,
    req: TranscriptCorrectionRequest,
    db: Session = Depends(get_db_session),
):
    """Correct a specific transcript segment. Records as a learning signal."""
    segment = db.get(TranscriptSegment, segment_id)
    if not segment or segment.meeting_id != meeting_id:
        raise HTTPException(404, "Transcript segment not found")

    original_text = segment.text
    segment.text = req.corrected_text

    # Record the correction
    db.add(UserCorrection(
        meeting_id=meeting_id,
        correction_type="transcript",
        target_id=segment_id,
        field_name="text",
        original_value=original_text,
        corrected_value=req.corrected_text,
    ))

    from backend.learning.memory import memory as mem_store
    mem_store.record_transcription_correction(
        original=original_text,
        corrected=req.corrected_text,
        meeting_id=meeting_id,
    )

    return {"segment_id": segment_id, "status": "corrected"}


# ── Pre-Meeting Briefing Endpoint ─────────────────────────────────────────────

class BriefingRequest(BaseModel):
    participants: list[str] = Field(..., min_length=1)
    purpose: str = ""


@router.post("/meetings/{meeting_id}/briefing")
def generate_meeting_briefing(
    meeting_id: str,
    req: BriefingRequest,
):
    """Generate a pre-meeting briefing based on participants and purpose."""
    from backend.intelligence.briefing import generate_briefing

    briefing = generate_briefing(
        participants=req.participants,
        purpose=req.purpose,
        meeting_id=meeting_id,
    )

    return {"meeting_id": meeting_id, "briefing": briefing}


# ── Semantic Search Endpoint ──────────────────────────────────────────────────

class SearchRequest(BaseModel):
    q: str = Field(..., min_length=1)
    n_results: int = 10
    meeting_id: Optional[str] = None


@router.get("/search")
def search_meetings(q: str, n_results: int = 10, meeting_id: Optional[str] = None):
    """Natural language search across all meetings and content."""
    from backend.storage.vector_store import vector_store

    segments = vector_store.search_segments(
        query=q, n_results=n_results, meeting_id=meeting_id,
    )
    summaries = vector_store.search_summaries(
        query=q, n_results=5,
    )

    return {
        "query": q,
        "segments": segments,
        "summaries": summaries,
    }


# ── Confidence Settings Endpoint ──────────────────────────────────────────────

@router.get("/settings/confidence")
def get_confidence_settings():
    """Get current confidence badge threshold."""
    return {
        "threshold": settings.confidence_badge_threshold,
    }


@router.patch("/settings/confidence")
def update_confidence_threshold(threshold: float):
    """Update the confidence badge threshold (0.0-1.0)."""
    if not 0.0 <= threshold <= 1.0:
        raise HTTPException(400, "Threshold must be between 0.0 and 1.0")
    settings.confidence_badge_threshold = threshold
    return {"threshold": threshold, "status": "updated"}


# ── Vector Store Stats ────────────────────────────────────────────────────────

@router.get("/vector-store/stats")
def vector_store_stats():
    """Get ChromaDB vector store statistics."""
    from backend.storage.vector_store import vector_store
    return vector_store.stats()


# ── Memory Endpoints ──────────────────────────────────────────────────────────

class MemoryUpdateRequest(BaseModel):
    content: str


@router.get("/memory/{tier}")
def get_memory(tier: str):
    """View a memory tier (short-term, medium-term, long-term)."""
    from backend.learning.memory import MemoryTier, memory as mem_store
    try:
        mem_tier = MemoryTier(tier)
    except ValueError:
        raise HTTPException(400, f"Invalid tier: {tier}. Use short-term, medium-term, or long-term.")
    return {"tier": tier, "content": mem_store.read_tier(mem_tier)}


@router.patch("/memory/{tier}")
def update_memory(tier: str, req: MemoryUpdateRequest):
    """Edit a memory tier. User edits are high-priority learning signals."""
    from backend.learning.memory import MemoryTier, memory as mem_store
    try:
        mem_tier = MemoryTier(tier)
    except ValueError:
        raise HTTPException(400, f"Invalid tier: {tier}. Use short-term, medium-term, or long-term.")
    mem_store.update_tier(mem_tier, req.content)
    return {"tier": tier, "status": "updated"}


@router.post("/memory/consolidate")
def trigger_consolidation():
    """Manually trigger memory consolidation (bypasses idle/schedule checks)."""
    from backend.learning.scheduler import scheduler
    stats = scheduler.force_run()
    return {"status": "complete", **stats}


@router.get("/memory/consolidation/status")
def consolidation_status():
    """Get current consolidation scheduler status."""
    from backend.learning.scheduler import scheduler
    return scheduler.status()


@router.post("/corrections")
def submit_correction(
    meeting_id: str = "",
    original: str = "",
    corrected: str = "",
):
    """Submit a transcription correction (feeds the learning loop)."""
    from backend.learning.memory import memory as mem_store
    mem_store.record_transcription_correction(original, corrected, meeting_id)
    return {"status": "recorded"}


# ── Correction History ────────────────────────────────────────────────────────

@router.get("/meetings/{meeting_id}/corrections")
def get_corrections(meeting_id: str, db: Session = Depends(get_db_session)):
    """Get all user corrections for a meeting."""
    corrections = (
        db.query(UserCorrection)
        .filter(UserCorrection.meeting_id == meeting_id)
        .order_by(UserCorrection.created_at.desc())
        .all()
    )
    return [
        {
            "id": c.id,
            "correction_type": c.correction_type,
            "target_id": c.target_id,
            "field_name": c.field_name,
            "original_value": c.original_value,
            "corrected_value": c.corrected_value,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in corrections
    ]


# ── Audio Upload Endpoints ────────────────────────────────────────────────────

@router.post("/meetings/upload")
async def upload_meeting_audio(
    audio: UploadFile = File(...),
    title: Optional[str] = Form(None),
    db: Session = Depends(get_db_session),
):
    """Upload an audio file to create a new meeting."""
    meeting_id = str(uuid.uuid4())
    audio_dir = Path(settings.audio_dir)
    audio_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(audio.filename).suffix if audio.filename else ".wav"
    audio_path = audio_dir / f"{meeting_id}{suffix}"

    with open(audio_path, "wb") as f:
        shutil.copyfileobj(audio.file, f)

    meeting = Meeting(
        id=meeting_id,
        title=title or audio.filename or "Uploaded Meeting",
        status=MeetingStatus.processing,
        audio_source=ModelAudioSource.microphone,
        raw_audio_path=str(audio_path),
    )
    db.add(meeting)
    db.commit()

    # Trigger processing in background
    def _run():
        try:
            from backend.intelligence.pipeline import pipeline
            pipeline.process(meeting_id)
        except Exception as e:
            logger.error(f"Upload processing failed for {meeting_id}: {e}")

    thread = threading.Thread(target=_run, daemon=True, name=f"upload-{meeting_id[:8]}")
    thread.start()

    return {"meeting_id": meeting_id, "status": "processing", "audio_path": str(audio_path)}


@router.post("/voice-memo")
async def upload_voice_memo(
    audio: UploadFile = File(...),
    db: Session = Depends(get_db_session),
):
    """Upload a voice memo (lightweight meeting record)."""
    memo_id = str(uuid.uuid4())
    audio_dir = Path(settings.audio_dir)
    audio_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(audio.filename).suffix if audio.filename else ".webm"
    audio_path = audio_dir / f"memo_{memo_id}{suffix}"

    with open(audio_path, "wb") as f:
        shutil.copyfileobj(audio.file, f)

    meeting = Meeting(
        id=memo_id,
        title="Voice Memo",
        status=MeetingStatus.processing,
        audio_source=ModelAudioSource.microphone,
        raw_audio_path=str(audio_path),
    )
    db.add(meeting)
    db.commit()

    return {"meeting_id": memo_id, "status": "processing", "audio_path": str(audio_path)}


# ── Audio Streaming ───────────────────────────────────────────────────────────

@router.get("/meetings/{meeting_id}/audio")
def get_meeting_audio(meeting_id: str, db: Session = Depends(get_db_session)):
    """Stream or download the audio file for a meeting."""
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(404, "Meeting not found")

    # Try compressed first, fall back to raw
    audio_path = None
    if meeting.compressed_audio_path:
        p = Path(meeting.compressed_audio_path)
        if p.exists():
            audio_path = p
    if audio_path is None and meeting.raw_audio_path:
        p = Path(meeting.raw_audio_path)
        if p.exists():
            audio_path = p

    if audio_path is None:
        # Search audio_dir by meeting ID
        audio_dir = Path(settings.audio_dir)
        for ext in (".wav", ".mp3", ".ogg", ".webm", ".m4a"):
            candidate = audio_dir / f"{meeting_id}{ext}"
            if candidate.exists():
                audio_path = candidate
                break

    if audio_path is None:
        raise HTTPException(404, "Audio file not found")

    return FileResponse(
        path=str(audio_path),
        filename=audio_path.name,
        media_type="audio/mpeg",
    )


# ── Full Settings Endpoints ──────────────────────────────────────────────────

class SettingsOut(BaseModel):
    llm_provider: str
    ollama_base_url: str
    ollama_model: str
    anthropic_model: str
    whisper_model: str
    confidence_badge_threshold: float
    transcription_provider: str
    sample_rate: int
    api_host: str
    api_port: int


class SettingsUpdateRequest(BaseModel):
    llm_provider: Optional[str] = None
    ollama_base_url: Optional[str] = None
    ollama_model: Optional[str] = None
    anthropic_model: Optional[str] = None
    whisper_model: Optional[str] = None
    confidence_badge_threshold: Optional[float] = None
    transcription_provider: Optional[str] = None


@router.get("/settings", response_model=SettingsOut)
def get_settings():
    """Get current application settings."""
    return SettingsOut(
        llm_provider=settings.llm_provider,
        ollama_base_url=settings.ollama_base_url,
        ollama_model=settings.ollama_model,
        anthropic_model=settings.anthropic_model,
        whisper_model=settings.whisper_model,
        confidence_badge_threshold=settings.confidence_badge_threshold,
        transcription_provider=settings.transcription_provider,
        sample_rate=settings.sample_rate,
        api_host=settings.api_host,
        api_port=settings.api_port,
    )


@router.patch("/settings")
def update_settings(req: SettingsUpdateRequest):
    """Update application settings (in-memory, non-persistent)."""
    updated = {}
    if req.llm_provider is not None:
        settings.llm_provider = req.llm_provider
        updated["llm_provider"] = req.llm_provider
    if req.ollama_base_url is not None:
        settings.ollama_base_url = req.ollama_base_url
        updated["ollama_base_url"] = req.ollama_base_url
    if req.ollama_model is not None:
        settings.ollama_model = req.ollama_model
        updated["ollama_model"] = req.ollama_model
    if req.anthropic_model is not None:
        settings.anthropic_model = req.anthropic_model
        updated["anthropic_model"] = req.anthropic_model
    if req.whisper_model is not None:
        settings.whisper_model = req.whisper_model
        updated["whisper_model"] = req.whisper_model
    if req.confidence_badge_threshold is not None:
        if not 0.0 <= req.confidence_badge_threshold <= 1.0:
            raise HTTPException(400, "confidence_badge_threshold must be between 0.0 and 1.0")
        settings.confidence_badge_threshold = req.confidence_badge_threshold
        updated["confidence_badge_threshold"] = req.confidence_badge_threshold
    if req.transcription_provider is not None:
        settings.transcription_provider = req.transcription_provider
        updated["transcription_provider"] = req.transcription_provider

    if not updated:
        raise HTTPException(400, "No valid fields to update")
    return {"status": "updated", "updated": updated}


# ── Cross-Meeting Connections ────────────────────────────────────────────────

@router.get("/connections/cross-meeting")
def get_cross_meeting_connections(db: Session = Depends(get_db_session)):
    """Get cross-meeting connections from the knowledge graph."""
    try:
        from backend.knowledge.graph import knowledge_graph
    except Exception:
        return {
            "people_referenced": [],
            "projects_referenced": [],
            "topics_referenced": [],
            "past_meeting_links": [],
            "contradictions": [],
            "open_threads": [],
        }

    graph = knowledge_graph
    people = []
    projects = []
    topics = []

    for node_id, data in graph._graph.nodes(data=True):
        entity_type = data.get("entity_type", "")
        label = data.get("label", node_id)
        # Count edges (meetings this entity appears in)
        edges = list(graph._graph.edges(node_id, data=True))
        meeting_ids = set()
        for _, target, edge_data in edges:
            mid = edge_data.get("meeting_id")
            if mid:
                meeting_ids.add(mid)

        entry = {
            "id": node_id,
            "label": label,
            "meeting_count": len(meeting_ids),
            "meeting_ids": list(meeting_ids)[:10],
        }

        if entity_type == "person":
            people.append(entry)
        elif entity_type == "project":
            projects.append(entry)
        elif entity_type == "topic":
            topics.append(entry)

    return {
        "people_referenced": sorted(people, key=lambda x: x["meeting_count"], reverse=True),
        "projects_referenced": sorted(projects, key=lambda x: x["meeting_count"], reverse=True),
        "topics_referenced": sorted(topics, key=lambda x: x["meeting_count"], reverse=True),
        "past_meeting_links": [],
        "contradictions": [],
        "open_threads": [],
    }
