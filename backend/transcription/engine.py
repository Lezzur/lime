"""
Unified transcription engine.
Fallback chain: Local (faster-whisper) → Cloud (Deepgram / AssemblyAI)
Runs in a worker thread consuming from the chunker output queue.
"""

import queue
import threading
import logging
from typing import Optional, Callable

import numpy as np

from backend.config.settings import settings
from backend.transcription.local import LocalTranscriber, TranscriptResult

logger = logging.getLogger(__name__)


class TranscriptionEngine:
    def __init__(
        self,
        input_queue: queue.Queue,
        on_result: Optional[Callable[[TranscriptResult], None]] = None,
    ):
        self.input_queue = input_queue   # from AudioChunker: (audio, start_time, end_time)
        self.on_result = on_result

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._local = LocalTranscriber()
        self._cloud = self._init_cloud()

    def _init_cloud(self):
        provider = settings.transcription_provider
        try:
            if provider == "deepgram":
                from backend.transcription.cloud import DeepgramTranscriber
                return DeepgramTranscriber()
            elif provider == "assemblyai":
                from backend.transcription.cloud import AssemblyAITranscriber
                return AssemblyAITranscriber()
        except RuntimeError as e:
            logger.warning(f"Cloud transcription unavailable: {e}")
        return None

    def preload(self):
        """Eagerly load the local Whisper model in a background thread."""
        t = threading.Thread(target=self._local.ensure_loaded, daemon=True)
        t.start()

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        logger.info("Transcription engine started.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=10.0)
        logger.info("Transcription engine stopped.")

    def _worker(self):
        while self._running:
            try:
                audio, start_time, end_time = self.input_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            result = self._transcribe(audio, start_time, end_time)
            if result and self.on_result:
                self.on_result(result)

    def _transcribe(
        self, audio: np.ndarray, start_time: float, end_time: float
    ) -> Optional[TranscriptResult]:
        # Try local first
        result = self._local.transcribe(audio, start_time, end_time)
        if result:
            return result

        # Fallback to cloud
        if self._cloud:
            logger.info("Local transcription returned nothing — trying cloud fallback.")
            result = self._cloud.transcribe(audio, start_time, end_time)
            if result:
                return result

        logger.warning(f"No transcript produced for segment [{start_time:.1f}s → {end_time:.1f}s]")
        return None
