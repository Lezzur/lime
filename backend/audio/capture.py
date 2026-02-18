"""
Audio capture engine.
Supports:
  - Microphone input via SoundDevice
  - System audio (WASAPI loopback) on Windows
Maintains a 30-second ring buffer and feeds audio to a queue for VAD/chunking.
"""

import threading
import queue
import time
import logging
from collections import deque
from enum import Enum
from typing import Optional, Callable
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd

from backend.config.settings import settings

logger = logging.getLogger(__name__)


class AudioSource(str, Enum):
    microphone = "microphone"
    system = "system"


class AudioCapture:
    def __init__(
        self,
        source: AudioSource = AudioSource.microphone,
        device_index: Optional[int] = None,
        on_chunk: Optional[Callable[[np.ndarray, float], None]] = None,
    ):
        self.source = source
        self.device_index = device_index
        self.on_chunk = on_chunk  # callback(audio_array, timestamp)

        self.sample_rate = settings.sample_rate
        self.channels = settings.channels
        self.ring_buffer_seconds = settings.ring_buffer_seconds

        self._ring_buffer: deque[np.ndarray] = deque(
            maxlen=int(self.ring_buffer_seconds * self.sample_rate)
        )
        self._audio_queue: queue.Queue[tuple[np.ndarray, float]] = queue.Queue()
        self._stream: Optional[sd.InputStream] = None
        self._recording = False
        self._start_time: Optional[float] = None
        self._raw_frames: list[np.ndarray] = []
        self._lock = threading.Lock()

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        if status:
            logger.error(f"Audio capture status: {status}")

        audio = indata[:, 0].copy() if indata.ndim > 1 else indata.copy()

        with self._lock:
            self._ring_buffer.extend(audio)
            self._raw_frames.append(audio)

        timestamp = time.time() - (self._start_time or time.time())
        self._audio_queue.put((audio, timestamp))

        if self.on_chunk:
            self.on_chunk(audio, timestamp)

    def start(self, raw_output_path: Optional[Path] = None) -> None:
        if self._recording:
            logger.warning("Capture already running.")
            return

        device = self._resolve_device()
        self._start_time = time.time()
        self._raw_frames.clear()
        self._raw_output_path = raw_output_path
        self._recording = True

        logger.info(f"Starting audio capture | source={self.source.value} | device={device}")

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            device=device,
            callback=self._audio_callback,
            blocksize=int(self.sample_rate * 0.032),  # 32ms blocks
        )
        self._stream.start()

    def stop(self) -> Optional[Path]:
        if not self._recording:
            return None

        self._recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        saved_path = None
        if self._raw_output_path and self._raw_frames:
            saved_path = self._save_raw_audio(self._raw_output_path)

        logger.info(f"Audio capture stopped. Duration: {self.elapsed_seconds:.1f}s")
        return saved_path

    def _save_raw_audio(self, path: Path) -> Path:
        import scipy.io.wavfile as wav
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            audio = np.concatenate(self._raw_frames)
        audio_int16 = (audio * 32767).astype(np.int16)
        wav.write(str(path), self.sample_rate, audio_int16)
        logger.info(f"Raw audio saved: {path}")
        return path

    def _resolve_device(self) -> Optional[int]:
        if self.device_index is not None:
            return self.device_index

        if self.source == AudioSource.system:
            return self._find_wasapi_loopback()

        # microphone: use configured default or system default
        return settings.mic_device_index

    def _find_wasapi_loopback(self) -> Optional[int]:
        """Find WASAPI loopback device for system audio capture on Windows."""
        if settings.system_audio_device_index is not None:
            return settings.system_audio_device_index

        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            name = dev.get("name", "").lower()
            # WASAPI loopback devices typically have "loopback" in the name
            # or are hostapi-specific
            if "loopback" in name:
                logger.info(f"Found loopback device: [{i}] {dev['name']}")
                return i

        logger.warning(
            "No WASAPI loopback device found. "
            "Ensure WASAPI loopback is available. "
            "Falling back to default output device."
        )
        return None

    @property
    def elapsed_seconds(self) -> float:
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    @property
    def is_recording(self) -> bool:
        return self._recording

    def get_ring_buffer_snapshot(self) -> np.ndarray:
        """Returns a copy of the last `ring_buffer_seconds` of audio."""
        with self._lock:
            return np.array(list(self._ring_buffer))

    def get_audio_queue(self) -> queue.Queue:
        return self._audio_queue


def list_audio_devices() -> list[dict]:
    """Return all available audio devices with index and name."""
    devices = []
    for i, dev in enumerate(sd.query_devices()):
        devices.append({
            "index": i,
            "name": dev["name"],
            "max_input_channels": dev["max_input_channels"],
            "max_output_channels": dev["max_output_channels"],
            "default_samplerate": dev["default_samplerate"],
            "hostapi": sd.query_hostapis(dev["hostapi"])["name"],
        })
    return devices
