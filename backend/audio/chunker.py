"""
Audio chunker. Takes VAD-filtered speech segments and produces
5-15 second chunks for transcription. Ensures chunks don't split mid-word
by accumulating until a natural boundary (silence after MIN duration).
"""

import queue
import threading
import logging
from typing import Optional

import numpy as np

from backend.config.settings import settings

logger = logging.getLogger(__name__)


class AudioChunker:
    """
    Accumulates speech segments from the VAD output queue and emits
    transcription-ready chunks between chunk_duration_min and chunk_duration_max.
    """

    def __init__(self, input_queue: queue.Queue, output_queue: queue.Queue):
        self.input_queue = input_queue   # VAD output: (audio: np.ndarray, timestamp: float)
        self.output_queue = output_queue  # Transcription input: (audio, start_time, end_time)

        self.sample_rate = settings.sample_rate
        self.min_samples = int(settings.chunk_duration_min * self.sample_rate)
        self.max_samples = int(settings.chunk_duration_max * self.sample_rate)

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._buffer: list[np.ndarray] = []
        self._buffer_samples = 0
        self._chunk_start_time: float = 0.0

    def start(self):
        self._running = True
        self._buffer.clear()
        self._buffer_samples = 0
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()
        logger.info("Audio chunker started.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        self._flush()
        logger.info("Audio chunker stopped.")

    def _process_loop(self):
        while self._running:
            try:
                audio, timestamp = self.input_queue.get(timeout=0.5)
            except queue.Empty:
                # Flush if buffer has been sitting for > max duration
                if self._buffer_samples >= self.min_samples:
                    self._flush()
                continue

            if self._buffer_samples == 0:
                self._chunk_start_time = timestamp

            self._buffer.append(audio)
            self._buffer_samples += len(audio)

            # Emit chunk when we hit the natural boundary (VAD segment end) >= min_duration
            # OR force-emit when we hit max_duration
            if self._buffer_samples >= self.min_samples:
                self._flush()

            elif self._buffer_samples >= self.max_samples:
                logger.debug("Max chunk size reached, forcing flush.")
                self._flush()

    def _flush(self):
        if not self._buffer:
            return

        combined = np.concatenate(self._buffer)
        duration = len(combined) / self.sample_rate
        end_time = self._chunk_start_time + duration

        self.output_queue.put((combined, self._chunk_start_time, end_time))
        logger.debug(f"Chunk emitted: {duration:.2f}s [{self._chunk_start_time:.1f}s → {end_time:.1f}s]")

        self._buffer.clear()
        self._buffer_samples = 0
