"""
Voice Activity Detection using Silero VAD.
Filters audio stream to only pass speech segments downstream.
~30ms latency, high accuracy, CPU-friendly.
"""

import logging
import queue
import threading
from typing import Optional

import numpy as np

from backend.config.settings import settings

logger = logging.getLogger(__name__)

_vad_model = None
_vad_utils = None
_model_lock = threading.Lock()


def _load_model():
    global _vad_model, _vad_utils
    with _model_lock:
        if _vad_model is None:
            try:
                import torch
            except ImportError:
                raise RuntimeError(
                    "torch is not installed. "
                    "Install it with: pip install torch"
                )
            logger.info("Loading Silero VAD model...")
            _vad_model, _vad_utils = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
                onnx=False,
            )
            logger.info("Silero VAD loaded.")
    return _vad_model, _vad_utils


class VADFilter:
    """
    Wraps Silero VAD. Consumes raw audio chunks from an input queue
    and outputs speech-only chunks to an output queue.
    """

    SPEECH_THRESHOLD = 0.5         # Probability above which audio is speech
    MIN_SPEECH_DURATION_MS = 250   # Ignore speech bursts shorter than this
    MIN_SILENCE_DURATION_MS = 300  # Silence needed to end a speech segment
    WINDOW_SIZE_SAMPLES = 512      # Silero VAD window (must be 256, 512, or 1024 @ 16kHz)

    def __init__(self, input_queue: queue.Queue, output_queue: queue.Queue):
        self.input_queue = input_queue
        self.output_queue = output_queue
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._model, utils = _load_model()
        (self.get_speech_timestamps, _, _, _, _) = utils
        self._reset_state()

    def _reset_state(self):
        if hasattr(self, '_model'):
            self._model.reset_states()
        self._speech_buffer = []
        self._silence_frames = 0
        self._speaking = False

    def start(self):
        self._running = True
        self._reset_state()
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()
        logger.info("VAD filter started.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        # Flush remaining buffer
        if self._speech_buffer:
            combined = np.concatenate(self._speech_buffer)
            self.output_queue.put((combined, True))  # (audio, is_speech)
            self._speech_buffer.clear()
        logger.info("VAD filter stopped.")

    def _process_loop(self):
        sample_rate = settings.sample_rate
        silence_threshold_frames = int(
            self.MIN_SILENCE_DURATION_MS / 1000 * sample_rate / self.WINDOW_SIZE_SAMPLES
        )

        while self._running:
            try:
                audio_chunk, timestamp = self.input_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            # Process in windows of WINDOW_SIZE_SAMPLES
            for i in range(0, len(audio_chunk), self.WINDOW_SIZE_SAMPLES):
                window = audio_chunk[i: i + self.WINDOW_SIZE_SAMPLES]
                if len(window) < self.WINDOW_SIZE_SAMPLES:
                    # Pad last window
                    window = np.pad(window, (0, self.WINDOW_SIZE_SAMPLES - len(window)))

                import torch
                tensor = torch.from_numpy(window).float()
                with torch.no_grad():
                    prob = self._model(tensor, sample_rate).item()

                is_speech = prob >= self.SPEECH_THRESHOLD

                if is_speech:
                    self._speech_buffer.append(window)
                    self._silence_frames = 0
                    self._speaking = True
                elif self._speaking:
                    self._silence_frames += 1
                    self._speech_buffer.append(window)  # Include trailing silence
                    if self._silence_frames >= silence_threshold_frames:
                        # End of speech segment
                        combined = np.concatenate(self._speech_buffer)
                        self.output_queue.put((combined, timestamp))
                        self._speech_buffer = []
                        self._silence_frames = 0
                        self._speaking = False
