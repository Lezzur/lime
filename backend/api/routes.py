"""
FastAPI REST routes for LIME Phase 1.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
import logging

from backend.storage.database import get_db_session
from backend.models.meeting import Meeting, MeetingStatus, TranscriptSegment, Speaker
from backend.audio.capture import AudioSource, list_audio_devices

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# Active sessions (meeting_id → MeetingSession)
_active_sessions: dict = {}


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


# ── Endpoints ─────────────────────────────────────────────────────────────────

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
        status="complete",
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
    """Manually trigger memory consolidation."""
    from backend.learning.consolidation import consolidator
    stats = consolidator.run()
    return {"status": "complete", **stats}


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
