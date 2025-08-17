import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from django.conf import settings

from .models import (
    ScheduledPost, WebhookEvent, DMMessage, Platform
)
from .services import ig_api, threads_api, auto_reply
from .services.post_importer import full_import, sync_latest


@staff_member_required
@require_POST
def import_posts(request):
    count = full_import()
    messages.success(request, f'{count}件取り込みました。')
    return redirect('admin:social_post_changelist')


@staff_member_required
@require_POST
def sync_posts(request):
    count = sync_latest()
    messages.success(request, f'{count}件同期しました。')
    return redirect('admin:social_post_changelist')


@staff_member_required
@require_POST
def approve_scheduled(request, pk):
    obj = get_object_or_404(ScheduledPost, pk=pk)
    if obj.status == ScheduledPost.Status.DRAFT:
        obj.status = ScheduledPost.Status.APPROVED
        obj.save()
        messages.success(request, '承認しました。')
    return redirect('admin:social_scheduledpost_change', pk)


# --------------------------------------------------------------
# Webhook handlers
# --------------------------------------------------------------

def is_within_24h(sent_at):
    return timezone.now() - sent_at <= timedelta(hours=24)


@csrf_exempt
def webhook_instagram(request):
    if request.method == 'GET':
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        if token == settings.VERIFY_TOKEN_IG:
            return HttpResponse(challenge or '')
        return HttpResponse('forbidden', status=403)

    payload = json.loads(request.body.decode('utf-8') or '{}')
    WebhookEvent.objects.create(platform=Platform.INSTAGRAM, field='', payload=payload)

    # very small subset for tests
    entries = payload.get('entry', [])
    for entry in entries:
        # New style payload: entry -> changes[] -> value.messages[]
        changes = entry.get('changes', [])
        for change in changes:
            if change.get('field') != 'messages':
                continue
            for msg in change.get('value', {}).get('messages', []):
                text = msg.get('text', '')
                user_id = msg.get('from', {}).get('id', '')
                dm = DMMessage.objects.create(
                    platform=Platform.INSTAGRAM,
                    user_id=user_id,
                    text=text,
                    sent_at=timezone.now(),
                    raw_json=msg,
                )
                if is_within_24h(dm.sent_at):
                    rule = auto_reply.match_rules(Platform.INSTAGRAM, dm.account, dm.text)
                    if rule:
                        auto_reply.build_reply_job(dm.account, rule, dm)

        # Fallback for legacy "messaging" format used in tests
        for msg in entry.get('messaging', []):
            message = msg.get('message')
            if not message:
                continue
            text = message.get('text', '')
            user_id = msg.get('sender', {}).get('id', '')
            dm = DMMessage.objects.create(
                platform=Platform.INSTAGRAM,
                user_id=user_id,
                text=text,
                sent_at=timezone.now(),
                raw_json=msg,
            )
            if is_within_24h(dm.sent_at):
                rule = auto_reply.match_rules(Platform.INSTAGRAM, dm.account, dm.text)
                if rule:
                    auto_reply.build_reply_job(dm.account, rule, dm)

    return JsonResponse({'status': 'ok'})


@csrf_exempt
def webhook_threads(request):
    if request.method == 'GET':
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        if token == settings.VERIFY_TOKEN_TH:
            return HttpResponse(challenge or '')
        return HttpResponse('forbidden', status=403)

    payload = json.loads(request.body.decode('utf-8') or '{}')
    WebhookEvent.objects.create(platform=Platform.THREADS, field='', payload=payload)

    entries = payload.get('entry', [])
    for entry in entries:
        for change in entry.get('changes', []):
            field = change.get('field')
            if field not in {'replies', 'messages', 'mentions'}:
                continue
            value = change.get('value', {})
            text = value.get('text', '')
            user_id = value.get('from', '') or value.get('user_id', '')
            dm = DMMessage.objects.create(
                platform=Platform.THREADS,
                user_id=user_id,
                text=text,
                sent_at=timezone.now(),
                raw_json=value,
            )
            if is_within_24h(dm.sent_at):
                rule = auto_reply.match_rules(Platform.THREADS, dm.account, dm.text)
                if rule:
                    auto_reply.build_reply_job(dm.account, rule, dm)
    return JsonResponse({'status': 'ok'})
