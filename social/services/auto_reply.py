from __future__ import annotations

import re
from datetime import time
from typing import Optional

from django.utils import timezone

from ..models import AutoReplyRule, DMMessage, Job, Platform


def _time_in_range(start: time | None, end: time | None, now: time) -> bool:
    if start is None and end is None:
        return True
    if start is None:
        start = time(0, 0)
    if end is None:
        end = time(23, 59, 59)
    if start <= end:
        return start <= now <= end
    # over midnight
    return now >= start or now <= end


def match_rules(platform: str, account, text: str) -> Optional[AutoReplyRule]:
    qs = AutoReplyRule.objects.filter(platform=platform, enabled=True)
    if account:
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(account)
        qs = qs.filter(content_type=ct, object_id=account.pk)
    now = timezone.localtime().time()
    for rule in qs.order_by('id'):
        if not _time_in_range(rule.active_from, rule.active_to, now):
            continue
        if rule.use_regex:
            if re.search(rule.keywords, text):
                return rule
        else:
            keywords = [k.strip() for k in rule.keywords.split(',') if k.strip()]
            if any(k in text for k in keywords):
                return rule
    return None


def build_reply_job(account, rule: AutoReplyRule, message: DMMessage) -> Job:
    from django.utils import timezone
    run_at = timezone.now() + timezone.timedelta(minutes=rule.delay_minutes)
    job = Job(
        job_type=Job.Type.REPLY,
        platform=rule.platform,
        account=account,
        run_at=run_at,
        args={
            'template_id': rule.reply_template_id,
            'to': message.user_id,
            'context': {'message_id': message.pk, 'text': message.text},
        },
    )
    job.save()
    return job
