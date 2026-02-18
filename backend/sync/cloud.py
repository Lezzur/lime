"""
S3-compatible storage client for the sync engine.

Bucket layout:
  {user_id}/dek.enc                          — encrypted DEK
  {user_id}/changelog/{device_id}/{batch}.enc — encrypted changelog batches
  {user_id}/files/{hash}.enc                  — content-addressed encrypted files
  {user_id}/manifest.enc                      — encrypted file manifest
"""

import logging
from pathlib import Path
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from backend.config.settings import settings

logger = logging.getLogger(__name__)


class SyncCloudClient:
    """S3-compatible storage client for sync operations."""

    def __init__(self):
        self._client = None
        self._bucket = settings.sync_s3_bucket
        self._user_id = settings.sync_user_id

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=settings.sync_s3_endpoint_url,
                aws_access_key_id=settings.sync_s3_access_key,
                aws_secret_access_key=settings.sync_s3_secret_key,
                region_name=settings.sync_s3_region,
                config=Config(signature_version="s3v4"),
            )
        return self._client

    def _key(self, *parts: str) -> str:
        return f"{self._user_id}/{'/'.join(parts)}"

    # ── DEK Storage ─────────────────────────────────────────────────

    def upload_dek(self, encrypted_dek: bytes) -> None:
        key = self._key("dek.enc")
        self.client.put_object(Bucket=self._bucket, Key=key, Body=encrypted_dek)
        logger.info("Uploaded encrypted DEK to %s", key)

    def download_dek(self) -> Optional[bytes]:
        key = self._key("dek.enc")
        try:
            resp = self.client.get_object(Bucket=self._bucket, Key=key)
            return resp["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise

    def dek_exists(self) -> bool:
        key = self._key("dek.enc")
        try:
            self.client.head_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError:
            return False

    # ── Changelog Batches ───────────────────────────────────────────

    def upload_changelog_batch(self, device_id: str, batch_id: str, data: bytes) -> None:
        key = self._key("changelog", device_id, f"{batch_id}.enc")
        self.client.put_object(Bucket=self._bucket, Key=key, Body=data)
        logger.debug("Uploaded changelog batch %s/%s", device_id, batch_id)

    def list_changelog_batches(self, device_id: str) -> list[str]:
        """List all batch IDs for a device, sorted by name."""
        prefix = self._key("changelog", device_id) + "/"
        batches = []
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                # Extract batch ID from key
                batch_file = obj["Key"].split("/")[-1]
                batch_id = batch_file.replace(".enc", "")
                batches.append(batch_id)
        return sorted(batches)

    def download_changelog_batch(self, device_id: str, batch_id: str) -> bytes:
        key = self._key("changelog", device_id, f"{batch_id}.enc")
        resp = self.client.get_object(Bucket=self._bucket, Key=key)
        return resp["Body"].read()

    # ── Content-Addressed File Storage ─────────────────────────────

    def upload_file(self, content_hash: str, data: bytes) -> None:
        key = self._key("files", f"{content_hash}.enc")
        # Skip if already exists (content-addressed deduplication)
        try:
            self.client.head_object(Bucket=self._bucket, Key=key)
            logger.debug("File %s already exists, skipping upload", content_hash)
            return
        except ClientError:
            pass
        self.client.put_object(Bucket=self._bucket, Key=key, Body=data)
        logger.debug("Uploaded file %s", content_hash)

    def download_file(self, content_hash: str) -> bytes:
        key = self._key("files", f"{content_hash}.enc")
        resp = self.client.get_object(Bucket=self._bucket, Key=key)
        return resp["Body"].read()

    def file_exists(self, content_hash: str) -> bool:
        key = self._key("files", f"{content_hash}.enc")
        try:
            self.client.head_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError:
            return False

    # ── Manifest ────────────────────────────────────────────────────

    def upload_manifest(self, data: bytes) -> None:
        key = self._key("manifest.enc")
        self.client.put_object(Bucket=self._bucket, Key=key, Body=data)

    def download_manifest(self) -> Optional[bytes]:
        key = self._key("manifest.enc")
        try:
            resp = self.client.get_object(Bucket=self._bucket, Key=key)
            return resp["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise

    # ── Device Discovery ────────────────────────────────────────────

    def list_devices(self) -> list[str]:
        """List device IDs that have pushed changelog batches."""
        prefix = self._key("changelog") + "/"
        devices = set()
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix, Delimiter="/"):
            for cp in page.get("CommonPrefixes", []):
                # Extract device_id from prefix path
                device_id = cp["Prefix"].rstrip("/").split("/")[-1]
                devices.add(device_id)
        return sorted(devices)

    # ── Cleanup ─────────────────────────────────────────────────────

    def delete_device_data(self, device_id: str) -> int:
        """Delete all changelog batches for a device. Returns count deleted."""
        prefix = self._key("changelog", device_id) + "/"
        deleted = 0
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            objects = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
            if objects:
                self.client.delete_objects(
                    Bucket=self._bucket,
                    Delete={"Objects": objects},
                )
                deleted += len(objects)
        logger.info("Deleted %d objects for device %s", deleted, device_id)
        return deleted

    def ensure_bucket(self) -> None:
        """Create the sync bucket if it doesn't exist."""
        try:
            self.client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self.client.create_bucket(Bucket=self._bucket)
            logger.info("Created sync bucket: %s", self._bucket)
