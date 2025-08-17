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
    ScheduledPost, WebhookEvent, DMMessage, AutoReplyRule, Job, Platform
)
from .services import ig_api, threads_api
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


def _schedule_auto_reply(platform: str, text: str):
    rules = AutoReplyRule.objects.filter(platform=platform, enabled=True)
    for rule in rules:
        keywords = [k.strip() for k in rule.keywords.split(',') if k.strip()]
        if any(k in text for k in keywords):
            run_at = timezone.now() + timedelta(minutes=rule.delay_minutes)
            Job.objects.create(
                job_type=Job.Type.REPLY,
                platform=platform,
                args={"text": rule.reply_template.reply_text},
                run_at=run_at,
            )


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
                _schedule_auto_reply(Platform.INSTAGRAM, dm.text)

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
    return JsonResponse({'status': 'ok'})
