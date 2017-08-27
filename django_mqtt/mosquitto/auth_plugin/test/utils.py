from django.contrib.auth.models import User, Group
from django.test import TestCase, Client, override_settings
from django.core.urlresolvers import reverse

from django_mqtt import models


@override_settings(MQTT_ACL_ALLOW=False)
@override_settings(MQTT_ACL_ALLOW_ANONIMOUS=False)
class BasicAuthWithTopicTestCase(TestCase):
    def setUp(self):
        self.username = 'user'
        self.password = 'password'
        User.objects.create_user(self.username, password=self.password)
        self.topic = '/topic'
        models.Topic.objects.create(name=self.topic)
        self.url_testing = reverse('mqtt_auth')
        self.client = Client()
        self.acc = None
        self.acc_allow = True

    def get_post_data(self):
        return {
            'username': self.username,
            'password': self.password,
            'topic': self.topic,
            'acc': self.acc
        }

    def create_acl(self, acc):
        topic = models.Topic.objects.get(name=self.topic)
        return models.ACL.objects.create(acc=acc, topic=topic, allow=self.acc_allow)

    def _test_no_login(self):
        data = self.get_post_data()
        if 'password' in data.keys():
            del (data['password'])
        if 'username' in data.keys():
            del (data['username'])
        return self.client.post(self.url_testing, data)

    def test_no_login(self):
        response = self._test_no_login()
        self.assertEqual(response.status_code, 403)

    @override_settings(MQTT_ACL_ALLOW=True)
    def test_no_login_acl_allow(self):
        response = self._test_no_login()
        self.assertEqual(response.status_code, 403)

    @override_settings(MQTT_ACL_ALLOW_ANONIMOUS=True)
    def test_no_login_no_acl_allow_yes_anonymous(self):
        response = self._test_no_login()
        self.assertEqual(response.status_code, 403)

    @override_settings(MQTT_ACL_ALLOW=True)
    @override_settings(MQTT_ACL_ALLOW_ANONIMOUS=True)
    def test_no_login_acl_allow_anonymous(self):
        response = self._test_no_login()
        self.assertEqual(response.status_code, 200)

    def _test_wrong_login(self):
        data = self.get_post_data()
        data['password'] = 'wrong'
        return self.client.post(self.url_testing, data)

    def test_wrong_login(self):
        response = self._test_wrong_login()
        self.assertEqual(response.status_code, 403)

    def _test_wrong_user(self):
        data = self.get_post_data()
        data['username'] = 'wrong'
        return self.client.post(self.url_testing, data)

    def test_wrong_user(self):
        response = self._test_wrong_user()
        self.assertEqual(response.status_code, 403)

    @override_settings(MQTT_ACL_ALLOW=True)
    def _test_login_acl_allow(self):
        return self.client.post(self.url_testing, self.get_post_data())

    def test_login_acl_allow(self):
        response = self._test_login_acl_allow()
        self.assertEqual(response.status_code, 200)

    def _test_login_no_acl_allow(self):
        return self.client.post(self.url_testing, self.get_post_data())

    def test_login_no_acl_allow(self):
        response = self._test_login_no_acl_allow()
        self.assertEqual(response.status_code, 403)

    def _test_login_wrong_topic(self):
        return self.client.post(self.url_testing, {'username': self.username,
                                                   'password': self.password,
                                                   'topic': None,
                                                   'acc': self.acc
                                                   })

    def test_login_wrong_topic(self):
        response = self._test_login_wrong_topic()
        self.assertEqual(response.status_code, 403)

    def _test_login_no_topic(self):
        return self.client.post(self.url_testing, {'username': self.username,
                                                   'password': self.password,
                                                   'acc': self.acc
                                                   })

    def test_login_no_topic(self):
        response = self._test_login_no_topic()
        self.assertEqual(response.status_code, 403)

    def _test_login_with_sus_acl_public(self):
        self.create_acl(models.PROTO_MQTT_ACC_SUS)
        return self.client.post(self.url_testing, self.get_post_data())

    def test_login_with_sus_acl_public(self):
        response = self._test_login_with_sus_acl_public()
        self.assertEqual(response.status_code, 403)

    def _test_login_with_pub_acl_public(self):
        self.create_acl(models.PROTO_MQTT_ACC_PUB)
        return self.client.post(self.url_testing, self.get_post_data())

    def test_login_with_pub_acl_public(self):
        response = self._test_login_with_pub_acl_public()
        self.assertEqual(response.status_code, 403)

    def _test_login_with_sus_acl(self):
        acl = self.create_acl(models.PROTO_MQTT_ACC_SUS)
        acl.users.add(User.objects.get(username=self.username))
        acl.save()
        return self.client.post(self.url_testing, self.get_post_data())

    def test_login_with_sus_acl(self):
        response = self._test_login_with_sus_acl()
        self.assertEqual(response.status_code, 403)

    def _test_login_with_pub_acl(self):
        acl = self.create_acl(models.PROTO_MQTT_ACC_PUB)
        acl.users.add(User.objects.get(username=self.username))
        acl.save()
        return self.client.post(self.url_testing, self.get_post_data())

    def test_login_with_pub_acl(self):
        response = self._test_login_with_pub_acl()
        self.assertEqual(response.status_code, 403)

    def _test_login_with_sus_acl_group(self):
        acl = self.create_acl(models.PROTO_MQTT_ACC_SUS)
        user = User.objects.get(username=self.username)
        group = Group.objects.create(name='mqtt')
        user.groups.add(group)
        user.save()
        acl.groups.add(group)
        acl.save()
        return self.client.post(self.url_testing, self.get_post_data())

    def test_login_with_sus_acl_group(self):
        response = self._test_login_with_sus_acl_group()
        self.assertEqual(response.status_code, 403)

    def _test_login_with_pub_acl_group(self):
        acl = self.create_acl(models.PROTO_MQTT_ACC_PUB)
        user = User.objects.get(username=self.username)
        group = Group.objects.create(name='mqtt')
        user.groups.add(group)
        user.save()
        acl.groups.add(group)
        acl.save()
        return self.client.post(self.url_testing, self.get_post_data())

    def test_login_with_pub_acl_group(self):
        response = self._test_login_with_pub_acl_group()
        self.assertEqual(response.status_code, 403)
