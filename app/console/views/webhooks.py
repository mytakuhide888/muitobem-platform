# app/app/console/views/webhooks.py
import hmac, hashlib, json
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from ..utils import meta as metaapi

@csrf_exempt
def meta_webhook(request):
    # Verify (GET)
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge", "")
        if mode == "subscribe" and token == settings.META_WEBHOOK_VERIFY_TOKEN:
            return HttpResponse(challenge)
        return HttpResponse("Forbidden", status=403)

    # Delivery (POST)
    try:
        payload = json.loads(request.body or "{}")
    except Exception:
        payload = {}
    # ここでイベント種別ごとにキュー投入 or DB保存（既存の WebhookEvent に寄せてもOK）
    # ひとまず見える化のため200で返す
    return JsonResponse({"ok": True})
