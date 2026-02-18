"""
Cloud transcription fallback.
Supports Deepgram Nova-2 and AssemblyAI.
User selects provider in settings.
"""

import logging
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
import scipy.io.wavfile as wav

from backend.config.settings import settings
from backend.transcription.local import TranscriptResult, TranscriptWord

logger = logging.getLogger(__name__)


def _audio_to_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    """Write numpy float32 audio to WAV bytes."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name
    audio_int16 = (audio * 32767).astype(np.int16)
    wav.write(tmp_path, sample_rate, audio_int16)
    with open(tmp_path, "rb") as f:
        data = f.read()
    Path(tmp_path).unlink(missing_ok=True)
    return data


class DeepgramTranscriber:
    def __init__(self):
        if not settings.deepgram_api_key:
            raise RuntimeError("DEEPGRAM_API_KEY not set in environment.")

    def transcribe(
        self,
        audio: np.ndarray,
        start_time: float,
        end_time: float,
    ) -> Optional[TranscriptResult]:
        try:
            from deepgram import DeepgramClient, PrerecordedOptions

            client = DeepgramClient(settings.deepgram_api_key)
            audio_bytes = _audio_to_wav_bytes(audio, settings.sample_rate)

            options = PrerecordedOptions(
                model="nova-2",
                language="en",
                detect_language=True,
                punctuate=True,
                diarize=False,  # Diarization handled by pyannote
                smart_format=True,
                utterances=False,
                words=True,
            )

            response = client.listen.prerecorded.v("1").transcribe_file(
                {"buffer": audio_bytes, "mimetype": "audio/wav"},
                options,
            )

            alt = response.results.channels[0].alternatives[0]
            text = alt.transcript.strip()
            if not text:
                return None

            detected_lang = (
                response.results.channels[0].detected_language or "en"
            )
            words = []
            if alt.words:
                for w in alt.words:
                    words.append(TranscriptWord(
                        word=w.word,
                        start=start_time + w.start,
                        end=start_time + w.end,
                        probability=w.confidence,
                    ))

            return TranscriptResult(
                text=text,
                language=detected_lang,
                language_probability=1.0,
                start_time=start_time,
                end_time=end_time,
                words=words,
                source="deepgram",
            )

        except Exception as e:
            logger.error(f"Deepgram transcription error: {e}", exc_info=True)
            return None


class AssemblyAITranscriber:
    def __init__(self):
        if not settings.assemblyai_api_key:
            raise RuntimeError("ASSEMBLYAI_API_KEY not set in environment.")

    def transcribe(
        self,
        audio: np.ndarray,
        start_time: float,
        end_time: float,
    ) -> Optional[TranscriptResult]:
        try:
            import assemblyai as aai

            aai.settings.api_key = settings.assemblyai_api_key

            audio_bytes = _audio_to_wav_bytes(audio, settings.sample_rate)
            config = aai.TranscriptionConfig(
                language_detection=True,
                punctuate=True,
                format_text=True,
            )
            transcriber = aai.Transcriber(config=config)
            transcript = transcriber.transcribe(audio_bytes)

            if transcript.status == aai.TranscriptStatus.error:
                logger.error(f"AssemblyAI error: {transcript.error}")
                return None

            text = (transcript.text or "").strip()
            if not text:
                return None

            words = []
            if transcript.words:
                for w in transcript.words:
                    words.append(TranscriptWord(
                        word=w.text,
                        start=start_time + w.start / 1000,
                        end=start_time + w.end / 1000,
                        probability=w.confidence,
                    ))

            return TranscriptResult(
                text=text,
                language=transcript.language_code or "en",
                language_probability=1.0,
                start_time=start_time,
                end_time=end_time,
                words=words,
                source="assemblyai",
            )

        except Exception as e:
            logger.error(f"AssemblyAI transcription error: {e}", exc_info=True)
            return None
