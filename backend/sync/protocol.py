"""
Sync protocol orchestrator — push/pull logic.

Push: compute delta → encrypt → upload changelog batches + files
Pull: download remote deltas → decrypt → detect conflicts → merge → apply
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.sync.changelog import ChangeTracker, FileChangeTracker
from backend.sync.clock import HLCTimestamp, HybridLogicalClock
from backend.sync.cloud import SyncCloudClient
from backend.sync.conflict import ChangeEntry, ConflictResolver, ResolutionStrategy
from backend.sync.encryption import encryption_service
from backend.sync.models import (
    ChangeLogEntry, ChangeOperation, Device, FileSyncManifest, SyncState,
)

logger = logging.getLogger(__name__)

MAX_BATCH_SIZE = 500


class SyncProtocol:
    """Handles push/pull sync operations."""

    def __init__(
        self,
        clock: HybridLogicalClock,
        cloud: SyncCloudClient,
        change_tracker: ChangeTracker,
        file_tracker: FileChangeTracker,
        device_id: str,
    ):
        self.clock = clock
        self.cloud = cloud
        self.change_tracker = change_tracker
        self.file_tracker = file_tracker
        self.device_id = device_id
        self.conflict_resolver = ConflictResolver()

    # ── Push ─────────────────────────────────────────────────────────

    def push(self, db: Session) -> dict:
        """Push local changes to cloud. Returns stats."""
        # Get sync state cursor
        state = self._get_or_create_state(db, self.device_id)
        last_pushed = state.last_pushed_hlc

        # Query unpushed changelog entries
        query = (
            db.query(ChangeLogEntry)
            .filter(ChangeLogEntry.device_id == self.device_id)
            .order_by(ChangeLogEntry.hlc_timestamp)
        )
        if last_pushed:
            query = query.filter(ChangeLogEntry.hlc_timestamp > last_pushed)

        entries = query.all()
        if not entries:
            return {"batches_pushed": 0, "entries_pushed": 0, "files_pushed": 0}

        # Push in batches
        batches_pushed = 0
        entries_pushed = 0
        for i in range(0, len(entries), MAX_BATCH_SIZE):
            batch = entries[i:i + MAX_BATCH_SIZE]
            batch_data = [self._entry_to_dict(e) for e in batch]
            payload = json.dumps(batch_data).encode("utf-8")
            encrypted = encryption_service.encrypt_bytes(payload)

            batch_id = f"{batch[-1].hlc_timestamp}_{uuid.uuid4().hex[:8]}"
            self.cloud.upload_changelog_batch(self.device_id, batch_id, encrypted)
            batches_pushed += 1
            entries_pushed += len(batch)

        # Push changed files
        files_pushed = self._push_files(db)

        # Update cursor
        state.last_pushed_hlc = entries[-1].hlc_timestamp
        db.commit()

        logger.info(
            "Push complete: %d batches, %d entries, %d files",
            batches_pushed, entries_pushed, files_pushed,
        )
        return {
            "batches_pushed": batches_pushed,
            "entries_pushed": entries_pushed,
            "files_pushed": files_pushed,
        }

    def _push_files(self, db: Session) -> int:
        """Push changed files to content-addressed cloud storage."""
        pending = (
            db.query(FileSyncManifest)
            .filter(FileSyncManifest.synced_at.is_(None))
            .all()
        )
        pushed = 0
        for manifest in pending:
            try:
                from pathlib import Path
                file_path = Path(manifest.file_path)
                if not file_path.exists():
                    continue

                data = file_path.read_bytes()
                encrypted = encryption_service.encrypt_bytes(data)
                cloud_key = manifest.content_hash
                self.cloud.upload_file(cloud_key, encrypted)

                manifest.cloud_key = cloud_key
                manifest.synced_at = datetime.now(timezone.utc)
                pushed += 1
            except Exception:
                logger.exception("Failed to push file: %s", manifest.file_path)

        if pushed:
            db.commit()
        return pushed

    # ── Pull ─────────────────────────────────────────────────────────

    def pull(self, db: Session) -> dict:
        """Pull remote changes from cloud. Returns stats."""
        remote_devices = self.cloud.list_devices()
        total_entries = 0
        total_conflicts = 0
        total_applied = 0

        for remote_device_id in remote_devices:
            if remote_device_id == self.device_id:
                continue

            state = self._get_or_create_state(db, remote_device_id)
            last_pulled = state.last_pulled_hlc

            batches = self.cloud.list_changelog_batches(remote_device_id)
            if not batches:
                continue

            # Filter batches after our cursor
            if last_pulled:
                batches = [b for b in batches if b > last_pulled]

            for batch_id in batches:
                encrypted = self.cloud.download_changelog_batch(remote_device_id, batch_id)
                payload = encryption_service.decrypt_bytes(encrypted)
                entries = json.loads(payload)
                total_entries += len(entries)

                applied, conflicts = self._apply_remote_changes(db, entries)
                total_applied += applied
                total_conflicts += conflicts

                state.last_pulled_hlc = batch_id

            # Update device last_sync
            device = db.query(Device).filter_by(id=remote_device_id).first()
            if device:
                device.last_sync_at = datetime.now(timezone.utc)

        db.commit()

        # Update our own device last_sync
        local_device = db.query(Device).filter_by(id=self.device_id).first()
        if local_device:
            local_device.last_sync_at = datetime.now(timezone.utc)
            db.commit()

        logger.info(
            "Pull complete: %d entries, %d applied, %d conflicts",
            total_entries, total_applied, total_conflicts,
        )
        return {
            "entries_received": total_entries,
            "entries_applied": total_applied,
            "conflicts_resolved": total_conflicts,
        }

    def _apply_remote_changes(self, db: Session, entries: list[dict]) -> tuple[int, int]:
        """Apply remote changelog entries with conflict detection. Returns (applied, conflicts)."""
        applied = 0
        conflicts = 0

        with self.change_tracker.suppress():
            for entry_data in entries:
                remote = ChangeEntry(
                    hlc_timestamp=entry_data["hlc_timestamp"],
                    device_id=entry_data["device_id"],
                    entity_table=entry_data["entity_table"],
                    entity_id=entry_data["entity_id"],
                    operation=entry_data["operation"],
                    changed_fields=entry_data.get("changed_fields"),
                )

                # Receive the remote timestamp to update our HLC
                remote_ts = HLCTimestamp.from_string(remote.hlc_timestamp)
                self.clock.receive(remote_ts)

                # Check for local conflicts
                local_entry = self._find_local_conflict(db, remote)

                if local_entry:
                    conflicts += 1
                    local_change = ChangeEntry(
                        hlc_timestamp=local_entry.hlc_timestamp,
                        device_id=local_entry.device_id,
                        entity_table=local_entry.entity_table,
                        entity_id=local_entry.entity_id,
                        operation=local_entry.operation,
                        changed_fields=(
                            json.loads(local_entry.changed_fields)
                            if local_entry.changed_fields else None
                        ),
                    )

                    result = self.conflict_resolver.detect_and_resolve(local_change, remote)
                    logger.info(
                        "Conflict on %s/%s: %s — %s",
                        remote.entity_table, remote.entity_id,
                        result.strategy.value, result.details,
                    )

                    if result.strategy == ResolutionStrategy.LOCAL_WINS:
                        continue  # skip remote change
                    elif result.strategy == ResolutionStrategy.MERGE:
                        remote.changed_fields = result.merged_fields
                    # DELETE_WINS and REMOTE_WINS: apply remote as-is

                self._apply_entry(db, remote)
                applied += 1

        return applied, conflicts

    def _find_local_conflict(self, db: Session, remote: ChangeEntry) -> Optional[ChangeLogEntry]:
        """Find a local change to the same entity that might conflict."""
        return (
            db.query(ChangeLogEntry)
            .filter(
                ChangeLogEntry.entity_table == remote.entity_table,
                ChangeLogEntry.entity_id == remote.entity_id,
                ChangeLogEntry.device_id == self.device_id,
                ChangeLogEntry.hlc_timestamp >= remote.hlc_timestamp,
            )
            .order_by(ChangeLogEntry.hlc_timestamp.desc())
            .first()
        )

    def _apply_entry(self, db: Session, entry: ChangeEntry) -> None:
        """Apply a single remote change entry to the local database."""
        from backend.storage.database import Base

        # Find the SQLAlchemy model class for this table
        model_class = None
        for mapper in Base.registry.mappers:
            if mapper.class_.__tablename__ == entry.entity_table:
                model_class = mapper.class_
                break

        if model_class is None:
            logger.warning("Unknown table: %s", entry.entity_table)
            return

        if entry.operation == "DELETE":
            obj = db.query(model_class).get(entry.entity_id)
            if obj:
                db.delete(obj)

        elif entry.operation == "INSERT":
            # Check if entity already exists (idempotency)
            existing = db.query(model_class).get(entry.entity_id)
            if existing:
                # Update instead of insert
                if entry.changed_fields:
                    self._apply_fields(existing, entry.changed_fields)
            else:
                obj = model_class()
                pk_col = model_class.__table__.primary_key.columns.values()[0].name
                setattr(obj, pk_col, entry.entity_id)
                if entry.changed_fields:
                    self._apply_fields(obj, entry.changed_fields)
                db.add(obj)

        elif entry.operation == "UPDATE":
            obj = db.query(model_class).get(entry.entity_id)
            if obj and entry.changed_fields:
                self._apply_fields(obj, entry.changed_fields)

        db.flush()

    @staticmethod
    def _apply_fields(obj, fields: dict) -> None:
        """Apply field values to a SQLAlchemy object, skipping PK and non-existent columns."""
        mapper = obj.__class__.__table__
        pk_names = {col.name for col in mapper.primary_key.columns}
        column_names = {col.name for col in mapper.columns}

        for key, value in fields.items():
            if key in pk_names:
                continue
            if key not in column_names:
                continue
            setattr(obj, key, value)

    @staticmethod
    def _entry_to_dict(entry: ChangeLogEntry) -> dict:
        return {
            "hlc_timestamp": entry.hlc_timestamp,
            "device_id": entry.device_id,
            "entity_table": entry.entity_table,
            "entity_id": entry.entity_id,
            "operation": entry.operation.value if hasattr(entry.operation, "value") else entry.operation,
            "changed_fields": json.loads(entry.changed_fields) if entry.changed_fields else None,
        }

    def _get_or_create_state(self, db: Session, remote_device_id: str) -> SyncState:
        state = db.query(SyncState).filter_by(remote_device_id=remote_device_id).first()
        if not state:
            state = SyncState(remote_device_id=remote_device_id)
            db.add(state)
            db.flush()
        return state
