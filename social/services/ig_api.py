"""Simplified Instagram Graph API wrapper.

All functions return the JSON body of the HTTP response and avoid any
side effects so that callers can decide how to persist data.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import requests
from django.conf import settings

BASE_URL = f"https://graph.facebook.com/{settings.DEFAULT_API_VERSION}"


def _post(path: str, params: Dict) -> Dict:
    url = f"{BASE_URL}/{path}"
    res = requests.post(url, data=params)
    res.raise_for_status()
    return res.json()


def _get(path: str, params: Dict) -> Dict:
    url = f"{BASE_URL}/{path}"
    res = requests.get(url, params=params)
    res.raise_for_status()
    return res.json()


def send_dm(access_token: str, recipient_id: str, text: str) -> Dict:
    params = {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
        "access_token": access_token,
    }
    return _post("me/messages", params)


def fetch_dms(access_token: str, since_ts: Optional[int] = None) -> Dict:
    params = {"access_token": access_token}
    if since_ts:
        params["since"] = since_ts
    return _get("me/conversations", params)


def fetch_comments(media_id: str, access_token: str) -> Dict:
    params = {"access_token": access_token, "fields": "id,text"}
    return _get(f"{media_id}/comments", params)


def reply_comment(comment_id: str, access_token: str, text: str) -> Dict:
    params = {"message": text, "access_token": access_token}
    return _post(f"{comment_id}/replies", params)


def hide_comment(comment_id: str, access_token: str, hide: bool) -> Dict:
    params = {"hidden": str(hide).lower(), "access_token": access_token}
    return _post(f"{comment_id}", params)


def create_media(ig_user_id: str, access_token: str, caption: str, **kwargs) -> Dict:
    params = {"caption": caption, "access_token": access_token}
    params.update(kwargs)
    return _post(f"{ig_user_id}/media", params)


def publish_media(creation_id: str, access_token: str) -> Dict:
    params = {"creation_id": creation_id, "access_token": access_token}
    return _post("me/media_publish", params)


def fetch_insights_ig_user(ig_user_id: str, access_token: str, metrics: List[str], period: str) -> Dict:
    params = {
        "metric": ",".join(metrics),
        "period": period,
        "access_token": access_token,
    }
    return _get(f"{ig_user_id}/insights", params)


def fetch_insights_media(media_id: str, access_token: str, metrics: List[str]) -> Dict:
    params = {"metric": ",".join(metrics), "access_token": access_token}
    return _get(f"{media_id}/insights", params)
