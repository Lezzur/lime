"""
Audio compression pipeline.
Converts raw WAV recordings to Opus format via ffmpeg.
Runs as a background task — never interrupts active processing.
Compressed audio is retained permanently unless user deletes it.
"""

import logging
import subprocess
import threading
import queue
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class AudioCompressor:
    """
    Background worker that compresses WAV files to Opus (.ogg container).
    Items are added to a queue and processed when the system is idle.
    """

    OPUS_BITRATE = "64k"   # 64kbps Opus — excellent quality for speech

    def __init__(self):
        self._queue: queue.Queue[Path] = queue.Queue()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True, name="audio-compressor")
        self._thread.start()
        logger.info("Audio compressor started.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        logger.info("Audio compressor stopped.")

    def enqueue(self, wav_path: Path) -> None:
        """Schedule a WAV file for compression. Non-blocking."""
        self._queue.put(wav_path)
        logger.debug(f"Enqueued for compression: {wav_path.name}")

    def _worker(self):
        while self._running:
            try:
                wav_path = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue

            if not wav_path.exists():
                logger.warning(f"Compression target not found: {wav_path}")
                continue

            output_path = wav_path.with_suffix(".ogg")
            success = self._compress(wav_path, output_path)

            if success:
                # Remove the original WAV to free space
                try:
                    wav_path.unlink()
                    logger.info(f"Compressed: {wav_path.name} → {output_path.name}")
                except Exception as e:
                    logger.error(f"Failed to remove raw WAV after compression: {e}")
            else:
                logger.error(f"Compression failed for {wav_path.name} — raw audio preserved.")

    def _compress(self, input_path: Path, output_path: Path) -> bool:
        try:
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-y",                    # Overwrite output if exists
                    "-i", str(input_path),
                    "-c:a", "libopus",
                    "-b:a", self.OPUS_BITRATE,
                    "-vbr", "on",
                    "-compression_level", "10",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout for very long recordings
            )
            if result.returncode != 0:
                logger.error(f"ffmpeg error: {result.stderr[-500:]}")
                return False
            return True
        except FileNotFoundError:
            logger.error(
                "ffmpeg not found. Install ffmpeg and ensure it is on PATH. "
                "Raw audio will be kept uncompressed."
            )
            return False
        except subprocess.TimeoutExpired:
            logger.error(f"ffmpeg timed out compressing {input_path.name}")
            return False
        except Exception as e:
            logger.error(f"Compression error: {e}", exc_info=True)
            return False

    def compressed_path_for(self, wav_path: Path) -> Path:
        """Returns where the compressed file would/will be."""
        return wav_path.with_suffix(".ogg")


# Module-level singleton
compressor = AudioCompressor()
