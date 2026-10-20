"""
Fire-and-forget helper that notifies the Express server of Django-side events.
Uses a short timeout so a slow/down Express service never blocks Django views.
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def notify_express(event, payload):
    """POST a notification to the Express server."""
    try:
        requests.post(
            f"{settings.EXPRESS_URL}/internal/notify",
            json={"event": event, "data": payload},
            headers={"X-API-Key": settings.EXPRESS_API_KEY},
            timeout=2,
        )
    except requests.RequestException as exc:
        # Never raise — notification failure shouldn't break the user's action.
        logger.warning("Failed to notify Express of %r: %s", event, exc)