from django.test import TestCase

from django_mqtt.server.packets import *
from django_mqtt.protocol import *

import six


class ConnectTestCase(TestCase):

    def do_check(self, pkg):
        # TODO check vs run server
        pkg.check_integrity()

    def test_invalid_flags(self):
        pkg = Connect(clientId='test', qos=0, keep_alive=0x0f, proto_level=0x04,
                      topic="", msg="", auth_name='', auth_password='')
        for f in range(int('1111', 2)):
            pkg.flags = f+1
            self.assertRaises(MQTTProtocolException, pkg.check_integrity)

    def test_invalid_proto_name(self):
        pkg = Connect(clientId='test', qos=0, keep_alive=0x0f, proto_level=0x04,
                      topic="", msg="", auth_name='', auth_password='')
        pkg.proto_name = gen_string("")
        self.assertRaises(MQTTException, pkg.check_integrity)

    def test_invalid_proto_level(self):
        pkg = Connect(clientId='test', qos=0, keep_alive=0x0f, proto_level=0x04,
                      topic="", msg="", auth_name='', auth_password='')

        pkg.proto_level = 0xFF
        self.assertRaises(MQTTException, pkg.check_integrity)

    def test_invalid_qos(self):
        pkg = Connect(clientId='', qos=0, keep_alive=0x0f, proto_level=0x04,
                      topic="", msg="", auth_name='', auth_password='')
        pkg.set_flags(qos=int('11', 2))
        self.assertEqual(pkg.conn_flags, int('11', 2) << 3)
        self.assertRaises(MQTTProtocolException, pkg.check_integrity)

    def test_retain(self):
        pkg = Connect(clientId='', qos=0, keep_alive=0x0f, proto_level=0x04,
                      topic="", msg="", auth_name='', auth_password='')
        pkg.set_flags(retain=True)
        self.assertEqual(pkg.conn_flags, MQTT_CONN_FLAGS_RETAIN)
        self.assertRaises(MQTTProtocolException, pkg.check_integrity)

    def test_auth_name(self):
        pkg = Connect(clientId='test', qos=0, keep_alive=0x0f, proto_level=0x04,
                      topic="", msg="", auth_name='username', auth_password='')
        self.assertEqual(pkg.conn_flags, MQTT_CONN_FLAGS_NAME)
        pkg.auth_name = ''
        self.assertRaises(MQTTException, pkg.check_integrity)
        pkg.set_flags(name='')
        self.assertEqual(pkg.conn_flags, 0x00)

    def test_auth_password(self):
        pkg = Connect(clientId='test', qos=0, keep_alive=0x0f, proto_level=0x04,
                      topic="", msg="", auth_name='', auth_password='user pasword')
        self.assertEqual(pkg.conn_flags, MQTT_CONN_FLAGS_PASSWORD)
        pkg.auth_password = ''
        self.assertRaises(MQTTException, pkg.check_integrity)
        pkg.set_flags(password='')
        self.assertEqual(pkg.conn_flags, 0x00)

    def test_bin_auth_password(self):
        pkg = Connect(clientId='test', qos=0, keep_alive=0x0f, proto_level=0x04,
                      topic="", msg="", auth_name='', auth_password='user\xC0\xC1\xF5\xFFbin_pasword')
        self.assertEqual(pkg.conn_flags, MQTT_CONN_FLAGS_PASSWORD)
        pkg.auth_password = ''
        self.assertRaises(MQTTException, pkg.check_integrity)
        pkg.set_flags(password='')
        self.assertEqual(pkg.conn_flags, 0x00)

    def test_invalid_client_id(self):
        pkg = Connect(clientId='', qos=0, keep_alive=0x0f, proto_level=0x04,
                      topic="", msg="", auth_name='', auth_password='')
        self.assertRaises(MQTTProtocolException, pkg.check_integrity)
        pkg.clientId = '$/+#'
        self.assertRaises(MQTTProtocolException, pkg.check_integrity)


