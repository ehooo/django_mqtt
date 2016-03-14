from django.test import TestCase

from django_mqtt.server.packets import *
from django_mqtt.protocol import *


class ConnectTestCase(TestCase):

    def do_check(self, pkg):
        # TODO check vs run server
        pkg.check_integrity()

    def test_invalid_flags(self):
        pkg = Connect(client_id='test')
        for f in range(int('1111', 2)):
            pkg.flags = f+1
            self.assertRaises(MQTTException, self.do_check, pkg)

    def test_invalid_proto_name(self):
        pkg = Connect(client_id='test')
        pkg.proto_name = gen_string("")
        self.assertRaises(MQTTException, self.do_check, pkg)

    def test_invalid_proto_level(self):
        pkg = Connect(client_id='test')
        pkg.proto_level = 0xFF
        self.assertRaises(MQTTException, self.do_check, pkg)

    def test_invalid_qos(self):
        pkg = Connect(client_id='test')
        pkg.set_flags(qos=int('11', 2))
        self.assertEqual(pkg.conn_flags, int('11', 2) << 3)
        self.assertRaises(MQTTException, self.do_check, pkg)

    def test_retain(self):
        pkg = Connect(client_id='test')
        pkg.set_flags(retain=True)
        self.assertEqual(pkg.conn_flags, MQTT_CONN_FLAGS_RETAIN)
        self.assertRaises(MQTTException, self.do_check, pkg)

        pkg.msg = ""
        self.assertEqual(pkg.conn_flags, 0x00)
        pkg.set_flags(retain=True)
        self.assertRaises(MQTTException, self.do_check, pkg)

        pkg.topic = ""
        self.assertEqual(pkg.conn_flags, MQTT_CONN_FLAGS_RETAIN)
        self.do_check(pkg)
        pkg.msg = "\x00\x00Binary\x00\xC0\xC1\xF5\xFFMSG"
        self.do_check(pkg)

    def test_auth_name(self):
        pkg = Connect(client_id='test', auth_name='username')
        self.assertEqual(pkg.conn_flags, MQTT_CONN_FLAGS_NAME)
        pkg.auth_name = ''
        self.assertRaises(MQTTException, self.do_check, pkg)
        pkg.set_flags(name='')
        self.assertEqual(pkg.conn_flags, 0x00)

    def test_auth_password(self):
        pkg = Connect(client_id='test', auth_password='user pasword')
        self.assertEqual(pkg.conn_flags, MQTT_CONN_FLAGS_PASSWORD)
        pkg.auth_password = ''
        self.assertRaises(MQTTException, self.do_check, pkg)
        pkg.set_flags(password='')
        self.assertEqual(pkg.conn_flags, 0x00)

    def test_bin_auth_password(self):
        pkg = Connect(client_id='test', auth_password='user\xC0\xC1\xF5\xFFbin_pasword')
        self.assertEqual(pkg.conn_flags, MQTT_CONN_FLAGS_PASSWORD)
        pkg.auth_password = ''
        self.assertRaises(MQTTException, self.do_check, pkg)
        pkg.set_flags(password='')
        self.assertEqual(pkg.conn_flags, 0x00)

    def test_invalid_client_id(self):
        pkg = Connect(client_id='$/+#')
        self.assertRaises(MQTTProtocolException, self.do_check, pkg)


