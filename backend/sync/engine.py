"""
High-level sync engine — lifecycle management and auto-sync loop.

Lifecycle: initialize → setup_encryption → sync
"""

import asyncio
import logging
import platform
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.config.settings import settings
from backend.storage.database import SessionLocal, get_db
from backend.sync.changelog import ChangeTracker, FileChangeTracker
from backend.sync.clock import HybridLogicalClock
from backend.sync.cloud import SyncCloudClient
from backend.sync.models import Device, DeviceType
from backend.sync.protocol import SyncProtocol
from backend.sync.vault import vault

logger = logging.getLogger(__name__)


class SyncEngine:
    """Orchestrates the sync lifecycle."""

    def __init__(self):
        self._device_id: Optional[str] = None
        self._clock: Optional[HybridLogicalClock] = None
        self._cloud: Optional[SyncCloudClient] = None
        self._protocol: Optional[SyncProtocol] = None
        self._change_tracker: Optional[ChangeTracker] = None
        self._file_tracker: Optional[FileChangeTracker] = None
        self._sync_lock = asyncio.Lock()
        self._auto_sync_task: Optional[asyncio.Task] = None
        self._online = True
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def device_id(self) -> Optional[str]:
        return self._device_id

    # ── Initialize ──────────────────────────────────────────────────

    def initialize(self) -> dict:
        """Create or load device identity, install change tracking, init components."""
        with get_db() as db:
            device = db.query(Device).filter_by(is_current=True).first()

            if device:
                self._device_id = device.id
                logger.info("Loaded existing device: %s (%s)", device.name, device.id)
            else:
                self._device_id = str(uuid.uuid4())
                device = Device(
                    id=self._device_id,
                    name=platform.node() or "unknown",
                    device_type=DeviceType.desktop,
                    is_current=True,
                )
                db.add(device)
                db.commit()
                logger.info("Created new device: %s (%s)", device.name, device.id)

        # Init components
        self._clock = HybridLogicalClock(self._device_id)
        self._cloud = SyncCloudClient()
        self._change_tracker = ChangeTracker(self._clock, self._device_id)
        self._file_tracker = FileChangeTracker(SessionLocal)

        # Install change tracking on the session factory
        self._change_tracker.install(SessionLocal)

        self._protocol = SyncProtocol(
            clock=self._clock,
            cloud=self._cloud,
            change_tracker=self._change_tracker,
            file_tracker=self._file_tracker,
            device_id=self._device_id,
        )

        self._initialized = True
        return {"device_id": self._device_id, "device_name": platform.node()}

    # ── Encryption Setup ────────────────────────────────────────────

    def setup_encryption(self, passphrase: str) -> dict:
        """Set up encryption. If vault is not initialized, init it. Otherwise unlock."""
        if not vault.is_initialized:
            result = vault.setup(passphrase)
            # Upload encrypted verification data to cloud for multi-device
            try:
                self._cloud.ensure_bucket()
            except Exception:
                logger.warning("Could not ensure S3 bucket — will retry on sync")
            return {"action": "initialized", **result}
        else:
            result = vault.unlock(passphrase)
            return {"action": "unlocked", **result}

    # ── Initial Clone (new device) ──────────────────────────────────

    def initial_clone(self, db: Session) -> dict:
        """Full data download for a new device joining the mesh."""
        if not vault.is_unlocked:
            raise RuntimeError("Vault must be unlocked before initial clone")

        # Pull all changelog batches from all devices
        stats = self._protocol.pull(db)

        # Rebuild ChromaDB from SQLite data
        self._rebuild_vector_store(db)

        logger.info("Initial clone complete: %s", stats)
        return stats

    def _rebuild_vector_store(self, db: Session) -> None:
        """Rebuild ChromaDB index from SQLite transcript data."""
        try:
            from backend.storage.vector_store import vector_store
            from backend.models.meeting import TranscriptSegment, Meeting

            segments = db.query(TranscriptSegment).all()
            if not segments:
                return

            for segment in segments:
                meeting = db.query(Meeting).get(segment.meeting_id)
                if meeting:
                    vector_store.add_segment(
                        segment_id=segment.id,
                        text=segment.text,
                        meeting_id=segment.meeting_id,
                        meeting_title=meeting.title or "",
                        speaker_id=segment.speaker_id or "",
                        start_time=segment.start_time,
                    )
            logger.info("Rebuilt vector store with %d segments", len(segments))
        except Exception:
            logger.exception("Failed to rebuild vector store")

    # ── Sync Now ────────────────────────────────────────────────────

    async def sync_now(self) -> dict:
        """Push then pull, thread-safe."""
        if not self._initialized:
            raise RuntimeError("Sync engine not initialized")
        if not vault.is_unlocked:
            raise RuntimeError("Vault is locked")

        async with self._sync_lock:
            with get_db() as db:
                # Track file changes before pushing
                self._track_file_changes(db)

                push_stats = self._protocol.push(db)
                pull_stats = self._protocol.pull(db)

        return {"push": push_stats, "pull": pull_stats}

    def _track_file_changes(self, db: Session) -> None:
        """Check all trackable files for changes."""
        # Knowledge graph JSON
        kg_path = settings.memory_dir.parent / "data" / "knowledge_graph.json"
        if kg_path.exists():
            self._file_tracker.check_file(kg_path, "knowledge_graph", db)

        # Memory tier files
        for tier in ["short_term", "medium_term", "long_term"]:
            tier_path = settings.memory_dir / f"{tier}.md"
            if tier_path.exists():
                self._file_tracker.check_file(tier_path, f"memory_{tier}", db)

        # Audio files (if enabled)
        if settings.sync_audio_enabled:
            from backend.models.meeting import Meeting
            meetings = db.query(Meeting).filter(Meeting.compressed_audio_path.isnot(None)).all()
            for meeting in meetings:
                from pathlib import Path
                audio_path = Path(meeting.compressed_audio_path)
                if audio_path.exists():
                    self._file_tracker.check_file(audio_path, "audio", db)

        db.flush()

    # ── Auto-Sync Loop ──────────────────────────────────────────────

    async def start_auto_sync(self) -> None:
        """Start the background auto-sync loop."""
        if self._auto_sync_task and not self._auto_sync_task.done():
            return
        self._auto_sync_task = asyncio.create_task(self._auto_sync_loop())
        logger.info("Auto-sync started (interval: %ds)", settings.sync_interval_seconds)

    async def stop_auto_sync(self) -> None:
        """Stop the background auto-sync loop."""
        if self._auto_sync_task:
            self._auto_sync_task.cancel()
            try:
                await self._auto_sync_task
            except asyncio.CancelledError:
                pass
            self._auto_sync_task = None
            logger.info("Auto-sync stopped")

    async def _auto_sync_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(settings.sync_interval_seconds)
                if self._online and vault.is_unlocked:
                    await self.sync_now()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Auto-sync error")

    # ── Connectivity ────────────────────────────────────────────────

    async def set_online(self, online: bool) -> None:
        """Update connectivity state. Triggers sync on reconnect."""
        was_offline = not self._online
        self._online = online

        if online and was_offline and vault.is_unlocked:
            logger.info("Back online — triggering sync")
            try:
                await self.sync_now()
            except Exception:
                logger.exception("Sync on reconnect failed")

    # ── Status ──────────────────────────────────────────────────────

    def status(self) -> dict:
        return {
            "initialized": self._initialized,
            "device_id": self._device_id,
            "vault_unlocked": vault.is_unlocked,
            "online": self._online,
            "auto_sync_running": (
                self._auto_sync_task is not None
                and not self._auto_sync_task.done()
            ),
            "sync_interval_seconds": settings.sync_interval_seconds,
        }

    # ── Device Management ───────────────────────────────────────────

    def list_devices(self, db: Session) -> list[dict]:
        devices = db.query(Device).all()
        return [
            {
                "id": d.id,
                "name": d.name,
                "device_type": d.device_type.value if d.device_type else None,
                "last_sync_at": d.last_sync_at.isoformat() if d.last_sync_at else None,
                "is_current": d.is_current,
            }
            for d in devices
        ]

    def remove_device(self, db: Session, device_id: str) -> dict:
        device = db.query(Device).filter_by(id=device_id).first()
        if not device:
            raise ValueError(f"Device not found: {device_id}")
        if device.is_current:
            raise ValueError("Cannot remove the current device")

        # Remove cloud data
        try:
            deleted = self._cloud.delete_device_data(device_id)
        except Exception:
            logger.warning("Could not clean cloud data for device %s", device_id)
            deleted = 0

        db.delete(device)
        db.commit()
        return {"device_id": device_id, "cloud_objects_deleted": deleted}


# Module-level singleton
sync_engine = SyncEngine()
