# app/app/console/utils/meta.py
# -*- coding: utf-8 -*-
import os
import json
import hmac
import hashlib
import datetime as dt
from urllib.parse import urlencode

import requests
from django.conf import settings

# ===== 基本設定（settings優先 / なければ環境変数） =====
APP_ID = getattr(settings, "META_APP_ID", os.getenv("META_APP_ID", ""))
APP_SECRET = getattr(settings, "META_APP_SECRET", os.getenv("META_APP_SECRET", ""))
SITE_BASE = getattr(settings, "SITE_BASE", os.getenv("SITE_BASE", "")).rstrip("/")
VERIFY_TOKEN = getattr(settings, "META_WEBHOOK_VERIFY_TOKEN", os.getenv("META_WEBHOOK_VERIFY_TOKEN", "dev-verify-token"))
GRAPH_VER = getattr(settings, "META_GRAPH_VERSION", "v20.0")
GRAPH = f"https://graph.facebook.com/{GRAPH_VER}"

# ===== 安全系ユーティリティ =====
def _appsecret_proof(token: str) -> str:
    """appsecret_proof を作成"""
    return hmac.new(APP_SECRET.encode(), msg=token.encode(), digestmod=hashlib.sha256).hexdigest()

def _ensure_conf():
    if not APP_ID or not APP_SECRET:
        raise RuntimeError("META_APP_ID / META_APP_SECRET が未設定です")

# ===== 共通リクエスト（appsecret_proof自動付与） =====
def api_get(path: str, params=None, access_token: str | None = None):
    _ensure_conf()
    params = dict(params or {})
    if access_token:
        params["access_token"] = access_token
        params["appsecret_proof"] = _appsecret_proof(access_token)
    r = requests.get(f"{GRAPH}/{path.lstrip('/')}", params=params, timeout=15)
    r.raise_for_status()
    return r.json()

def api_post(path: str, data=None, access_token: str | None = None):
    _ensure_conf()
    data = dict(data or {})
    if access_token:
        data["access_token"] = access_token
        data["appsecret_proof"] = _appsecret_proof(access_token)
    r = requests.post(f"{GRAPH}/{path.lstrip('/')}", data=data, timeout=15)
    r.raise_for_status()
    return r.json()

# ===== OAuth URL 作成 =====
def oauth_url(scopes: list[str], state: str = "", redirect_uri: str | None = None) -> str:
    """
    Facebook OAuth の開始URLを返す。
    scopes はスペース区切りで渡すのが正しい（カンマでも一部通るが非推奨）。
    """
    _ensure_conf()
    # 既定のコールバック（/meta/oauth/callback/）。別パスを使いたければ引数で上書き。
    redirect_uri = redirect_uri or (f"{SITE_BASE}/meta/oauth/callback/" if SITE_BASE else "")
    # join時に万一カンマが混ざってもスペース区切りに寄せる
    scope_str = " ".join(s.strip() for s in scopes if s and s.strip())
    params = {
        "client_id": APP_ID,
        "redirect_uri": redirect_uri,
        "scope": scope_str,
        "response_type": "code",
        "state": state or "",
    }
    return f"https://www.facebook.com/{GRAPH_VER}/dialog/oauth?{urlencode(params)}"

# ===== code -> user access token =====
def exchange_code(code: str, redirect_uri: str | None = None):
    """
    code を user access token へ交換。
    戻り値: (token, user_id, scopes(list), expires_at(datetime|None))
    """
    _ensure_conf()
    redirect_uri = redirect_uri or (f"{SITE_BASE}/meta/oauth/callback/" if SITE_BASE else "")
    res = requests.get(
        f"{GRAPH}/oauth/access_token",
        params={
            "client_id": APP_ID,
            "client_secret": APP_SECRET,
            "redirect_uri": redirect_uri,
            "code": code,
        },
        timeout=15,
    )
    res.raise_for_status()
    j = res.json()
    token = j["access_token"]

    # token debugging
    dbg = requests.get(
        f"{GRAPH}/debug_token",
        params={"input_token": token, "access_token": f"{APP_ID}|{APP_SECRET}"},
        timeout=15,
    ).json()
    data = dbg.get("data", {}) or {}
    user_id = data.get("user_id")
    scopes = data.get("scopes", []) or []
    exp = data.get("expires_at")
    expires_at = dt.datetime.fromtimestamp(exp, tz=dt.timezone.utc) if exp else None
    return token, user_id, scopes, expires_at

# ===== ユーザー短期 -> 長期トークン交換 =====
def exchange_long_lived(user_token: str) -> dict:
    """
    戻り値: {access_token, token_type, expires_in}
    """
    _ensure_conf()
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "fb_exchange_token": user_token,
    }
    r = requests.get(f"{GRAPH}/oauth/access_token", params=params, timeout=15)
    r.raise_for_status()
    return r.json()

# ===== 権限 / ページ / IGBA 取得 =====
def me_permissions(token: str):
    """
    (granted, declined) を返す簡易版
    """
    r = api_get("me/permissions", access_token=token)
    items = r.get("data", []) or []
    granted = [i["permission"] for i in items if i.get("status") == "granted"]
    declined = [i["permission"] for i in items if i.get("status") != "granted"]
    return granted, declined

def me_accounts(token: str) -> dict:
    """所有ページ一覧（name,id,access_token,perms など）"""
    return api_get("me/accounts", params={"fields": "name,id,access_token,perms"}, access_token=token)

def list_pages(token: str):
    """後方互換：従来の返し（data配列）"""
    return me_accounts(token).get("data", [])

def page_ig_business(page_id: str, page_token: str):
    """ページに紐づく InstagramBusinessAccount を取得"""
    r = api_get(
        f"{page_id}",
        params={"fields": "instagram_business_account{id,username}"},
        access_token=page_token,
    )
    return r.get("instagram_business_account")

# エイリアス（後方互換）
page_to_ig = page_ig_business

# ===== Webhook購読作成（アプリ単位） =====
def subscribe_webhooks(callback_url: str, verify_token: str | None = None, *, objects=("instagram", "page")) -> dict:
    """
    /{app-id}/subscriptions に対して購読を作成/更新
    アクセストークンは app access token (app_id|app_secret) を使用
    """
    _ensure_conf()
    verify_token = verify_token or VERIFY_TOKEN
    app_token = f"{APP_ID}|{APP_SECRET}"
    fields_map = {
        "instagram": "comments,mentions,messages",
        "page": "feed,conversations",
    }
    results = {}
    for obj in objects:
        fields = fields_map.get(obj)
        if not fields:
            continue
        res = api_post(
            f"{APP_ID}/subscriptions",
            data={"object": obj, "callback_url": callback_url, "verify_token": verify_token, "fields": fields},
            access_token=app_token,
        )
        results[obj] = res
    return results

# ===== デバッグ補助 =====
def debug_token(token: str) -> dict:
    _ensure_conf()
    r = requests.get(
        f"{GRAPH}/debug_token",
        params={"input_token": token, "access_token": f"{APP_ID}|{APP_SECRET}"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()

__all__ = [
    "GRAPH", "oauth_url", "exchange_code", "exchange_long_lived",
    "me_permissions", "me_accounts", "list_pages", "page_ig_business", "page_to_ig",
    "api_get", "api_post", "subscribe_webhooks", "debug_token",
]
