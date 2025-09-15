# -*- coding: utf-8 -*-
import json
from .dashboard import dashboard
from .health import connection_test
from .logs import logs_view
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.test import RequestFactory

def dashboard(request):
    return render(request, "admin/console/dashboard.html")

@staff_member_required
def integration(request):
    """
    連携中アカウントの一覧をざっくり表示（安全に文字列化）。
    失敗しても画面は落とさず、エラーを画面に出すだけにします。
    """
    ig_accounts = []
    th_accounts = []
    ig_err = th_err = None

    # Instagram Business Account
    try:
        from ig.models import InstagramBusinessAccount
        ig_accounts = list(InstagramBusinessAccount.objects.all()[:50])
    except Exception as e:
        ig_err = str(e)

    # Threads Account
    try:
        from th.models import ThreadsAccount
        th_accounts = list(ThreadsAccount.objects.all()[:50])
    except Exception as e:
        th_err = str(e)

    ctx = {
        "ig_accounts": ig_accounts,
        "th_accounts": th_accounts,
        "ig_err": ig_err,
        "th_err": th_err,
    }
    return render(request, "admin/console/integration.html", ctx)

@staff_member_required
def webhook_test(request):
    """
    Webhook受信の疎通テスト。
    サンプルJSONを /webhook/instagram/ または /webhook/threads/ に投げ、
    ステータスとレスポンスの一部を画面表示します。
    ※ 実装側で署名検証等が厳しい場合は 4xx でも“到達確認”として扱えます。
    """
    from django.test import Client

    # 画面の選択状態＆サンプルJSON
    target = request.POST.get("target") or "instagram"
    sample_instagram = (
        '{\n'
        '  "object": "instagram",\n'
        '  "entry": [\n'
        '    {"id": "1234567890", "changes": [{"field": "comments", "value": {"text": "hello"}}]}\n'
        '  ]\n'
        '}'
    )
    sample_threads = (
        '{\n'
        '  "object": "threads",\n'
        '  "entry": [\n'
        '    {"id": "9876543210", "changes": [{"field": "post", "value": {"text": "hi"}}]}\n'
        '  ]\n'
        '}'
    )
    payload_default = sample_instagram if target == "instagram" else sample_threads
    payload = request.POST.get("payload") or payload_default

    result = None
    error = None

    if request.method == "POST":
        try:
            client = Client()
            url = "/webhook/instagram/" if target == "instagram" else "/webhook/threads/"
            resp = client.post(url, data=payload, content_type="application/json")
            body = resp.content.decode("utf-8", errors="replace")
            result = {
                "url": url,
                "status": resp.status_code,
                "body": body[:2000],  # 表示は先頭2,000文字まで
            }
        except Exception as e:
            error = str(e)

    ctx = {
        "target": target,
        "payload": payload,
        "result": result,
        "error": error,
        "sample_instagram": sample_instagram,
        "sample_threads": sample_threads,
    }
    return render(request, "admin/console/webhook_test.html", ctx)

@staff_member_required
def logs(request):
    """
    指定ファイルの末尾を表示。?lines=, ?level=(ALL|ERROR|WARNING|INFO), ?download=1 をサポート。
    """
    import os, io, re, itertools

    path = request.GET.get("path") or "/app/deploy/app.log"
    try:
        lines = int(request.GET.get("lines", "500"))
    except ValueError:
        lines = 500

    level = (request.GET.get("level") or "ALL").upper()
    download = request.GET.get("download") == "1"

    text = ""
    exists = os.path.exists(path)
    if exists:
        # 高速 tail：末尾から読み出し
        def tail_lines(file_path, n=500, chunk_size=8192):
            with open(file_path, "rb") as f:
                f.seek(0, os.SEEK_END)
                end = f.tell()
                size = 0
                blocks = []
                while size < end and len(blocks) < 10000:  # 念のため上限
                    seek = max(end - size - chunk_size, 0)
                    f.seek(seek)
                    block = f.read(min(chunk_size, end - seek))
                    blocks.append(block)
                    size += len(block)
                    if blocks[-1].count(b"\n") >= n + 1:
                        break
                data = b"".join(reversed(blocks))
                return b"\n".join(data.splitlines()[-n:]).decode("utf-8", "ignore")
        text = tail_lines(path, lines)
    else:
        text = f"(ログファイルが見つかりません: {path})"

    # レベル絞り込み（簡易）
    if level in {"ERROR", "WARNING", "INFO"}:
        patt = re.compile(rf"\b{level}\b")
        filtered = [ln for ln in text.splitlines() if patt.search(ln)]
        text = "\n".join(filtered)

    if download:
        from django.http import HttpResponse
        resp = HttpResponse(text, content_type="text/plain; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="tail.log.txt"'
        return resp

    ctx = {
        "path": path,
        "lines": lines,
        "level": level,
        "text": text,
        "exists": exists,
    }
    return render(request, "admin/console/logs.html", ctx)
