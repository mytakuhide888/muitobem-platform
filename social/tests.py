from django.test import SimpleTestCase, Client


class AdminSmokeTest(SimpleTestCase):
    def test_admin_login_page(self):
        client = Client()
        res = client.get('/admin/login/')
        self.assertEqual(res.status_code, 200)
