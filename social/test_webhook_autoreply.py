import json
from django.test import Client, TestCase
from django.utils import timezone

from .models import (
    DMReplyTemplate,
    AutoReplyRule,
    WebhookEvent,
    DMMessage,
    Job,
    Platform,
    InstagramAccount,
)
from .services import auto_reply


class WebhookAutoReplyTests(TestCase):
    def setUp(self):
        self.client = Client()
        tmpl = DMReplyTemplate.objects.create(name='t', reply_text='hi')
        AutoReplyRule.objects.create(
            name='r',
            platform=Platform.INSTAGRAM,
            keywords='hello',
            delay_minutes=1,
            reply_template=tmpl,
        )

    def test_match_creates_job_with_delay(self):
        payload = {
            'entry': [
                {'messaging': [{'sender': {'id': 'u1'}, 'message': {'text': 'hello'}}]}
            ]
        }
        res = self.client.post('/webhook/instagram/', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(WebhookEvent.objects.count(), 1)
        self.assertEqual(DMMessage.objects.count(), 1)
        job = Job.objects.get()
        self.assertEqual(job.job_type, Job.Type.REPLY)
        self.assertGreater(job.run_at, timezone.now())

    def test_no_match_no_job(self):
        payload = {
            'entry': [
                {'messaging': [{'sender': {'id': 'u1'}, 'message': {'text': 'nomatch'}}]}
            ]
        }
        res = self.client.post('/webhook/instagram/', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Job.objects.count(), 0)

    def test_global_rule_matches_with_account(self):
        account = InstagramAccount.objects.create(
            display_name='acc', instagram_user_id='1', username='user'
        )
        rule = auto_reply.match_rules(Platform.INSTAGRAM, account, 'hello')
        self.assertIsNotNone(rule)
