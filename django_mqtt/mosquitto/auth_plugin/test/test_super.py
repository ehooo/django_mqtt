
from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse


class AdminTestCase(TestCase):
    def setUp(self):
        self.url_testing = reverse('django_mqtt:mqtt_superuser')
        self.client = Client()

    def test_user_good(self):
        username = 'user'
        User.objects.create_user(username)
        response = self.client.post(self.url_testing, {'username': username})
        self.assertEqual(response.status_code, 403)

    def test_user_wrong(self):
        response = self.client.post(self.url_testing, {'username': 'test'})
        self.assertEqual(response.status_code, 403)

    def test_user_admin(self):
        username = 'admin'
        User.objects.create_superuser(username, 'email@test.test', 'password')
        response = self.client.post(self.url_testing, {'username': username})
        self.assertEqual(response.status_code, 200)

    def test_user_admin_no_active(self):
        username = 'admin'
        user = User.objects.create_superuser(username, 'email@test.test', 'password')
        user.is_active = False
        user.save()
        response = self.client.post(self.url_testing, {'username': username})
        self.assertEqual(response.status_code, 403)
