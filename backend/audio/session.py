"""
MeetingSession — orchestrates the full audio pipeline for a single recording.
Audio Capture → VAD → Chunker → Transcription → Diarization → DB Storage
"""

import queue
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Callable

import numpy as np

from backend.config.settings import settings
from backend.audio.capture import AudioCapture, AudioSource
from backend.audio.vad import VADFilter
from backend.audio.chunker import AudioChunker
from backend.audio.compressor import compressor
from backend.transcription.engine import TranscriptionEngine
from backend.transcription.local import TranscriptResult
from backend.diarization.speaker import SpeakerDiarizer, DiarizedSegment
from backend.storage.database import get_db
from backend.models.meeting import (
    Meeting, MeetingStatus, AudioSource as DBAudioSource,
    TranscriptSegment, Speaker, MeetingSpeaker
)

logger = logging.getLogger(__name__)


class MeetingSession:
    def __init__(
        self,
        source: AudioSource = AudioSource.microphone,
        device_index: Optional[int] = None,
        on_transcript: Optional[Callable[[TranscriptResult], None]] = None,
    ):
        self.source = source
        self.device_index = device_index
        self.on_transcript = on_transcript  # Live callback for WebSocket streaming

        self.meeting_id: Optional[str] = None
        self._full_audio: list[np.ndarray] = []

        # Pipeline queues
        self._raw_queue: queue.Queue = queue.Queue()
        self._vad_queue: queue.Queue = queue.Queue()
        self._chunk_queue: queue.Queue = queue.Queue()

        # Pipeline components
        self._capture = AudioCapture(
            source=source,
            device_index=device_index,
            on_chunk=self._on_raw_audio,
        )
        self._vad = VADFilter(self._raw_queue, self._vad_queue)
        self._chunker = AudioChunker(self._vad_queue, self._chunk_queue)
        self._transcription = TranscriptionEngine(
            self._chunk_queue,
            on_result=self._on_transcript_result,
        )
        self._diarizer = SpeakerDiarizer()

    def start(self) -> str:
        """Start recording. Returns meeting_id."""
        # Create DB record
        db_source = (
            DBAudioSource.system if self.source == AudioSource.system
            else DBAudioSource.microphone
        )
        with get_db() as db:
            meeting = Meeting(status=MeetingStatus.recording, audio_source=db_source)
            db.add(meeting)
            db.flush()
            self.meeting_id = meeting.id

        logger.info(f"Meeting started: {self.meeting_id}")

        # Start pipeline (order matters)
        self._vad.start()
        self._chunker.start()
        self._transcription.start()

        raw_path = settings.audio_dir / f"{self.meeting_id}_raw.wav"
        self._capture.start(raw_output_path=raw_path)

        return self.meeting_id

    def stop(self) -> dict:
        """Stop recording. Returns summary dict."""
        logger.info(f"Stopping meeting: {self.meeting_id}")

        raw_path = self._capture.stop()
        duration = self._capture.elapsed_seconds

        self._vad.stop()
        self._chunker.stop()
        self._transcription.stop()

        # Update DB record
        with get_db() as db:
            meeting = db.get(Meeting, self.meeting_id)
            if meeting:
                meeting.status = MeetingStatus.complete
                meeting.ended_at = datetime.now(timezone.utc)
                meeting.duration_seconds = duration
                if raw_path:
                    meeting.raw_audio_path = str(raw_path)

        # Schedule compression as background task
        if raw_path and raw_path.exists():
            compressor.enqueue(raw_path)

        return {
            "meeting_id": self.meeting_id,
            "duration_seconds": duration,
            "raw_audio": str(raw_path) if raw_path else None,
        }

    def _on_raw_audio(self, audio: np.ndarray, timestamp: float):
        """Direct callback from AudioCapture — feeds VAD."""
        self._full_audio.append(audio)
        self._raw_queue.put((audio, timestamp))

    def _on_transcript_result(self, result: TranscriptResult):
        """Called by TranscriptionEngine for each completed segment."""
        logger.info(
            f"[{result.start_time:.1f}s → {result.end_time:.1f}s] "
            f"({result.language}, {result.confidence:.0%}) {result.text[:80]}"
        )

        # Persist to DB
        with get_db() as db:
            segment = TranscriptSegment(
                meeting_id=self.meeting_id,
                start_time=result.start_time,
                end_time=result.end_time,
                text=result.text,
                language=result.language,
                confidence=result.confidence,
                is_low_confidence=result.confidence < 0.6,
                transcription_source=result.source,
            )
            db.add(segment)

        # Fire live callback (for WebSocket streaming)
        if self.on_transcript:
            self.on_transcript(result)
