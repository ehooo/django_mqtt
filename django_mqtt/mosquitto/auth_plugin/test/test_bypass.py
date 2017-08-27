
from django.test import override_settings
from django_mqtt import models
from django_mqtt.mosquitto.auth_plugin.test.utils import BasicAuthWithTopicTestCase


class PubAcc(BasicAuthWithTopicTestCase):
    def setUp(self):
        BasicAuthWithTopicTestCase.setUp(self)
        topic = models.Topic.objects.create(name='#')
        self.acc_allow = False
        self.acc = models.PROTO_MQTT_ACC_PUB
        models.ACL.objects.create(acc=models.PROTO_MQTT_ACC_PUB, topic=topic)
        models.ACL.objects.create(acc=models.PROTO_MQTT_ACC_SUS, topic=topic)

    def test_wrong_user(self):
        response = self._test_wrong_user()
        self.assertEqual(response.status_code, 403)

    def test_login_wrong_topic(self):
        response = self._test_login_wrong_topic()
        self.assertEqual(response.status_code, 200)

    def test_login_no_topic(self):
        response = self._test_login_no_topic()
        self.assertEqual(response.status_code, 200)

    def test_login_no_acl_allow(self):
        response = self._test_login_no_acl_allow()
        self.assertEqual(response.status_code, 200)

    def test_login_with_sus_acl_public(self):
        response = self._test_login_with_sus_acl_public()
        self.assertEqual(response.status_code, 200)

    def test_login_with_sus_acl(self):
        response = self._test_login_with_sus_acl()
        self.assertEqual(response.status_code, 200)

    def test_login_with_sus_acl_group(self):
        response = self._test_login_with_sus_acl_group()
        self.assertEqual(response.status_code, 200)


class SusAcc(BasicAuthWithTopicTestCase):
    def setUp(self):
        BasicAuthWithTopicTestCase.setUp(self)
        topic = models.Topic.objects.create(name='#')
        self.acc_allow = False
        self.acc = models.PROTO_MQTT_ACC_SUS
        models.ACL.objects.create(acc=models.PROTO_MQTT_ACC_PUB, topic=topic)
        models.ACL.objects.create(acc=models.PROTO_MQTT_ACC_SUS, topic=topic)

    @override_settings(MQTT_ACL_ALLOW=True)
    @override_settings(MQTT_ACL_ALLOW_ANONIMOUS=True)
    def test_no_login_acl_allow_anonymous(self):
        response = self._test_no_login()
        self.assertEqual(response.status_code, 200)

    def test_login_wrong_topic(self):
        response = self._test_login_wrong_topic()
        self.assertEqual(response.status_code, 200)

    def test_login_no_topic(self):
        response = self._test_login_no_topic()
        self.assertEqual(response.status_code, 200)

    def test_login_no_acl_allow(self):
        response = self._test_login_no_acl_allow()
        self.assertEqual(response.status_code, 200)

    def test_login_with_pub_acl_public(self):
        response = self._test_login_with_pub_acl_public()
        self.assertEqual(response.status_code, 200)

    def test_login_with_pub_acl(self):
        response = self._test_login_with_pub_acl()
        self.assertEqual(response.status_code, 200)

    def test_login_with_pub_acl_group(self):
        response = self._test_login_with_pub_acl_group()
        self.assertEqual(response.status_code, 200)
