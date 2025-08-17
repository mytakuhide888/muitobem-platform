from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import WebhookEvent, Platform


class WebhookEventAdminTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser('admin', 'admin@example.com', 'pw')
        self.client = Client()
        self.client.login(username='admin', password='pw')

    def test_pretty_payload(self):
        ev = WebhookEvent.objects.create(platform=Platform.INSTAGRAM, field='messages', payload={'a': 1})
        url = reverse('admin:social_webhookevent_change', args=[ev.pk])
        res = self.client.get(url)
        self.assertContains(res, '<pre>')
        self.assertIn('"a": 1', res.content.decode())

    def test_compare_latest(self):
        WebhookEvent.objects.create(platform=Platform.INSTAGRAM, field='messages', payload={'a': 1})
        newer = WebhookEvent.objects.create(platform=Platform.INSTAGRAM, field='messages', payload={'a': 2})
        url = reverse('admin:social_webhookevent_compare', args=[newer.pk])
        res = self.client.get(url)
        self.assertContains(res, '<pre>')
        self.assertIn('-  "a": 1', res.content.decode())
