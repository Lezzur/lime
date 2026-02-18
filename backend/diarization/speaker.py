"""
Speaker diarization using pyannote-audio 3.1.
- Identifies speaker segments in audio
- Maintains voice profiles across meetings
- Labels as "Speaker 1", "Speaker 2" initially; user assigns names
- Progressively learns speaker identities over time
"""

import json
import logging
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import scipy.io.wavfile as wav

from backend.config.settings import settings

logger = logging.getLogger(__name__)

_pipeline = None
_pipeline_lock = threading.Lock()

VOICE_PROFILES_FILE = settings.audio_dir.parent / "db" / "voice_profiles.json"


@dataclass
class DiarizedSegment:
    speaker_label: str    # e.g. "SPEAKER_00"
    start: float          # seconds
    end: float


@dataclass
class SpeakerProfile:
    label: str            # "SPEAKER_00"
    display_name: str     # "Speaker 1" or user-assigned name like "Marco"
    meeting_ids: list[str] = field(default_factory=list)


def _load_pipeline():
    global _pipeline
    with _pipeline_lock:
        if _pipeline is None:
            if not settings.huggingface_token:
                logger.error(
                    "HUGGINGFACE_TOKEN not set. "
                    "pyannote.audio requires a Hugging Face token. "
                    "Get one at https://hf.co/settings/tokens and accept model terms at "
                    "https://hf.co/pyannote/speaker-diarization-3.1"
                )
                return None
            try:
                from pyannote.audio import Pipeline
                logger.info("Loading pyannote speaker diarization pipeline...")
                _pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    use_auth_token=settings.huggingface_token,
                )
                logger.info("Diarization pipeline loaded.")
            except Exception as e:
                logger.error(f"Failed to load diarization pipeline: {e}", exc_info=True)
                return None
    return _pipeline


class SpeakerDiarizer:
    def __init__(self):
        self._pipeline = None
        self._profiles: dict[str, SpeakerProfile] = {}
        self._load_profiles()

    def ensure_loaded(self):
        if self._pipeline is None:
            self._pipeline = _load_pipeline()

    def diarize(
        self,
        audio: np.ndarray,
        sample_rate: int,
        meeting_id: str,
    ) -> list[DiarizedSegment]:
        """
        Run diarization on audio. Returns segments with speaker labels.
        Gracefully degrades to a single "Speaker 1" if diarization is unavailable.
        """
        self.ensure_loaded()

        if self._pipeline is None:
            logger.warning("Diarization unavailable — returning single speaker.")
            duration = len(audio) / sample_rate
            return [DiarizedSegment("SPEAKER_00", 0.0, duration)]

        try:
            # Write audio to temp WAV for pyannote
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp_path = f.name
            audio_int16 = (audio * 32767).astype(np.int16)
            wav.write(tmp_path, sample_rate, audio_int16)

            diarization = self._pipeline(tmp_path)
            Path(tmp_path).unlink(missing_ok=True)

            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append(DiarizedSegment(
                    speaker_label=speaker,
                    start=turn.start,
                    end=turn.end,
                ))

            # Register any new speakers encountered
            for seg in segments:
                self._register_speaker(seg.speaker_label, meeting_id)

            return segments

        except Exception as e:
            logger.error(f"Diarization error: {e}", exc_info=True)
            duration = len(audio) / sample_rate
            return [DiarizedSegment("SPEAKER_00", 0.0, duration)]

    def assign_name(self, diarization_label: str, name: str):
        """User assigns a real name to a speaker label (e.g. SPEAKER_00 → 'Marco')."""
        if diarization_label in self._profiles:
            self._profiles[diarization_label].display_name = name
            self._save_profiles()
            logger.info(f"Speaker {diarization_label} assigned name: {name}")

    def get_display_name(self, diarization_label: str) -> str:
        profile = self._profiles.get(diarization_label)
        return profile.display_name if profile else diarization_label

    def get_all_profiles(self) -> list[SpeakerProfile]:
        return list(self._profiles.values())

    def _register_speaker(self, label: str, meeting_id: str):
        if label not in self._profiles:
            index = len(self._profiles) + 1
            self._profiles[label] = SpeakerProfile(
                label=label,
                display_name=f"Speaker {index}",
            )
        if meeting_id not in self._profiles[label].meeting_ids:
            self._profiles[label].meeting_ids.append(meeting_id)
        self._save_profiles()

    def _load_profiles(self):
        if VOICE_PROFILES_FILE.exists():
            try:
                with open(VOICE_PROFILES_FILE, "r") as f:
                    data = json.load(f)
                self._profiles = {
                    k: SpeakerProfile(**v) for k, v in data.items()
                }
                logger.info(f"Loaded {len(self._profiles)} voice profiles.")
            except Exception as e:
                logger.error(f"Failed to load voice profiles: {e}")

    def _save_profiles(self):
        VOICE_PROFILES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(VOICE_PROFILES_FILE, "w") as f:
            json.dump(
                {k: {"label": v.label, "display_name": v.display_name, "meeting_ids": v.meeting_ids}
                 for k, v in self._profiles.items()},
                f,
                indent=2,
            )
