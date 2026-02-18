"""
LIME Zero-Knowledge Vault — Key derivation and session management.

The server never stores or transmits the user's passphrase or derived key.
vault.json holds only a random salt and an encrypted verification token.
"""

import hashlib
import hmac
import json
import logging
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

from argon2.low_level import Type, hash_secret_raw

from backend.config.settings import settings

logger = logging.getLogger(__name__)

VERIFICATION_PLAINTEXT = b"LIME-vault-verification-token-v1"


class Vault:
    """Manages passphrase-derived key lifecycle (singleton)."""

    _instance: Optional["Vault"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "Vault":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._session_key: Optional[bytearray] = None
        self._key_id: Optional[str] = None
        self._unlocked_at: Optional[float] = None
        self._op_lock = threading.Lock()
        self._vault_path: Path = settings.crypto_vault_path

    # ── Public API ──────────────────────────────────────────────

    @property
    def is_initialized(self) -> bool:
        return self._vault_path.exists()

    @property
    def is_unlocked(self) -> bool:
        if self._session_key is None:
            return False
        if self._is_session_expired():
            self.lock()
            return False
        return True

    @property
    def key_id(self) -> Optional[str]:
        return self._key_id

    @property
    def session_timeout_minutes(self) -> int:
        return settings.crypto_session_timeout_minutes

    def get_key(self) -> bytes:
        """Return a *copy* of the session key. Raises if locked."""
        with self._op_lock:
            if not self.is_unlocked:
                raise RuntimeError("Vault is locked")
            self._unlocked_at = time.monotonic()  # touch
            return bytes(self._session_key)

    # ── Setup ───────────────────────────────────────────────────

    def setup(self, passphrase: str) -> dict:
        """First-time vault initialisation. Raises if already initialised."""
        with self._op_lock:
            if self.is_initialized:
                raise RuntimeError("Vault already initialized")

            salt = os.urandom(settings.argon2_salt_len)
            key_id = uuid.uuid4().hex
            derived = self._derive_key(passphrase, salt)

            verification_token = self._create_verification_token(derived)

            vault_data = {
                "version": 1,
                "salt": salt.hex(),
                "key_id": key_id,
                "verification_token": verification_token.hex(),
            }
            self._vault_path.write_text(json.dumps(vault_data, indent=2))

            self._set_session_key(derived, key_id)
            logger.info("Vault initialized (key_id=%s)", key_id)
            return {"key_id": key_id}

    # ── Unlock / Lock ───────────────────────────────────────────

    def unlock(self, passphrase: str) -> dict:
        with self._op_lock:
            vault_data = self._read_vault()
            salt = bytes.fromhex(vault_data["salt"])
            derived = self._derive_key(passphrase, salt)

            stored_token = bytes.fromhex(vault_data["verification_token"])
            if not self._verify_token(derived, stored_token):
                raise ValueError("Invalid passphrase")

            self._set_session_key(derived, vault_data["key_id"])
            logger.info("Vault unlocked (key_id=%s)", vault_data["key_id"])
            return {"key_id": vault_data["key_id"]}

    def lock(self) -> None:
        with self._op_lock:
            self._wipe_session_key()
            logger.info("Vault locked")

    # ── Verify (stateless) ──────────────────────────────────────

    def verify(self, passphrase: str) -> bool:
        with self._op_lock:
            vault_data = self._read_vault()
            salt = bytes.fromhex(vault_data["salt"])
            derived = self._derive_key(passphrase, salt)

            stored_token = bytes.fromhex(vault_data["verification_token"])
            result = self._verify_token(derived, stored_token)
            # Wipe the derived key — verify is stateless
            self._wipe(bytearray(derived))
            return result

    # ── Change Passphrase ───────────────────────────────────────

    def change_passphrase(self, current_passphrase: str, new_passphrase: str) -> dict:
        with self._op_lock:
            vault_data = self._read_vault()
            old_salt = bytes.fromhex(vault_data["salt"])
            old_derived = self._derive_key(current_passphrase, old_salt)

            stored_token = bytes.fromhex(vault_data["verification_token"])
            if not self._verify_token(old_derived, stored_token):
                self._wipe(bytearray(old_derived))
                raise ValueError("Invalid current passphrase")

            old_key_id = vault_data["key_id"]
            self._wipe(bytearray(old_derived))

            new_salt = os.urandom(settings.argon2_salt_len)
            new_key_id = uuid.uuid4().hex
            new_derived = self._derive_key(new_passphrase, new_salt)

            verification_token = self._create_verification_token(new_derived)

            vault_data = {
                "version": 1,
                "salt": new_salt.hex(),
                "key_id": new_key_id,
                "verification_token": verification_token.hex(),
                "previous_key_id": old_key_id,
            }
            self._vault_path.write_text(json.dumps(vault_data, indent=2))

            self._set_session_key(new_derived, new_key_id)
            logger.info(
                "Passphrase changed (old_key=%s → new_key=%s)", old_key_id, new_key_id
            )
            return {"key_id": new_key_id, "previous_key_id": old_key_id}

    # ── Status ──────────────────────────────────────────────────

    def status(self) -> dict:
        return {
            "initialized": self.is_initialized,
            "unlocked": self.is_unlocked,
            "key_id": self._key_id,
            "timeout_minutes": settings.crypto_session_timeout_minutes,
        }

    # ── Internal ────────────────────────────────────────────────

    def _derive_key(self, passphrase: str, salt: bytes) -> bytes:
        return hash_secret_raw(
            secret=passphrase.encode("utf-8"),
            salt=salt,
            time_cost=settings.argon2_time_cost,
            memory_cost=settings.argon2_memory_cost,
            parallelism=settings.argon2_parallelism,
            hash_len=settings.argon2_hash_len,
            type=Type.ID,
        )

    def _create_verification_token(self, key: bytes) -> bytes:
        return hmac.new(key, VERIFICATION_PLAINTEXT, hashlib.sha256).digest()

    def _verify_token(self, key: bytes, stored_token: bytes) -> bool:
        expected = hmac.new(key, VERIFICATION_PLAINTEXT, hashlib.sha256).digest()
        return hmac.compare_digest(expected, stored_token)

    def _read_vault(self) -> dict:
        if not self.is_initialized:
            raise RuntimeError("Vault not initialized")
        return json.loads(self._vault_path.read_text())

    def _set_session_key(self, key: bytes, key_id: str) -> None:
        self._wipe_session_key()
        self._session_key = bytearray(key)
        self._key_id = key_id
        self._unlocked_at = time.monotonic()

    def _wipe_session_key(self) -> None:
        if self._session_key is not None:
            self._wipe(self._session_key)
            self._session_key = None
        self._key_id = None
        self._unlocked_at = None

    @staticmethod
    def _wipe(buf: bytearray) -> None:
        for i in range(len(buf)):
            buf[i] = 0

    def _is_session_expired(self) -> bool:
        if self._unlocked_at is None:
            return True
        elapsed = time.monotonic() - self._unlocked_at
        return elapsed > (settings.crypto_session_timeout_minutes * 60)


vault = Vault()
