import os
import ssl

import six
from django.conf import settings
from django.core.files import File
from django.test import TestCase
from django_mqtt.models import Topic
from django_mqtt.protocol import MQTT_QoS0, MQTT_QoS1, MQTT_QoS2
from django_mqtt.publisher.management.commands.mqtt_updater import Command as CommandUpdater
from django_mqtt.publisher.models import (
    CERT_REQS,
    PROTO_MQTT_CONN_ERROR_UNKNOWN,
    PROTO_MQTT_CONN_OK,
    PROTO_SSL_VERSION,
    Auth,
    Client,
    ClientId,
    Data,
    SecureConf,
    Server,
    private_fs,
)
from paho.mqtt.client import MQTTMessage


class PublishTestCase(TestCase):
    def setUp(self):
        self.ca_file = os.path.join(settings.BASE_DIR, 'test_web', 'ca', 'mosquitto.org.crt')
        self.ca_cert_file = File(open(self.ca_file, 'rb'), 'mosquitto.org.crt')

    def tearDown(self):
        if private_fs.exists('ca/mosquitto.org.crt'):
            for sec_conf in SecureConf.objects.filter(ca_certs__isnull=False):
                sec_conf.ca_certs.delete()

    def test_publish_secure(self):
        for (cert_req, c) in CERT_REQS:
            for (ver, v) in PROTO_SSL_VERSION:
                SecureConf.objects.create(ca_certs=self.ca_cert_file,
                                          cert_reqs=cert_req,
                                          tls_version=ver,
                                          ciphers='rsa')
        Server.objects.create(host='encrypted.host', port=8883)
        Server.objects.create(host='encrypted.client_certificate.host', port=8884)
        Server.objects.create(host='test.mosquitto.org', port=8883)
        Server.objects.create(host='test.mosquitto.org', port=8884)
        # TODO test send using secure

    def test_publish_websock(self):
        secure = SecureConf.objects.create(ca_certs=self.ca_cert_file,
                                           cert_reqs=ssl.CERT_REQUIRED,
                                           tls_version=ssl.PROTOCOL_TLSv1,
                                           ciphers=None)
        Server.objects.create(host='test.mosquitto.org', port=8080)
        Server.objects.create(host='test.mosquitto.org', port=8081, secure=secure)
        # TODO

    def test_get_mqtt_client(self):
        client_id = ClientId.objects.create(name='test1client')
        server = Server.objects.create(host='localhost', port=1883)
        self.assertNotEqual(server.status, PROTO_MQTT_CONN_OK)
        auth = Auth.objects.create(user='admin', password='admin1234')
        client = Client.objects.create(server=server, auth=auth, client_id=client_id, clean_session=True)
        client.get_mqtt_client(empty_client_id=True)

        client = Client.objects.create(server=server, auth=auth, client_id=client_id, clean_session=False)
        self.assertRaises(ValueError, client.get_mqtt_client, empty_client_id=True)

        client = Client.objects.create(server=server, auth=auth, clean_session=False)
        client.get_mqtt_client(empty_client_id=True)

    def test_publish_fail(self):
        server = Server.objects.create(host='localhost', port=1883)
        init_status = server.status
        self.assertNotEqual(server.status, PROTO_MQTT_CONN_OK)
        auth = Auth.objects.create(user='admin', password='admin1234')
        self.assertEqual(str(auth), 'admin:*********')
        if six.PY2:  # pragma: no cover
            self.assertEqual(unicode(auth), u'admin:*********')
        client = Client.objects.create(server=server, auth=auth, clean_session=False, keepalive=5)
        self.assertEqual(client.client_id, None)

        topic = Topic.objects.create(name='/fail/publish')
        for qos in [MQTT_QoS0, MQTT_QoS1, MQTT_QoS2]:
            data, is_new = Data.objects.get_or_create(client=client, topic=topic)
            data.qos = qos
            data.payload = 'fail test'
            data.retain = True
            data.save()
            server = Server.objects.get(pk=server.pk)
            self.assertNotEqual(server.status, PROTO_MQTT_CONN_OK)
            server.status = init_status
            server.save()

    def test_publish_ok_clear(self):
        server = Server.objects.create(host='test.mosquitto.org', port=1883)
        self.assertEqual(server.status, PROTO_MQTT_CONN_ERROR_UNKNOWN)
        self.assertNotEqual(server.status, PROTO_MQTT_CONN_OK)
        client = Client.objects.create(server=server, clean_session=False)
        self.assertEqual(client.client_id, None)

        topic = Topic.objects.create(name='/test/publish')
        for qos in [MQTT_QoS0, MQTT_QoS1, MQTT_QoS2]:
            data, is_new = Data.objects.get_or_create(client=client, topic=topic)
            data.qos = qos
            data.payload = 'test %(qos)s' % {'qos': qos}
            data.retain = True
            data.save()
            data.update_remote()

            server = Server.objects.get(pk=server.pk)
            self.assertEqual(server.status, PROTO_MQTT_CONN_OK)
            server.status = PROTO_MQTT_CONN_ERROR_UNKNOWN
            server.save()

            client = Client.objects.get(pk=client.pk)
            self.assertNotEqual(client.client_id, None)
            client.client_id = None
            client.save()

    def test_publish_ok(self):
        client_id = ClientId.objects.create(name='publisher')
        server = Server.objects.create(host='test.mosquitto.org', port=1883)
        self.assertEqual(str(server), 'mqtt://test.mosquitto.org:1883')
        if six.PY2:  # pragma: no cover
            self.assertEqual(unicode(server), u'mqtt://test.mosquitto.org:1883')
        self.assertEqual(server.status, PROTO_MQTT_CONN_ERROR_UNKNOWN)
        self.assertNotEqual(server.status, PROTO_MQTT_CONN_OK)
        client = Client.objects.create(server=server, clean_session=True, client_id=client_id)
        self.assertEqual(str(client), 'publisher - mqtt://test.mosquitto.org:1883')
        if six.PY2:  # pragma: no cover
            self.assertEqual(unicode(client), u'publisher - mqtt://test.mosquitto.org:1883')

        topic = Topic.objects.create(name='/test/publish')
        for qos in [MQTT_QoS0, MQTT_QoS1, MQTT_QoS2]:
            data, is_new = Data.objects.get_or_create(client=client, topic=topic)
            data.qos = qos
            data.payload = 'test %(qos)s' % {'qos': qos}
            data.retain = True
            data.save()
            self.assertEqual(str(data), 'test %(qos)s - /test/publish - publisher - mqtt://test.mosquitto.org:1883' %
                             {'qos': qos})
            if six.PY2:  # pragma: no cover
                self.assertEqual(unicode(data),
                                 u'test %(qos)s - /test/publish - publisher - mqtt://test.mosquitto.org:1883' %
                                 {'qos': qos})
            data.update_remote()

            server = Server.objects.get(pk=server.pk)
            self.assertEqual(server.status, PROTO_MQTT_CONN_OK)
            server.status = PROTO_MQTT_CONN_ERROR_UNKNOWN
            server.save()

            client = Client.objects.get(pk=client.pk)
            self.assertNotEqual(client.client_id, None)
            client.save()


