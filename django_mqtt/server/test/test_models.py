
from django.test import TestCase
import time

from django_mqtt.server.models import *


class SessionModelsTestCase(TestCase):
    def setUp(self):
        self.topic = Topic.objects.create(name='/test')
        self.topic1 = Topic.objects.create(name='/plus/test')
        self.topic2 = Topic.objects.create(name='/test/broadcast')
        self.topic_plus = Topic.objects.create(name='/+/test')
        self.topic_broadcast = Topic.objects.create(name='/test/#')
        self.channel0 = Channel.objects.create(qos=MQTT_QoS0, topic=self.topic)
        self.channel1 = Channel.objects.create(qos=MQTT_QoS1, topic=self.topic1)
        self.channel2 = Channel.objects.create(qos=MQTT_QoS2, topic=self.topic2)
        self.channel_plus = Channel.objects.create(qos=MQTT_QoS2, topic=self.topic_plus)
        self.channel_broadcast = Channel.objects.create(qos=MQTT_QoS2, topic=self.topic_broadcast)
        self.client_id = ClientId.objects.create(name='test')
        self.session = Session.objects.create(keep_alive=3600, client_id=self.client_id)

    def test_string(self):
        str(self.channel0)
        unicode(self.channel0)
        str(self.session)
        unicode(self.session)

    def test_timeout(self):
        session = Session.objects.create(keep_alive=1, client_id=ClientId.objects.create(name='timeout'))
        self.assertEqual(session.is_alive(), True)
        time.sleep(2)
        self.assertEqual(session.is_alive(), False)
        session.ping()
        self.assertEqual(session.is_alive(), True)

    def test_subscribe(self):
        self.session.subscribe(channel=self.channel1)
        self.session.subscribe(topic='/my/topic')
        self.session.subscribe(topic='/my/topic', qos=MQTT_QoS1)
        self.session.subscribe(topic=self.topic2, qos=MQTT_QoS0)
        self.assertRaises(ValueError, self.session.subscribe, qos=MQTT_SUBACK_QoS1)
        self.assertRaises(ValueError, self.session.subscribe, topic=object)
        self.assertRaises(ValueError, self.session.subscribe, channel=object)

    def test_unsubscribe(self):
        self.session.unsubscribe(self.channel1.topic)
        self.session.unsubscribe('/my/topic')
        self.assertRaises(ValueError, self.session.unsubscribe, None)

    def test_disconnect(self):
        session = Session.objects.create(keep_alive=1, client_id=ClientId.objects.create(name='timeout'))
        session.subscribe(channel=self.channel1)
        self.assertEqual(session.subscriptions.all().count(), 1)
        session.unsubscribe(self.topic1)
        self.assertEqual(session.unsubscriptions.all().count(), 1)
        session.disconnect(True)
        self.assertEqual(session.subscriptions.all().count(), 0)
        self.assertEqual(session.unsubscriptions.all().count(), 0)

    def test_is4me(self):
        session = Session.objects.create(keep_alive=1, client_id=ClientId.objects.create(name='timeout'))
        session.subscribe(channel=self.channel2)
        self.assertEqual(session.is4me(self.channel2.topic, MQTT_QoS0), True)
        self.assertEqual(session.is4me(self.channel2.topic, MQTT_QoS1), True)
        self.assertEqual(session.is4me(self.channel2.topic, MQTT_QoS2), True)

        self.assertRaises(ValueError, self.session.is4me, object, 255)

        self.assertEqual(self.session.is4me(self.topic, MQTT_QoS0), False)
        self.assertEqual(self.session.is4me(self.topic, MQTT_QoS1), False)
        self.assertEqual(self.session.is4me(self.topic, MQTT_QoS2), False)

        self.session.subscribe(channel=self.channel0)
        self.assertEqual(self.session.is4me(self.topic, MQTT_QoS0), True)
        self.assertEqual(self.session.is4me(self.topic, MQTT_QoS1), False)
        self.assertEqual(self.session.is4me(self.topic, MQTT_QoS2), False)
        self.session.subscribe(channel=self.channel1)
        self.assertEqual(self.session.is4me(self.topic1, MQTT_QoS0), True)
        self.assertEqual(self.session.is4me(self.topic1, MQTT_QoS1), True)
        self.assertEqual(self.session.is4me(self.topic1, MQTT_QoS2), False)
        self.session.subscribe(channel=self.channel_broadcast)
        self.assertEqual(self.session.is4me(self.topic2, MQTT_QoS0), True)
        self.assertEqual(self.session.is4me(self.topic2, MQTT_QoS1), True)
        self.assertEqual(self.session.is4me(self.topic2, MQTT_QoS2), True)
        self.session.unsubscribe(self.topic2)
        self.assertEqual(self.session.is4me(self.topic2, MQTT_QoS0), False)
        self.assertEqual(self.session.is4me(self.topic2, MQTT_QoS1), False)
        self.assertEqual(self.session.is4me(self.topic2, MQTT_QoS2), False)

        self.assertEqual(self.session.is4me('/test/4me', MQTT_QoS0), True)
        self.assertEqual(self.session.is4me('/test/4me', MQTT_QoS1), True)
        self.assertEqual(self.session.is4me('/test/4me', MQTT_QoS2), True)
        self.assertEqual(self.session.is4me('/not/4me', MQTT_QoS0), False)
        self.assertEqual(self.session.is4me('/not/4me', MQTT_QoS1), False)
        self.assertEqual(self.session.is4me('/not/4me', MQTT_QoS2), False)
        self.assertEqual(self.session.is4me('/test/also/4me', MQTT_QoS0), True)
        self.assertEqual(self.session.is4me('/test/also/4me', MQTT_QoS1), True)
        self.assertEqual(self.session.is4me('/test/also/4me', MQTT_QoS2), True)

        self.session.unsubscribe('/test/+')
        self.assertEqual(self.session.is4me('/test/4me', MQTT_QoS0), False)
        self.assertEqual(self.session.is4me('/test/4me', MQTT_QoS1), False)
        self.assertEqual(self.session.is4me('/test/4me', MQTT_QoS2), False)
        self.session.subscribe(topic='/test/4me', qos=MQTT_QoS2)
        self.assertEqual(self.session.is4me('/test/4me', MQTT_QoS0), True)
        self.assertEqual(self.session.is4me('/test/4me', MQTT_QoS1), True)
        self.assertEqual(self.session.is4me('/test/4me', MQTT_QoS2), True)

        self.assertEqual(self.session.is4me('/test/also/4me', MQTT_QoS0), True)
        self.assertEqual(self.session.is4me('/test/also/4me', MQTT_QoS1), True)
        self.assertEqual(self.session.is4me('/test/also/4me', MQTT_QoS2), True)
        self.session.unsubscribe('/test/+/+')
        self.assertEqual(self.session.is4me('/test/also/4me', MQTT_QoS0), False)
        self.assertEqual(self.session.is4me('/test/also/4me', MQTT_QoS1), False)
        self.assertEqual(self.session.is4me('/test/also/4me', MQTT_QoS2), False)
        self.session.subscribe(topic='/test/also/+')
        self.assertEqual(self.session.is4me('/test/also/4me', MQTT_QoS0), True)
        self.assertEqual(self.session.is4me('/test/also/4me', MQTT_QoS1), False)
        self.assertEqual(self.session.is4me('/test/also/4me', MQTT_QoS2), False)

        self.session.subscribe(topic='/test/also/4me', qos=MQTT_QoS1)
        self.assertEqual(self.session.is4me('/test/also/4me', MQTT_QoS0), True)
        self.assertEqual(self.session.is4me('/test/also/4me', MQTT_QoS1), True)
        self.assertEqual(self.session.is4me('/test/also/4me', MQTT_QoS2), False)
        self.session.unsubscribe(self.channel_broadcast.topic)
        self.assertEqual(self.session.is4me('/test/also/4me', MQTT_QoS0), True)
        self.assertEqual(self.session.is4me('/test/also/4me', MQTT_QoS1), True)
        self.assertEqual(self.session.is4me('/test/also/4me', MQTT_QoS2), False)
        topic, is_new = Topic.objects.get_or_create(name='/test/also/4me')
        acl = ACL.objects.create(topic=topic, acc=PROTO_MQTT_ACC_SUS, allow=True)
        self.assertEqual(self.session.is4me('/test/also/4me', MQTT_QoS0), True)
        self.assertEqual(self.session.is4me('/test/also/4me', MQTT_QoS1), True)
        self.assertEqual(self.session.is4me('/test/also/4me', MQTT_QoS2), False)
        user = User.objects.create_user('test')
        acl.users.add(user)
        self.assertEqual(self.session.is4me('/test/also/4me', MQTT_QoS0), False)
        self.assertEqual(self.session.is4me('/test/also/4me', MQTT_QoS1), False)
        self.assertEqual(self.session.is4me('/test/also/4me', MQTT_QoS2), False)
        self.session.user = user
        self.session.save()
        self.assertEqual(self.session.is4me('/test/also/4me', MQTT_QoS0), True)
        self.assertEqual(self.session.is4me('/test/also/4me', MQTT_QoS1), True)
        self.assertEqual(self.session.is4me('/test/also/4me', MQTT_QoS2), False)

        if session.is_alive():
            time.sleep(2)
        self.assertEqual(session.is4me(self.channel2.topic, MQTT_QoS0), False)
        self.assertEqual(session.is4me(self.channel2.topic, MQTT_QoS1), False)
        self.assertEqual(session.is4me(self.channel2.topic, MQTT_QoS2), False)


class PublicationModelsTestCase(TestCase):
    def setUp(self):
        self.topic = Topic.objects.create(name='/test')
        self.channel = Channel.objects.create(qos=MQTT_QoS0, topic=self.topic)

    def test_string(self):
        pub = Publication.objects.create(channel=self.channel, remain=False)
        str(pub)
        unicode(pub)
