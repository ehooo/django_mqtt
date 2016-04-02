
from django_mqtt.publisher.models import *
from  django.core.files import File
from django.test import TestCase
import os


class PublishTestCase(TestCase):
    def setUp(self):
        self.ca_file = os.path.join(settings.BASE_DIR, 'test_web', 'ca', 'mosquitto.org.crt')

    def test_publish_secure(self):
        for (cert_req, c) in CERT_REQS:
            for (ver, v) in PROTO_SSL_VERSION:
                SecureConf.objects.create(ca_certs=File(open(self.ca_file, 'rb')),
                                          cert_reqs=cert_req,
                                          tls_version=ver,
                                          ciphers='rsa')
        Server.objects.create(host='encrypted.host', port=8883)
        Server.objects.create(host='encrypted.client_certificate.host', port=8884)
        Server.objects.create(host='test.mosquitto.org', port=8883)
        Server.objects.create(host='test.mosquitto.org', port=8884)
        # TODO test send using secure

    def test_publish_websock(self):
        secure = SecureConf.objects.create(ca_certs=File(open(self.ca_file, 'rb')),
                                           cert_reqs=ssl.CERT_REQUIRED,
                                           tls_version=ssl.PROTOCOL_TLSv1,
                                           ciphers=None)
        Server.objects.create(host='test.mosquitto.org', port=8080)
        Server.objects.create(host='test.mosquitto.org', port=8081, secure=secure)
        # TODO

    def test_get_mqtt_client(self):
        client_id = ClientId.objects.create(name='test1client')
        server = Server.objects.create(host='localhost', port=1883)
        init_status = server.status
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
        init_status = server.status
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
        self.assertEqual(unicode(server), u'mqtt://test.mosquitto.org:1883')
        self.assertEqual(server.status, PROTO_MQTT_CONN_ERROR_UNKNOWN)
        self.assertNotEqual(server.status, PROTO_MQTT_CONN_OK)
        client = Client.objects.create(server=server, clean_session=True, client_id=client_id)
        self.assertEqual(str(client), 'publisher - mqtt://test.mosquitto.org:1883')
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
