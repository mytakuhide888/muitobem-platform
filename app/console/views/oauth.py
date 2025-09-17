# app/console/views/oauth.py
import json, secrets
from django.http import HttpResponseBadRequest, JsonResponse, HttpResponseRedirect
from django.views.decorators.http import require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.urls import reverse


from sns_core.models import MetaUserToken
from ig.models import InstagramBusinessAccount
# ThreadsAccount も必要になったら import
from ..utils import meta as metaapi

# 必要スコープ（最小セット）: 後述の P0-2 と共通辞書にしてもOK
SCOPES_MIN = [
    "public_profile",
    "email",
    "pages_show_list",
    "pages_manage_metadata",
    "instagram_basic",
    # 投稿系を使うなら:
    # "instagram_content_publish",
]

def _redirect_uri(request):
    return request.build_absolute_uri(reverse("console_public:meta_oauth_cb"))

@staff_member_required
def meta_oauth_start(request):
    scopes = ["pages_show_list","pages_read_engagement","pages_manage_metadata","pages_read_user_content",
              "instagram_basic","instagram_manage_comments","instagram_manage_messages"]
    url = metaapi.oauth_url(scopes, state="setup", redirect_uri=_redirect_uri(request))
    return redirect(url)

@staff_member_required
def meta_connect(request):
    state = secrets.token_urlsafe(24)
    request.session["meta_oauth_state"] = state
    url = metaapi.oauth_url(SCOPES_MIN, state)
    return HttpResponseRedirect(url)

@require_http_methods(["GET"])
def meta_callback(request):
    st = request.GET.get("state")
    if st != request.session.get("meta_oauth_state"):
        return HttpResponseBadRequest("state mismatch")
    code = request.GET.get("code")
    if not code:
        return HttpResponseBadRequest("no code")

    token, user_id, scopes, exp_at = metaapi.exchange_code(code)
    granted, declined = metaapi.me_permissions(token)

    # 保存
    MetaUserToken.objects.update_or_create(
        user_id=user_id,
        defaults=dict(
            access_token=token,
            expires_at=exp_at,
            granted_scopes=granted,
            declined_scopes=declined,
            created_by=request.user if request.user.is_authenticated else None,
        )
    )
    request.session["meta_user_id"] = user_id
    return redirect("console:accounts")  # 取り込み画面へ

@csrf_exempt
@require_POST
def meta_import(request):
    """
    Graph API の結果をそのまま POST して取り込む簡易エンドポイント。
    期待ペイロード例:
    {
      "granted": ["pages_show_list", "instagram_basic", ...],
      "declined": [],
      "expires_in": 5183945,               # 任意
      "pages": [                           # /me/accounts?fields=id,name,access_token,instagram_business_account{id}
        {
          "id": "PAGE_ID",
          "name": "ページ名",
          "access_token": "EAAB...",
          "instagram_business_account": {"id": "1784..."}
        },
        ...
      ]
    }

    ※ "pages" がなく "data" に同等配列が入るケースにも対応します。
    """
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except Exception as e:
        return JsonResponse({"ok": False, "error": f"invalid json: {e}"}, status=400)

    granted  = payload.get("granted") or []
    declined = payload.get("declined") or []

    # トークン有効期限をサーバ側で推定（任意）
    token_expires_at = None
    if payload.get("expires_in"):
        try:
            sec = int(payload["expires_in"])
            token_expires_at = timezone.now() + timezone.timedelta(seconds=sec)
        except Exception:
            token_expires_at = None

    pages = payload.get("pages") or payload.get("data") or []
    saved, errors = [], []

    # ここで IG アカウントを upsert
    try:
        from ig.models import InstagramBusinessAccount
    except Exception as e:
        return JsonResponse({"ok": False, "error": f"model import failed: {e}"}, status=500)

    for p in pages:
        try:
            fb_page_id = p.get("id") or p.get("page_id")
            page_token = p.get("access_token")
            igbiz = (p.get("instagram_business_account") or {})
            ig_business_id = (igbiz or {}).get("id")

            # IG の紐づきがないページはスキップ
            if not ig_business_id:
                continue

            obj, created = InstagramBusinessAccount.objects.get_or_create(
                ig_business_id=ig_business_id,
                defaults={"fb_page_id": fb_page_id or ""}
            )
            # 更新項目
            if fb_page_id:
                obj.fb_page_id = fb_page_id
            if page_token:
                obj.access_token = page_token
            if token_expires_at:
                obj.token_expires_at = token_expires_at
            obj.permissions = {"granted": granted, "declined": declined}
            obj.save()

            saved.append({
                "ig_business_id": ig_business_id,
                "fb_page_id": obj.fb_page_id,
                "created": created,
            })
        except Exception as e:
            errors.append({"page": p, "error": str(e)})

    return JsonResponse({"ok": True, "saved": saved, "errors": errors})