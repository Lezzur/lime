"""
SQLAlchemy models for the sync engine.

- Device: identity of each device in the sync mesh
- ChangeLogEntry: per-row change tracking with HLC timestamps
- SyncState: per-remote-device sync cursors
- FileSyncManifest: tracks non-SQL file sync state
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text,
    DateTime, Index, Enum as SAEnum,
)
from sqlalchemy.sql import func
import enum
import uuid

from backend.storage.database import Base


def _gen_id() -> str:
    return str(uuid.uuid4())


class DeviceType(str, enum.Enum):
    desktop = "desktop"
    phone = "phone"
    tablet = "tablet"


class ChangeOperation(str, enum.Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class Device(Base):
    __tablename__ = "sync_devices"

    id = Column(String, primary_key=True, default=_gen_id)
    name = Column(String, nullable=False)
    device_type = Column(SAEnum(DeviceType), default=DeviceType.desktop)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    is_current = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ChangeLogEntry(Base):
    __tablename__ = "sync_changelog"
    __table_args__ = (
        Index("ix_changelog_entity_hlc", "entity_table", "entity_id", "hlc_timestamp"),
        Index("ix_changelog_hlc", "hlc_timestamp"),
    )

    id = Column(String, primary_key=True, default=_gen_id)
    hlc_timestamp = Column(String, nullable=False)
    device_id = Column(String, nullable=False)
    entity_table = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    operation = Column(SAEnum(ChangeOperation), nullable=False)
    changed_fields = Column(Text, nullable=True)  # JSON: {"field": new_value}
    base_version = Column(String, nullable=True)   # HLC of the version this change is based on
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SyncState(Base):
    __tablename__ = "sync_state"

    id = Column(String, primary_key=True, default=_gen_id)
    remote_device_id = Column(String, nullable=False, unique=True)
    last_pulled_hlc = Column(String, nullable=True)
    last_pushed_hlc = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class FileSyncManifest(Base):
    __tablename__ = "sync_file_manifest"

    id = Column(String, primary_key=True, default=_gen_id)
    file_type = Column(String, nullable=False)    # "audio", "knowledge_graph", "memory"
    file_path = Column(String, nullable=False)
    content_hash = Column(String, nullable=False)  # SHA-256
    size_bytes = Column(Integer, nullable=False, default=0)
    cloud_key = Column(String, nullable=True)      # S3 object key
    synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