class CommandUpdaterTestCase(TestCase):
    def setUp(self):
        self.command = CommandUpdater()
        self.message = MQTTMessage()
        self.message.topic = '/topic/name'
        self.message.qos = 0
        self.message.payload = 'payload'

    def create_client(self):
        server = Server.objects.create(host='test.mosquitto.org', port=1883)
        return Client.objects.create(server=server, clean_session=False, keepalive=5)

    def test_blank(self):
        self.assertEqual(Client.objects.count(), 0)
        self.assertIsNone(self.command.on_message(None, None, self.message))
        self.assertEqual(Topic.objects.count(), 0)
        self.assertEqual(Data.objects.count(), 0)

    def test_message_no_topic(self):
        self.command.client_db = self.create_client()
        self.assertEqual(Client.objects.count(), 1)
        self.assertIsNone(self.command.on_message(None, None, self.message))
        self.assertEqual(Topic.objects.count(), 0)
        self.assertEqual(Data.objects.count(), 0)

    def test_message_no_data(self):
        self.command.client_db = self.create_client()
        Topic.objects.create(name=self.message.topic)
        self.assertEqual(Client.objects.count(), 1)
        self.assertIsNone(self.command.on_message(None, None, self.message))
        self.assertEqual(Topic.objects.count(), 1)
        self.assertEqual(Data.objects.count(), 0)

    def test_message_with_all(self):
        client = self.create_client()
        self.command.client_db = client
        self.assertEqual(Client.objects.count(), 1)
        topic = Topic.objects.create(name=self.message.topic)
        self.assertEqual(Topic.objects.count(), 1)
        Data.objects.create(client=client, topic=topic, payload='initial payload')
        self.assertEqual(Data.objects.count(), 1)
        self.assertEqual(Data.objects.get().payload, 'initial payload')
        self.assertIsNone(self.command.on_message(None, None, self.message))
        self.assertEqual(Data.objects.get().payload, self.message.payload)

    def test_message_for_other(self):
        client = self.create_client()
        self.command.client_db = client
        topic = Topic.objects.create(name=self.message.topic)
        Data.objects.create(client=client, topic=topic, payload='initial payload')
        self.message.topic = '/new/topic'
        self.assertIsNone(self.command.on_message(None, None, self.message))
        self.assertEqual(Client.objects.count(), 1)
        self.assertEqual(Topic.objects.count(), 1)
        self.assertEqual(Data.objects.count(), 1)
        self.assertEqual(Data.objects.get().payload, 'initial payload')

    def test_message_with_create(self):
        self.command.client_db = self.create_client()
        self.assertEqual(Client.objects.count(), 1)
        self.command.create_if_not_exist = True
        self.assertIsNone(self.command.on_message(None, None, self.message))
        self.assertEqual(Topic.objects.count(), 1)
        self.assertEqual(Topic.objects.get().name, self.message.topic)
        self.assertEqual(Data.objects.count(), 1)
        self.assertEqual(Data.objects.get().payload, self.message.payload)
