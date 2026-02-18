"""
Change tracking for the sync engine.

Hooks into SQLAlchemy after_flush events to automatically log INSERT/UPDATE/DELETE
operations on syncable tables. Also tracks file changes (knowledge graph, memory, audio).
"""

import hashlib
import json
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from backend.sync.clock import HybridLogicalClock
from backend.sync.models import ChangeLogEntry, ChangeOperation, FileSyncManifest

logger = logging.getLogger(__name__)

SYNCABLE_TABLES = {
    "meetings",
    "speakers",
    "meeting_speakers",
    "transcript_segments",
    "meeting_analyses",
    "action_items",
    "analysis_decisions",
    "topic_segments",
    "user_corrections",
    "people",
    "projects",
    "decisions",
    "topics",
    "person_meetings",
    "project_meetings",
    "topic_meetings",
}


class ChangeTracker:
    """Hooks into SQLAlchemy to auto-log changes on syncable tables."""

    def __init__(self, clock: HybridLogicalClock, device_id: str):
        self.clock = clock
        self.device_id = device_id
        self._suppressed = False
        self._installed = False

    def install(self, session_factory) -> None:
        """Register SQLAlchemy event listeners."""
        if self._installed:
            return
        event.listen(session_factory, "after_flush", self._after_flush)
        self._installed = True
        logger.info("Change tracker installed on session factory")

    @contextmanager
    def suppress(self):
        """Disable change tracking (use during sync-apply to prevent echo)."""
        self._suppressed = True
        try:
            yield
        finally:
            self._suppressed = False

    def _after_flush(self, session: Session, flush_context) -> None:
        if self._suppressed:
            return

        entries = []

        # INSERTs
        for obj in session.new:
            table = obj.__class__.__tablename__
            if table not in SYNCABLE_TABLES:
                continue
            mapper = inspect(obj.__class__)
            pk = self._get_pk(obj, mapper)
            fields = self._get_all_fields(obj, mapper)
            entries.append(self._make_entry(
                table, pk, ChangeOperation.INSERT, fields,
            ))

        # UPDATEs
        for obj in session.dirty:
            if not session.is_modified(obj, include_collections=False):
                continue
            table = obj.__class__.__tablename__
            if table not in SYNCABLE_TABLES:
                continue
            mapper = inspect(obj.__class__)
            pk = self._get_pk(obj, mapper)
            changed = self._get_changed_fields(obj, mapper)
            if not changed:
                continue
            entries.append(self._make_entry(
                table, pk, ChangeOperation.UPDATE, changed,
            ))

        # DELETEs
        for obj in session.deleted:
            table = obj.__class__.__tablename__
            if table not in SYNCABLE_TABLES:
                continue
            mapper = inspect(obj.__class__)
            pk = self._get_pk(obj, mapper)
            entries.append(self._make_entry(
                table, pk, ChangeOperation.DELETE, None,
            ))

        for entry in entries:
            session.add(entry)

    def _make_entry(
        self,
        table: str,
        entity_id: str,
        operation: ChangeOperation,
        fields: Optional[dict],
    ) -> ChangeLogEntry:
        ts = self.clock.now()
        return ChangeLogEntry(
            hlc_timestamp=str(ts),
            device_id=self.device_id,
            entity_table=table,
            entity_id=entity_id,
            operation=operation,
            changed_fields=json.dumps(fields, default=str) if fields else None,
        )

    @staticmethod
    def _get_pk(obj, mapper) -> str:
        pk_cols = mapper.primary_key
        pk_values = [getattr(obj, col.name) for col in pk_cols]
        return str(pk_values[0]) if len(pk_values) == 1 else json.dumps(pk_values)

    @staticmethod
    def _get_all_fields(obj, mapper) -> dict:
        result = {}
        for col in mapper.columns:
            val = getattr(obj, col.key)
            if val is not None:
                result[col.key] = val
        return result

    @staticmethod
    def _get_changed_fields(obj, mapper) -> dict:
        insp = inspect(obj)
        changed = {}
        for attr in mapper.column_attrs:
            hist = insp.attrs[attr.key].history
            if hist.has_changes():
                changed[attr.key] = getattr(obj, attr.key)
        return changed


class FileChangeTracker:
    """Tracks changes to non-SQL files (knowledge graph JSON, memory .md, audio)."""

    def __init__(self, db_session_factory):
        self._session_factory = db_session_factory

    @staticmethod
    def compute_hash(file_path: Path) -> str:
        """SHA-256 hash of a file."""
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()

    def check_file(self, file_path: Path, file_type: str, db: Session) -> Optional[FileSyncManifest]:
        """Check if a file has changed since last sync. Returns manifest entry if changed."""
        file_path = Path(file_path)
        if not file_path.exists():
            return None

        current_hash = self.compute_hash(file_path)
        size_bytes = file_path.stat().st_size

        existing = (
            db.query(FileSyncManifest)
            .filter_by(file_path=str(file_path), file_type=file_type)
            .first()
        )

        if existing and existing.content_hash == current_hash:
            return None  # no change

        if existing:
            existing.content_hash = current_hash
            existing.size_bytes = size_bytes
            existing.cloud_key = None  # needs re-upload
            existing.synced_at = None
            return existing
        else:
            manifest = FileSyncManifest(
                file_type=file_type,
                file_path=str(file_path),
                content_hash=current_hash,
                size_bytes=size_bytes,
            )
            db.add(manifest)
            return manifest
