"""
Push notification subscription management and sender.
Stores web push subscriptions and fires notifications after meeting processing.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# Persist subscriptions to a local JSON file so they survive restarts
_SUBS_FILE = Path("data/push_subscriptions.json")
_subscriptions: dict[str, dict] = {}


def _load_subs():
    global _subscriptions
    if _SUBS_FILE.exists():
        try:
            _subscriptions = json.loads(_SUBS_FILE.read_text())
        except Exception:
            _subscriptions = {}


def _save_subs():
    _SUBS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SUBS_FILE.write_text(json.dumps(_subscriptions, indent=2))


_load_subs()


@router.post("/push/subscribe")
def subscribe(sub: dict):
    """Register a Web Push subscription from the web app."""
    endpoint = sub.get("endpoint")
    if not endpoint:
        from fastapi import HTTPException
        raise HTTPException(400, "Missing endpoint")
    _subscriptions[endpoint] = sub
    _save_subs()
    logger.info(f"Push subscription registered: {endpoint[:40]}…")
    return {"status": "subscribed", "count": len(_subscriptions)}


@router.delete("/push/subscribe")
def unsubscribe(payload: dict):
    """Remove a Web Push subscription."""
    endpoint = payload.get("endpoint", "")
    _subscriptions.pop(endpoint, None)
    _save_subs()
    return {"status": "unsubscribed"}


@router.get("/push/subscriptions")
def list_subscriptions():
    return {"count": len(_subscriptions)}


def send_push_notification(
    title: str,
    body: str,
    meeting_id: Optional[str] = None,
    tag: str = "lime-meeting",
):
    """Send a Web Push notification to all registered subscribers."""
    if not _subscriptions:
        return

    try:
        import pywebpush
    except ImportError:
        logger.warning("pywebpush not installed — skipping push notification")
        return

    from backend.config.settings import settings

    vapid_private = settings.vapid_private_key
    vapid_claims = {"sub": settings.vapid_mailto or "mailto:admin@localhost"}

    if not vapid_private:
        logger.warning("VAPID_PRIVATE_KEY not set — skipping push notification")
        return

    payload = json.dumps({
        "title": title,
        "body": body,
        "tag": tag,
        **({"meeting_id": meeting_id} if meeting_id else {}),
    })

    dead_endpoints = []
    for endpoint, sub in list(_subscriptions.items()):
        try:
            pywebpush.webpush(
                subscription_info=sub,
                data=payload,
                vapid_private_key=vapid_private,
                vapid_claims=vapid_claims,
            )
            logger.debug(f"Push sent to {endpoint[:40]}…")
        except pywebpush.WebPushException as e:
            if e.response and e.response.status_code in (404, 410):
                dead_endpoints.append(endpoint)
            else:
                logger.warning(f"Push failed: {e}")

    for ep in dead_endpoints:
        _subscriptions.pop(ep, None)
    if dead_endpoints:
        _save_subs()
