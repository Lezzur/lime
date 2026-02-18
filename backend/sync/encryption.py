"""
LIME Zero-Knowledge Encryption Service.

All crypto uses AES-256-GCM with a wire format compatible with iOS CryptoKit:
    nonce(12) || ciphertext || tag(16)

File encryption uses LIME's own container format:
    magic(4) || version(1) || flags(1) || payload
"""

import base64
import json
import logging
import os
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from backend.config.settings import settings
from backend.sync.vault import vault

logger = logging.getLogger(__name__)

MAGIC = b"LIME"
FORMAT_VERSION = 1
FLAG_CHUNKED = 0x01


@dataclass
class EncryptedPayload:
    """Holds nonce + ciphertext (with appended GCM tag)."""

    nonce: bytes
    ciphertext: bytes  # ciphertext || tag

    def to_combined(self) -> bytes:
        """iOS CryptoKit AES.GCM.SealedBox.combined format."""
        return self.nonce + self.ciphertext

    @classmethod
    def from_combined(cls, data: bytes) -> "EncryptedPayload":
        nonce_len = settings.crypto_nonce_len
        if len(data) < nonce_len + settings.crypto_tag_len + 1:
            raise ValueError("Combined payload too short")
        return cls(nonce=data[:nonce_len], ciphertext=data[nonce_len:])

    def to_base64(self) -> str:
        return base64.b64encode(self.to_combined()).decode("ascii")

    @classmethod
    def from_base64(cls, b64: str) -> "EncryptedPayload":
        return cls.from_combined(base64.b64decode(b64))


class EncryptionService:
    """Singleton providing encrypt/decrypt operations backed by the Vault key."""

    _instance: Optional["EncryptionService"] = None

    def __new__(cls) -> "EncryptionService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ── Low-level ───────────────────────────────────────────────

    def encrypt(self, plaintext: bytes, aad: Optional[bytes] = None) -> EncryptedPayload:
        key = vault.get_key()
        nonce = os.urandom(settings.crypto_nonce_len)
        aesgcm = AESGCM(key)
        ct = aesgcm.encrypt(nonce, plaintext, aad)  # ct includes 16-byte tag
        return EncryptedPayload(nonce=nonce, ciphertext=ct)

    def decrypt(self, payload: EncryptedPayload, aad: Optional[bytes] = None) -> bytes:
        key = vault.get_key()
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(payload.nonce, payload.ciphertext, aad)

    # ── JSON helpers ────────────────────────────────────────────

    def encrypt_json(self, obj: Union[dict, list]) -> str:
        plaintext = json.dumps(obj, separators=(",", ":")).encode("utf-8")
        return self.encrypt(plaintext).to_base64()

    def decrypt_json(self, b64: str) -> Union[dict, list]:
        payload = EncryptedPayload.from_base64(b64)
        plaintext = self.decrypt(payload)
        return json.loads(plaintext)

    # ── Sync payload helpers ────────────────────────────────────

    def encrypt_sync_payload(self, data: dict) -> dict:
        encrypted = self.encrypt_json(data)
        return {
            "v": 1,
            "key_id": vault.key_id,
            "payload": encrypted,
        }

    def decrypt_sync_payload(self, envelope: dict) -> dict:
        if envelope.get("v") != 1:
            raise ValueError(f"Unsupported sync payload version: {envelope.get('v')}")
        return self.decrypt_json(envelope["payload"])

    # ── Chunked byte encryption (for sync batches) ────────────

    def encrypt_bytes(self, plaintext: bytes) -> bytes:
        """Encrypt raw bytes, return combined nonce+ciphertext."""
        payload = self.encrypt(plaintext)
        return payload.to_combined()

    def decrypt_bytes(self, data: bytes) -> bytes:
        """Decrypt combined nonce+ciphertext bytes."""
        payload = EncryptedPayload.from_combined(data)
        return self.decrypt(payload)

    # ── File encryption ─────────────────────────────────────────

    def encrypt_file(self, src: Path, dst: Path) -> None:
        file_size = src.stat().st_size
        chunk_size = settings.crypto_file_chunk_size

        if file_size <= chunk_size:
            self._encrypt_file_single(src, dst)
        else:
            self._encrypt_file_chunked(src, dst, chunk_size)

    def decrypt_file(self, src: Path, dst: Path) -> None:
        with open(src, "rb") as f:
            magic = f.read(4)
            if magic != MAGIC:
                raise ValueError("Not a LIME encrypted file")
            version = struct.unpack("B", f.read(1))[0]
            if version != FORMAT_VERSION:
                raise ValueError(f"Unsupported format version: {version}")
            flags = struct.unpack("B", f.read(1))[0]

            if flags & FLAG_CHUNKED:
                self._decrypt_file_chunked(f, dst)
            else:
                self._decrypt_file_single(f, dst)

    # ── File internals ──────────────────────────────────────────

    def _encrypt_file_single(self, src: Path, dst: Path) -> None:
        plaintext = src.read_bytes()
        payload = self.encrypt(plaintext)
        combined = payload.to_combined()

        with open(dst, "wb") as f:
            f.write(MAGIC)
            f.write(struct.pack("B", FORMAT_VERSION))
            f.write(struct.pack("B", 0))  # flags: single-shot
            f.write(struct.pack("<I", len(combined)))
            f.write(combined)

    def _decrypt_file_single(self, f, dst: Path) -> None:
        payload_len = struct.unpack("<I", f.read(4))[0]
        combined = f.read(payload_len)
        payload = EncryptedPayload.from_combined(combined)
        plaintext = self.decrypt(payload)
        dst.write_bytes(plaintext)

    def _encrypt_file_chunked(self, src: Path, dst: Path, chunk_size: int) -> None:
        with open(dst, "wb") as out:
            out.write(MAGIC)
            out.write(struct.pack("B", FORMAT_VERSION))
            out.write(struct.pack("B", FLAG_CHUNKED))

            chunk_index = 0
            with open(src, "rb") as inp:
                while True:
                    chunk = inp.read(chunk_size)
                    if not chunk:
                        break
                    # AAD includes chunk index to prevent reordering
                    aad = struct.pack("<I", chunk_index)
                    payload = self.encrypt(chunk, aad=aad)
                    combined = payload.to_combined()

                    out.write(struct.pack("<I", len(combined)))
                    out.write(combined)
                    chunk_index += 1

            # Sentinel: zero-length chunk marks end
            out.write(struct.pack("<I", 0))

    def _decrypt_file_chunked(self, f, dst: Path) -> None:
        chunk_index = 0
        with open(dst, "wb") as out:
            while True:
                raw_len = f.read(4)
                if len(raw_len) < 4:
                    break
                payload_len = struct.unpack("<I", raw_len)[0]
                if payload_len == 0:
                    break  # sentinel
                combined = f.read(payload_len)
                aad = struct.pack("<I", chunk_index)
                payload = EncryptedPayload.from_combined(combined)
                plaintext = self.decrypt(payload, aad=aad)
                out.write(plaintext)
                chunk_index += 1


encryption_service = EncryptionService()
