"""
Local transcription using faster-whisper (CTranslate2 backend).
Auto-selects model based on available GPU VRAM:
  - large-v3 : ~4GB VRAM
  - medium   : ~2GB VRAM
  - small    : ~1GB VRAM / CPU-friendly
  - base     : minimal resources
"""

import logging
import threading
from dataclasses import dataclass
from typing import Optional

import numpy as np

from backend.config.settings import settings

logger = logging.getLogger(__name__)

_model = None
_model_lock = threading.Lock()


@dataclass
class TranscriptWord:
    word: str
    start: float
    end: float
    probability: float


@dataclass
class TranscriptResult:
    text: str
    language: str
    language_probability: float
    start_time: float
    end_time: float
    words: list[TranscriptWord]
    source: str = "local"

    @property
    def confidence(self) -> float:
        if not self.words:
            return self.language_probability
        return sum(w.probability for w in self.words) / len(self.words)


def _detect_available_vram() -> int:
    """Returns available VRAM in MB. Returns 0 if no GPU."""
    try:
        import torch
        if torch.cuda.is_available():
            free, total = torch.cuda.mem_get_info()
            return free // (1024 * 1024)
    except Exception:
        pass
    return 0


def _select_model_size() -> str:
    if settings.whisper_model != "auto":
        return settings.whisper_model

    vram_mb = _detect_available_vram()
    if vram_mb >= 4500:
        model = "large-v3"
    elif vram_mb >= 2200:
        model = "medium"
    elif vram_mb >= 1100:
        model = "small"
    else:
        model = "base"

    logger.info(f"VRAM available: {vram_mb}MB → selected Whisper model: {model}")
    return model


def load_model():
    global _model
    with _model_lock:
        if _model is None:
            from faster_whisper import WhisperModel
            model_size = _select_model_size()
            vram_mb = _detect_available_vram()
            device = "cuda" if vram_mb > 0 else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"

            logger.info(f"Loading Whisper model: {model_size} on {device} ({compute_type})")
            _model = WhisperModel(model_size, device=device, compute_type=compute_type)
            logger.info("Whisper model loaded.")
    return _model


class LocalTranscriber:
    LOW_CONFIDENCE_THRESHOLD = 0.6

    def __init__(self):
        self._model = None

    def ensure_loaded(self):
        if self._model is None:
            self._model = load_model()

    def transcribe(
        self,
        audio: np.ndarray,
        start_time: float,
        end_time: float,
        language: Optional[str] = None,
    ) -> Optional[TranscriptResult]:
        self.ensure_loaded()

        try:
            segments, info = self._model.transcribe(
                audio,
                language=language,
                beam_size=5,
                word_timestamps=True,
                vad_filter=False,  # VAD already applied upstream
            )

            words = []
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())
                if segment.words:
                    for w in segment.words:
                        words.append(TranscriptWord(
                            word=w.word,
                            start=start_time + w.start,
                            end=start_time + w.end,
                            probability=w.probability,
                        ))

            full_text = " ".join(text_parts).strip()
            if not full_text:
                return None

            result = TranscriptResult(
                text=full_text,
                language=info.language,
                language_probability=info.language_probability,
                start_time=start_time,
                end_time=end_time,
                words=words,
            )

            if result.confidence < self.LOW_CONFIDENCE_THRESHOLD:
                logger.warning(
                    f"Low-confidence segment ({result.confidence:.2f}): '{full_text[:60]}'"
                )

            return result

        except Exception as e:
            logger.error(f"Local transcription error: {e}", exc_info=True)
            return None
