
from django.test import TestCase

from django_mqtt.models import *
from django.core.exceptions import ValidationError


class TopicModelsTestCase(TestCase):

    def test_topic_simple_wildcard(self):
        topic = Topic.objects.create(name='+')
        self.assertEqual('' in topic, True)
        self.assertEqual('test' in topic, True)
        self.assertEqual('/test' in topic, False)
        self.assertEqual('/test/sd' in topic, False)
        topic = Topic.objects.create(name='/test/+/two')
        self.assertEqual('/test/a/two' in topic, True)
        self.assertEqual('/test/b/two' in topic, True)
        self.assertEqual('/test' in topic, False)
        self.assertEqual('/test/a/twos' in topic, False)
        self.assertEqual('/test/b/two/3' in topic, False)
        topic = Topic.objects.create(name='test/+/two')
        self.assertEqual('test/a/two' in topic, True)
        self.assertEqual('test/b/two' in topic, True)
        self.assertEqual('test' in topic, False)
        self.assertEqual('test/a/twos' in topic, False)
        self.assertEqual('test/b/two/3' in topic, False)

    def test_wrong_topic_simple_wildcard(self):
        self.assertRaises(ValidationError, Topic.objects.create, name='a+')
        self.assertRaises(ValidationError, Topic.objects.create, name='a+/')
        self.assertRaises(ValidationError, Topic.objects.create, name='a/a+')
        self.assertRaises(ValidationError, Topic.objects.create, name='a/+a')

    def test_topic_multi_wildcard(self):
        topic = Topic.objects.create(name='#')
        self.assertEqual('test/a/two' in topic, True)
        self.assertEqual('test/b/two' in topic, True)
        self.assertEqual('test' in topic, True)
        self.assertEqual('test/a/twos' in topic, True)
        self.assertEqual('test/b/two/3' in topic, True)
        self.assertEqual('/test/a/two' in topic, True)
        self.assertEqual('/test/b/two' in topic, True)
        self.assertEqual('/test' in topic, True)
        self.assertEqual('/test/a/twos' in topic, True)
        self.assertEqual('/test/b/two/3' in topic, True)
        topic = Topic.objects.create(name='/#')
        self.assertEqual('/test/a/two' in topic, True)
        self.assertEqual('/test/b/two' in topic, True)
        self.assertEqual('/test' in topic, True)
        self.assertEqual('/test/a/twos' in topic, True)
        self.assertEqual('/test/b/two/3' in topic, True)
        self.assertEqual('test' in topic, False)
        self.assertEqual('test/a/twos' in topic, False)
        self.assertEqual('test/b/two/3' in topic, False)

    def test_wrong_topic_multi_wildcard(self):
        self.assertRaises(ValidationError, Topic.objects.create, name='#/')
        self.assertRaises(ValidationError, Topic.objects.create, name='a#')
        self.assertRaises(ValidationError, Topic.objects.create, name='a#/')
        self.assertRaises(ValidationError, Topic.objects.create, name='a/#a')
        self.assertRaises(ValidationError, Topic.objects.create, name='a/a#')

    def test_topic_wildcard(self):
        Topic.objects.create(name='/test/+/two/#')
        Topic.objects.create(name='/+/#')
        Topic.objects.create(name='+/#')

    def test_wrong_topic_wildcard(self):
        self.assertRaises(ValidationError, Topic.objects.create, name='#+/')
        self.assertRaises(ValidationError, Topic.objects.create, name='+#/')

    def test_topic_dollar(self):
        plus = Topic.objects.create(name='$SYS/+')
        multi = Topic.objects.create(name='$SYS/#')
        self.assertEqual(plus in multi, True)
        self.assertEqual(multi in plus, False)
        self.assertRaises(ValidationError, Topic.objects.create, name='$+')
        self.assertRaises(ValidationError, Topic.objects.create, name='$#')
        topic = Topic.objects.create(name='$/+')
        self.assertEqual('+/+' in topic, False)
        self.assertEqual('+/#' in topic, False)
        self.assertEqual('$/test' in topic, True)
        self.assertEqual('$/test/one' in topic, False)
        topic = Topic.objects.create(name='$/#')
        self.assertEqual('+/+' in topic, False)
        self.assertEqual('+/#' in topic, False)
        self.assertEqual('$/test' in topic, True)
        self.assertEqual('$/test/one' in topic, True)
        topic = Topic.objects.get_or_create(name='+')
        dollar = Topic.objects.create(name='$')
        self.assertEqual(dollar in topic, False)
        self.assertRaises(ValidationError, Topic.objects.create, name='$/')

    def test_topic(self):
        Topic.objects.create(name='test')
        Topic.objects.create(name='test/one')
        Topic.objects.create(name='test/one/two')
        Topic.objects.create(name='/test')
        Topic.objects.create(name='/test/one')
        Topic.objects.create(name='/test/one/two')

        self.assertRaises(ValidationError, Topic.objects.create, name='//')
        self.assertRaises(ValidationError, Topic.objects.create, name='/')


class ClientIdModelsTestCase(TestCase):

    def test_client_id(self):
        if hasattr(settings, 'MQTT_ALLOW_EMPTY_CLIENT_ID') and settings.MQTT_ALLOW_EMPTY_CLIENT_ID:
            ClientId.objects.create(name='')
        ClientId.objects.create(name='1234')
        ClientId.objects.create(name='test')
        ClientId.objects.create(name='test123')

    def test_wrong_client_id(self):
        if not hasattr(settings, 'MQTT_ALLOW_EMPTY_CLIENT_ID') or not settings.MQTT_ALLOW_EMPTY_CLIENT_ID:
            self.assertRaises(ValidationError, ClientId.objects.create, name='')
        self.assertRaises(ValidationError, ClientId.objects.create, name='012345678901234567890123456789')
        self.assertRaises(ValidationError, ClientId.objects.create, name='/')
        self.assertRaises(ValidationError, ClientId.objects.create, name='+')
        self.assertRaises(ValidationError, ClientId.objects.create, name='#')




