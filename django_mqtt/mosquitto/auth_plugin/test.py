
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.core.urlresolvers import reverse
from django.conf import settings

from django_mqtt.mosquitto.auth_plugin import models


class AuthTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        User.objects.create_user('test', 'test@test.com', 'test')
        User.objects.create_superuser('admin', 'admin@test.com', 'admin')
        self.url_testing = reverse('mqtt_auth')
        self.client = Client()

    def test_login(self):
        response = self.client.post(self.url_testing, {'username': 'test', 'password': 'test'})
        self.assertEqual(response.status_code, 200)
        response = self.client.post(self.url_testing, {'username': 'admin', 'password': 'admin'})
        self.assertEqual(response.status_code, 200)

    def test_wrong_login(self):
        response = self.client.post(self.url_testing, {'username': 'test', 'password': 'wrong'})
        self.assertEqual(response.status_code, 403)
        response = self.client.post(self.url_testing, {'username': 'admin', 'password': 'wrong'})
        self.assertEqual(response.status_code, 403)
        response = self.client.post(self.url_testing, {'username': 'asdf', 'password': 'wrong'})
        self.assertEqual(response.status_code, 403)

    def test_wrong_params(self):
        response = self.client.post(self.url_testing, {'username': 'test'})
        self.assertEqual(response.status_code, 403)
        response = self.client.post(self.url_testing, {'password': 'test'})
        self.assertEqual(response.status_code, 403)
        response = self.client.post(self.url_testing, {})
        self.assertEqual(response.status_code, 403)


class AdminTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        User.objects.create_user('test', 'test@test.com', 'test')
        User.objects.create_superuser('admin', 'admin@test.com', 'admin')
        self.url_testing = reverse('mqtt_superuser')
        self.client = Client()

    def test_user_publisher(self):
        response = self.client.post(self.url_testing, {'username': 'test'})
        self.assertEqual(response.status_code, 403)

    def test_no_user_publisher(self):
        response = self.client.post(self.url_testing, {'username': 'asdf'})
        self.assertEqual(response.status_code, 403)

    def test_superadmin_publisher(self):
        response = self.client.post(self.url_testing, {'username': 'admin'})
        self.assertEqual(response.status_code, 200)


class AclTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        User.objects.create_user('test', 'test@test.com', 'test')
        user_login = User.objects.get(username='test')
        User.objects.create_superuser('admin', 'admin@test.com', 'admin')
        self.topic_public_publish = '/test/publisher/allow'
        self.topic_forbidden_publish = '/test/publisher/disallow'
        self.topic_private_publish = '/test/subscriber/login'
        self.topic_public_subs = '/test/subscriber/allow'
        self.topic_forbidden_subs = '/test/subscriber/disallow'
        self.topic_private_subs = '/test/subscriber/login'
        models.MQTT_ACL.objects.create(
            allow=True, topic=self.topic_public_publish,
            acc=models.PROTO_MQTT_ACC_PUB, user=None)
        models.MQTT_ACL.objects.create(
            allow=False, topic=self.topic_forbidden_publish,
            acc=models.PROTO_MQTT_ACC_PUB, user=None)
        models.MQTT_ACL.objects.create(
            allow=True, topic=self.topic_private_publish,
            acc=models.PROTO_MQTT_ACC_PUB, user=user_login)
        models.MQTT_ACL.objects.create(
            allow=True, topic=self.topic_public_subs,
            acc=models.PROTO_MQTT_ACC_SUS, user=None)
        models.MQTT_ACL.objects.create(
            allow=False, topic=self.topic_forbidden_subs,
            acc=models.PROTO_MQTT_ACC_SUS, user=None)
        models.MQTT_ACL.objects.create(
            allow=True, topic=self.topic_private_subs,
            acc=models.PROTO_MQTT_ACC_SUS, user=user_login)
        self.url_testing = reverse('mqtt_acl')
        self.client = Client()

    def test_no_topic(self):
        response = self.client.post(self.url_testing,
                                    {'username': 'test',
                                     'acc': models.PROTO_MQTT_ACC_PUB,
                                     'topic': '/no/exist/topic'})
        allow = 200
        if hasattr(settings, 'MQTT_ACL_ALLOW'):
            if not settings.MQTT_ACL_ALLOW:
                allow = 403
        self.assertEqual(response.status_code, allow)
        response = self.client.post(self.url_testing,
                                    {'username': 'admin',
                                     'acc': models.PROTO_MQTT_ACC_PUB,
                                     'topic': '/no/exist/topic'})
        allow = 200
        if hasattr(settings, 'MQTT_ACL_ALLOW'):
            if not settings.MQTT_ACL_ALLOW:
                allow = 403
        self.assertEqual(response.status_code, allow)
        response = self.client.post(self.url_testing,
                                    {'username': 'asdf',
                                     'acc': models.PROTO_MQTT_ACC_PUB,
                                     'topic': '/no/exist/topic'})
        allow = 200
        if hasattr(settings, 'MQTT_ACL_ALLOW'):
            if not settings.MQTT_ACL_ALLOW:
                allow = 403
        if hasattr(settings, 'MQTT_ACL_ALLOW_ANONIMOUS'):
            if not settings.MQTT_ACL_ALLOW_ANONIMOUS:
                allow = 403
        self.assertEqual(response.status_code, allow)

    def test_public_publisher(self):
        response = self.client.post(self.url_testing,
                                    {'username': 'test',
                                     'acc': models.PROTO_MQTT_ACC_PUB,
                                     'topic': self.topic_public_publish})
        self.assertEqual(response.status_code, 200)
        response = self.client.post(self.url_testing,
                                    {'username': 'admin',
                                     'acc': models.PROTO_MQTT_ACC_PUB,
                                     'topic': self.topic_public_publish})
        self.assertEqual(response.status_code, 200)
        response = self.client.post(self.url_testing,
                                    {'username': 'asdf',
                                     'acc': models.PROTO_MQTT_ACC_PUB,
                                     'topic': self.topic_public_publish})
        allow = 200
        if hasattr(settings, 'MQTT_ACL_ALLOW'):
            if not settings.MQTT_ACL_ALLOW:
                allow = 403
        if hasattr(settings, 'MQTT_ACL_ALLOW_ANONIMOUS'):
            if not settings.MQTT_ACL_ALLOW_ANONIMOUS:
                allow = 403
        self.assertEqual(response.status_code, allow)

    def test_disallow_publisher(self):
        response = self.client.post(self.url_testing,
                                    {'username': 'test',
                                     'acc': models.PROTO_MQTT_ACC_PUB,
                                     'topic': self.topic_forbidden_publish})
        self.assertEqual(response.status_code, 403)
        response = self.client.post(self.url_testing,
                                    {'username': 'admin',
                                     'acc': models.PROTO_MQTT_ACC_PUB,
                                     'topic': self.topic_forbidden_publish})
        self.assertEqual(response.status_code, 403)
        response = self.client.post(self.url_testing,
                                    {'username': 'asdf',
                                     'acc': models.PROTO_MQTT_ACC_PUB,
                                     'topic': self.topic_forbidden_publish})
        self.assertEqual(response.status_code, 403)

    def test_login_publisher(self):
        response = self.client.post(self.url_testing,
                                    {'username': 'test',
                                     'acc': models.PROTO_MQTT_ACC_PUB,
                                     'topic': self.topic_private_publish})
        self.assertEqual(response.status_code, 200)
        response = self.client.post(self.url_testing,
                                    {'username': 'admin',
                                     'acc': models.PROTO_MQTT_ACC_PUB,
                                     'topic': self.topic_private_publish})
        self.assertEqual(response.status_code, 403)
        response = self.client.post(self.url_testing,
                                    {'username': 'asdf',
                                     'acc': models.PROTO_MQTT_ACC_PUB,
                                     'topic': self.topic_private_publish})
        self.assertEqual(response.status_code, 403)

    def test_public_subscriber(self):
        response = self.client.post(self.url_testing,
                                    {'username': 'test',
                                     'acc': models.PROTO_MQTT_ACC_SUS,
                                     'topic': self.topic_public_subs})
        self.assertEqual(response.status_code, 200)
        response = self.client.post(self.url_testing,
                                    {'username': 'admin',
                                     'acc': models.PROTO_MQTT_ACC_SUS,
                                     'topic': self.topic_public_subs})
        self.assertEqual(response.status_code, 200)
        response = self.client.post(self.url_testing,
                                    {'username': 'asdf',
                                     'acc': models.PROTO_MQTT_ACC_SUS,
                                     'topic': self.topic_public_subs})
        allow = 200
        if hasattr(settings, 'MQTT_ACL_ALLOW'):
            if not settings.MQTT_ACL_ALLOW:
                allow = 403
        if hasattr(settings, 'MQTT_ACL_ALLOW_ANONIMOUS'):
            if not settings.MQTT_ACL_ALLOW_ANONIMOUS:
                allow = 403
        self.assertEqual(response.status_code, allow)

    def test_disallow_subscriber(self):
        response = self.client.post(self.url_testing,
                                    {'username': 'test',
                                     'acc': models.PROTO_MQTT_ACC_SUS,
                                     'topic': self.topic_forbidden_subs})
        self.assertEqual(response.status_code, 403)
        response = self.client.post(self.url_testing,
                                    {'username': 'admin',
                                     'acc': models.PROTO_MQTT_ACC_SUS,
                                     'topic': self.topic_forbidden_subs})
        self.assertEqual(response.status_code, 403)
        response = self.client.post(self.url_testing,
                                    {'username': 'asdf',
                                     'acc': models.PROTO_MQTT_ACC_SUS,
                                     'topic': self.topic_forbidden_subs})
        self.assertEqual(response.status_code, 403)

    def test_login_subscriber(self):
        response = self.client.post(self.url_testing,
                                    {'username': 'test',
                                     'acc': models.PROTO_MQTT_ACC_SUS,
                                     'topic': self.topic_private_subs})
        self.assertEqual(response.status_code, 200)
        response = self.client.post(self.url_testing,
                                    {'username': 'admin',
                                     'acc': models.PROTO_MQTT_ACC_SUS,
                                     'topic': self.topic_private_subs})
        self.assertEqual(response.status_code, 403)
        response = self.client.post(self.url_testing,
                                    {'username': 'asdf',
                                     'acc': models.PROTO_MQTT_ACC_SUS,
                                     'topic': self.topic_private_subs})
        self.assertEqual(response.status_code, 403)
