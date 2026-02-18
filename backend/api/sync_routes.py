"""
Sync API routes.

POST   /api/sync/setup          — Initialize encryption with passphrase
POST   /api/sync/initial-clone   — Full data download for new device
POST   /api/sync                 — Trigger immediate sync
GET    /api/sync/status          — Sync engine status
GET    /api/sync/devices         — List all devices in sync mesh
GET    /api/sync/changelog       — View recent changes (debug)
DELETE /api/sync/device/{id}     — Remove device
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from backend.storage.database import get_db_session
from backend.sync.engine import sync_engine
from backend.sync.models import ChangeLogEntry, Device

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sync", tags=["sync"])


# ── Request/Response Models ─────────────────────────────────────────────

class SetupRequest(BaseModel):
    passphrase: str


class SetupResponse(BaseModel):
    action: str
    key_id: Optional[str] = None


class SyncResponse(BaseModel):
    push: dict
    pull: dict


class StatusResponse(BaseModel):
    initialized: bool
    device_id: Optional[str] = None
    vault_unlocked: bool
    online: bool
    auto_sync_running: bool
    sync_interval_seconds: int


class DeviceOut(BaseModel):
    id: str
    name: str
    device_type: Optional[str] = None
    last_sync_at: Optional[str] = None
    is_current: bool


class ChangeLogOut(BaseModel):
    id: str
    hlc_timestamp: str
    device_id: str
    entity_table: str
    entity_id: str
    operation: str
    changed_fields: Optional[str] = None


# ── Routes ──────────────────────────────────────────────────────────────

@router.post("/setup", response_model=SetupResponse)
def setup_encryption(req: SetupRequest):
    """Initialize or unlock encryption vault."""
    if not sync_engine.is_initialized:
        sync_engine.initialize()
    try:
        result = sync_engine.setup_encryption(req.passphrase)
        return SetupResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/initial-clone")
def initial_clone(db: Session = Depends(get_db_session)):
    """Full data download for a new device joining the sync mesh."""
    if not sync_engine.is_initialized:
        raise HTTPException(status_code=400, detail="Sync engine not initialized")
    try:
        stats = sync_engine.initial_clone(db)
        return stats
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("", response_model=SyncResponse)
async def trigger_sync():
    """Trigger an immediate push+pull sync."""
    if not sync_engine.is_initialized:
        raise HTTPException(status_code=400, detail="Sync engine not initialized")
    try:
        result = await sync_engine.sync_now()
        return SyncResponse(**result)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status", response_model=StatusResponse)
def get_status():
    """Get current sync engine status."""
    return StatusResponse(**sync_engine.status())


@router.get("/devices", response_model=list[DeviceOut])
def list_devices(db: Session = Depends(get_db_session)):
    """List all devices in the sync mesh."""
    if not sync_engine.is_initialized:
        raise HTTPException(status_code=400, detail="Sync engine not initialized")
    devices = sync_engine.list_devices(db)
    return [DeviceOut(**d) for d in devices]


@router.get("/changelog", response_model=list[ChangeLogOut])
def get_changelog(
    limit: int = 50,
    entity_table: Optional[str] = None,
    db: Session = Depends(get_db_session),
):
    """View recent changelog entries (debug endpoint)."""
    query = db.query(ChangeLogEntry).order_by(ChangeLogEntry.hlc_timestamp.desc())
    if entity_table:
        query = query.filter(ChangeLogEntry.entity_table == entity_table)
    entries = query.limit(limit).all()
    return [
        ChangeLogOut(
            id=e.id,
            hlc_timestamp=e.hlc_timestamp,
            device_id=e.device_id,
            entity_table=e.entity_table,
            entity_id=e.entity_id,
            operation=e.operation.value if hasattr(e.operation, "value") else e.operation,
            changed_fields=e.changed_fields,
        )
        for e in entries
    ]


@router.delete("/device/{device_id}")
def remove_device(device_id: str, db: Session = Depends(get_db_session)):
    """Remove a device from the sync mesh."""
    if not sync_engine.is_initialized:
        raise HTTPException(status_code=400, detail="Sync engine not initialized")
    try:
        result = sync_engine.remove_device(db, device_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
