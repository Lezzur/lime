"""
LIME Crypto REST API — Zero-knowledge vault management endpoints.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.sync.vault import vault

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/crypto", tags=["crypto"])


# ── Request / Response models ──────────────────────────────────

class PassphraseRequest(BaseModel):
    passphrase: str = Field(..., min_length=1)


class ChangePassphraseRequest(BaseModel):
    current_passphrase: str = Field(..., min_length=1)
    new_passphrase: str = Field(..., min_length=1)


class SetupResponse(BaseModel):
    key_id: str


class UnlockResponse(BaseModel):
    key_id: str


class ChangePassphraseResponse(BaseModel):
    key_id: str
    previous_key_id: str


class VerifyResponse(BaseModel):
    valid: bool


class StatusResponse(BaseModel):
    initialized: bool
    unlocked: bool
    key_id: str | None
    timeout_minutes: int


# ── Endpoints ──────────────────────────────────────────────────

@router.post("/setup", response_model=SetupResponse)
def crypto_setup(req: PassphraseRequest):
    """Initialize the vault with a passphrase (one-time operation)."""
    try:
        result = vault.setup(req.passphrase)
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return result


@router.post("/unlock", response_model=UnlockResponse)
def crypto_unlock(req: PassphraseRequest):
    """Derive key from passphrase, verify, and hold in memory."""
    if not vault.is_initialized:
        raise HTTPException(status_code=400, detail="Vault not initialized")
    try:
        result = vault.unlock(req.passphrase)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid passphrase")
    return result


@router.post("/lock")
def crypto_lock():
    """Clear the session key from memory."""
    vault.lock()
    return {"status": "locked"}


@router.post("/change-passphrase", response_model=ChangePassphraseResponse)
def crypto_change_passphrase(req: ChangePassphraseRequest):
    """Re-derive key with a new passphrase. Generates new salt and key_id."""
    if not vault.is_initialized:
        raise HTTPException(status_code=400, detail="Vault not initialized")
    try:
        result = vault.change_passphrase(req.current_passphrase, req.new_passphrase)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid current passphrase")
    return result


@router.post("/verify", response_model=VerifyResponse)
def crypto_verify(req: PassphraseRequest):
    """Check whether the passphrase is correct without unlocking."""
    if not vault.is_initialized:
        raise HTTPException(status_code=400, detail="Vault not initialized")
    return {"valid": vault.verify(req.passphrase)}


@router.get("/status", response_model=StatusResponse)
def crypto_status():
    """Return vault initialisation and unlock state."""
    return vault.status()
