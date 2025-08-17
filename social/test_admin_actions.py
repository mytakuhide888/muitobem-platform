from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from .models import Job, Platform


class JobAdminActionsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser('admin', 'admin@example.com', 'pw')
        self.client = Client()
        self.client.login(username='admin', password='pw')

    def test_run_now_resend_reset(self):
        job = Job.objects.create(job_type=Job.Type.REPLY, platform=Platform.INSTAGRAM, run_at=timezone.now() + timezone.timedelta(hours=1))
        self.client.post('/admin/social/job/', {'action': 'run_now', '_selected_action': [job.pk]})
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.PENDING)
        self.assertLessEqual(job.run_at, timezone.now())

        job.status = Job.Status.DONE
        job.save()
        self.client.post('/admin/social/job/', {'action': 'resend', '_selected_action': [job.pk]})
        self.assertEqual(Job.objects.count(), 2)
        new_job = Job.objects.order_by('-pk').first()
        self.assertEqual(new_job.status, Job.Status.PENDING)

        failed = Job.objects.create(job_type=Job.Type.REPLY, platform=Platform.INSTAGRAM, run_at=timezone.now(), status=Job.Status.FAILED)
        self.client.post('/admin/social/job/', {'action': 'reset_failed', '_selected_action': [failed.pk]})
        failed.refresh_from_db()
        self.assertEqual(failed.status, Job.Status.PENDING)
