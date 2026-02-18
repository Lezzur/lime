from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path
from typing import Optional, Literal


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Transcription
    transcription_provider: Literal["deepgram", "assemblyai"] = "deepgram"
    deepgram_api_key: Optional[str] = None
    assemblyai_api_key: Optional[str] = None
    whisper_model: Literal["large-v3", "medium", "small", "base", "auto"] = "auto"

    # Diarization
    huggingface_token: Optional[str] = None

    # Database
    database_url: str = f"sqlite:///{BASE_DIR}/data/db/lime.db"

    # Audio
    mic_device_index: Optional[int] = None
    system_audio_device_index: Optional[int] = None
    sample_rate: int = 16000          # 16kHz — Whisper's native rate
    channels: int = 1                  # Mono
    chunk_duration_min: float = 5.0   # Minimum chunk size in seconds
    chunk_duration_max: float = 15.0  # Maximum chunk size in seconds
    ring_buffer_seconds: int = 30     # Rolling audio buffer

    # Server
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # Storage
    audio_dir: Path = BASE_DIR / "data" / "audio"
    exports_dir: Path = BASE_DIR / "data" / "exports"
    memory_dir: Path = BASE_DIR / "memory"

    # LLM Provider
    llm_provider: Literal["ollama", "anthropic", "openai"] = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-sonnet-4-20250514"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    confidence_badge_threshold: float = 0.7

    # Memory Consolidation
    consolidation_check_interval: float = 60.0       # Seconds between idle checks
    consolidation_max_daily_runs: int = 1             # At most N consolidation runs per day
    consolidation_forced_interval_days: int = 14      # Forced run if no idle window in N days

    # Web Push (VAPID)
    vapid_private_key: Optional[str] = None
    vapid_mailto: Optional[str] = None

    # Sync Engine
    sync_enabled: bool = False
    sync_interval_seconds: int = 300                    # 5 minutes
    sync_user_id: str = "default"
    sync_s3_endpoint_url: Optional[str] = None          # e.g. http://localhost:9000
    sync_s3_access_key: Optional[str] = None
    sync_s3_secret_key: Optional[str] = None
    sync_s3_bucket: str = "lime-sync"
    sync_s3_region: str = "us-east-1"
    sync_max_batch_size: int = 500
    sync_audio_enabled: bool = False
    sync_changelog_retention_days: int = 90

    # Zero-Knowledge Encryption
    crypto_vault_path: Path = BASE_DIR / "data" / "crypto" / "vault.json"
    argon2_time_cost: int = 3
    argon2_memory_cost: int = 65536          # 64 MB
    argon2_parallelism: int = 4
    argon2_hash_len: int = 32                # 256-bit key
    argon2_salt_len: int = 16
    crypto_nonce_len: int = 12               # AES-GCM standard
    crypto_tag_len: int = 16                 # AES-GCM tag
    crypto_file_chunk_size: int = 1_048_576  # 1 MB
    crypto_session_timeout_minutes: int = 30

    def model_post_init(self, __context):
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        (BASE_DIR / "data" / "db").mkdir(parents=True, exist_ok=True)
        self.crypto_vault_path.parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
