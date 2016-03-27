from django.test import TestCase

from django_mqtt.server.test_service import *
from django_mqtt.test_models import *
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

    def test_flag(self):
        pkg = Connect(client_id='test')
        pkg.set_flags(retain=True)
        self.assertEqual(pkg.conn_flags, MQTT_CONN_FLAGS_RETAIN | MQTT_CONN_FLAGS_FLAG)
        self.assertRaises(MQTTException, self.do_check, pkg)

        pkg.msg = ""
        self.assertEqual(pkg.conn_flags, 0x00)
        pkg.set_flags(retain=True)
        pkg.set_flags(retain=False)
        self.assertEqual(pkg.conn_flags, MQTT_CONN_FLAGS_FLAG)
        self.assertRaises(MQTTException, self.do_check, pkg)

        pkg.topic = ""
        self.assertEqual(pkg.conn_flags, MQTT_CONN_FLAGS_FLAG)
        self.assertRaises(MQTTException, self.do_check, pkg)

        pkg.msg = "\x00\x00Binary\x00\xC0\xC1\xF5\xFFMSG"
        self.assertRaises(MQTTException, self.do_check, pkg)

        pkg.topic = "\test"
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


class AckConnTestCase(TestCase):

    def do_check(self, pkg):
        pkg.check_integrity()

    def test_invalid_flags(self):
        pkg = ConnAck(ret_code=mqtt.CONNACK_ACCEPTED)
        for f in range(int('1111', 2)):
            pkg.flags = f+1
            self.assertRaises(MQTTException, self.do_check, pkg)

    def test_valid_ack(self):
        for ret_code in [mqtt.CONNACK_ACCEPTED, mqtt.CONNACK_REFUSED_SERVER_UNAVAILABLE,
                         mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED, mqtt.CONNACK_REFUSED_PROTOCOL_VERSION,
                         mqtt.CONNACK_REFUSED_NOT_AUTHORIZED, mqtt.CONNACK_REFUSED_BAD_USERNAME_PASSWORD]:
            pkg = ConnAck(ret_code=ret_code)
            if ret_code != mqtt.CONNACK_ACCEPTED:
                self.assertRaises(MQTTProtocolException, self.do_check, pkg)
                pkg.set_flags(sp=True)
                self.assertRaises(MQTTException, self.do_check, pkg)
            else:
                self.do_check(pkg)
                pkg.set_flags(sp=True)
                self.do_check(pkg)

    def test_invalid_ack(self):
        pkg = ConnAck(ret_code=254)
        self.assertRaises(MQTTException, self.do_check, pkg)


class PublisherTestCase(TestCase):

    def do_check(self, pkg):
        pkg.check_integrity()

    def test_invalid_qos(self):
        pkg = Publish(topic="/test", msg="test", qos=3, dup=False, retain=False)
        self.assertRaises(MQTTException, self.do_check, pkg)

    def test_invalid_topic(self):
        pkg = Publish(topic="/#", msg="test", qos=0, dup=False, retain=False)
        self.assertRaises(MQTTException, self.do_check, pkg)
        pkg = Publish(topic="", msg="test", qos=0, dup=False, retain=False)
        self.assertRaises(MQTTException, self.do_check, pkg)

    def test_valid_qos0(self):
        pkg = Publish(topic="/test", msg="test", qos=0, dup=False, retain=False)
        self.do_check(pkg)
        pkg.set_flags(retain=True)
        self.do_check(pkg)

    def test_invalid_qos0(self):
        pkg = Publish(topic="/test", msg="test", qos=0, dup=True, retain=False)
        self.assertRaises(MQTTException, self.do_check, pkg)

    def test_valid_qos1(self):
        pkg = Publish(topic="/test", msg="test", qos=1, dup=False, retain=False, pack_identifier=0x1234)
        self.do_check(pkg)
        pkg = Publish(topic="/test", msg="test", qos=1, dup=False, retain=True, pack_identifier=0x1234)
        self.do_check(pkg)
        pkg = Publish(topic="/test", msg="test", qos=1, dup=True, retain=True, pack_identifier=0x1234)
        self.do_check(pkg)
        pkg = Publish(topic="/test", msg="test", qos=1, dup=True, retain=False, pack_identifier=0x1234)
        self.do_check(pkg)

    def test_invalid_qos1(self):
        pkg = Publish(topic="/test", msg="test", qos=1, dup=True, retain=False, pack_identifier=None)
        self.assertRaises(MQTTException, self.do_check, pkg)
        pkg = Publish(topic="/test", msg="test", qos=1, dup=True, retain=False, pack_identifier=0x0000)
        self.assertRaises(MQTTException, self.do_check, pkg)

    def test_valid_qos2(self):
        pkg = Publish(topic="/test", msg="test", qos=2, dup=False, retain=False, pack_identifier=0x1234)
        self.do_check(pkg)
        pkg = Publish(topic="/test", msg="test", qos=2, dup=False, retain=True, pack_identifier=0x1234)
        self.do_check(pkg)
        pkg = Publish(topic="/test", msg="test", qos=2, dup=True, retain=True, pack_identifier=0x1234)
        self.do_check(pkg)
        pkg = Publish(topic="/test", msg="test", qos=2, dup=True, retain=False, pack_identifier=0x1234)
        self.do_check(pkg)
        pkg = Publish(topic="/test", msg="test", qos=2, dup=True, retain=False, pack_identifier=None)
        self.assertRaises(MQTTException, self.do_check, pkg)
        pkg = Publish(topic="/test", msg="test", qos=2, dup=True, retain=False, pack_identifier=0x0000)
        self.assertRaises(MQTTException, self.do_check, pkg)

    def test_invalid_qos2(self):
        pkg = Publish(topic="/test", msg="test", qos=2, dup=True, retain=False)
        self.assertRaises(MQTTException, self.do_check, pkg)


class PubAckTestCase(TestCase):

    def do_check(self, pkg):
        pkg.check_integrity()

    def test_invalid_flags(self):
        pkg = PubAck(pack_identifier=0x1234)
        for f in range(int('1111', 2)):
            pkg.flags = f+1
            self.assertRaises(MQTTException, self.do_check, pkg)

    def test_invalid_ack(self):
        pkg = PubAck(pack_identifier=None)
        self.assertRaises(MQTTException, self.do_check, pkg)

    def test_valid_ack(self):
        pkg = PubAck(pack_identifier=0x1234)
        self.do_check(pkg)


class PubRecTestCase(TestCase):

    def do_check(self, pkg):
        pkg.check_integrity()

    def test_invalid_flags(self):
        pkg = PubRec(pack_identifier=0x1234)
        for f in range(int('1111', 2)):
            pkg.flags = f+1
            self.assertRaises(MQTTException, self.do_check, pkg)

    def test_invalid_ack(self):
        pkg = PubRec(pack_identifier=None)
        self.assertRaises(MQTTException, self.do_check, pkg)

    def test_valid_ack(self):
        pkg = PubRec(pack_identifier=0x1234)
        self.do_check(pkg)


class PubRelTestCase(TestCase):

    def do_check(self, pkg):
        pkg.check_integrity()

    def test_invalid_flags(self):
        pkg = PubRel(pack_identifier=0x1234)
        for f in range(int('1111', 2)):
            pkg.flags = f+1
            if pkg.flags == MQTTFlagsTable[pkg.ctl]:
                pkg.flags = 0x0000
            self.assertRaises(MQTTException, self.do_check, pkg)

    def test_invalid_ack(self):
        pkg = PubRel(pack_identifier=None)
        self.assertRaises(MQTTException, self.do_check, pkg)

    def test_valid_ack(self):
        pkg = PubRel(pack_identifier=0x1234)
        self.do_check(pkg)


class PubCompTestCase(TestCase):

    def do_check(self, pkg):
        pkg.check_integrity()

    def test_invalid_flags(self):
        pkg = PubComp(pack_identifier=0x1234)
        for f in range(int('1111', 2)):
            pkg.flags = f+1
            self.assertRaises(MQTTException, self.do_check, pkg)

    def test_invalid_ack(self):
        pkg = PubComp(pack_identifier=None)
        self.assertRaises(MQTTException, self.do_check, pkg)

    def test_valid_ack(self):
        pkg = PubComp(pack_identifier=0x1234)
        self.do_check(pkg)


class SubscribeTestCase(TestCase):

    def do_check(self, pkg):
        pkg.check_integrity()

    def test_invalid_flags(self):
        pkg = Subscribe()
        for f in range(int('1111', 2)):
            pkg.flags = f+1
            if pkg.flags == MQTTFlagsTable[pkg.ctl]:
                pkg.flags = 0x0000
            self.assertRaises(MQTTException, self.do_check, pkg)

    def test_invalid_topics(self):
        pkg = Subscribe()
        pkg.add_topic('', MQTT_QoS0)
        for topic in TopicModelsTestCase.WRONG_TOPIC_MULTI_WILDCARD:
            pkg.add_topic(topic, MQTT_QoS0)
        for topic in TopicModelsTestCase.WRONG_TOPIC_SIMPLE_WILDCARD:
            pkg.add_topic(topic, MQTT_QoS0)
        self.do_check(pkg)

    def test_invalid_qos(self):
        pkg = Subscribe()
        pkg.add_topic('/test', 0x03)
        pkg.add_topic('/test', 0x0f)
        self.assertRaises(MQTTException, self.do_check, pkg)


class SubAckTestCase(TestCase):

    def do_check(self, pkg):
        pkg.check_integrity()

    def test_invalid_flags(self):
        pkg = SubAck(pack_identifier=0x1234)
        for f in range(int('1111', 2)):
            pkg.flags = f+1
            self.assertRaises(MQTTException, self.do_check, pkg)

    def test_invalid_code(self):
        pkg = SubAck(pack_identifier=0x1234)
        pkg.add_response(0xff)
        self.assertRaises(MQTTException, self.do_check, pkg)

    def test_valid(self):
        pkg = SubAck(pack_identifier=0x1234)
        pkg.add_response(MQTT_SUBACK_QoS0)
        pkg.add_response(MQTT_SUBACK_QoS1)
        pkg.add_response(MQTT_SUBACK_QoS2)
        pkg.add_response(MQTT_SUBACK_FAILURE)
        self.do_check(pkg)


class UnsubscribeTestCase(TestCase):

    def do_check(self, pkg):
        pkg.check_integrity()

    def test_invalid_flags(self):
        pkg = Unsubscribe()
        for f in range(int('1111', 2)):
            pkg.flags = f+1
            if pkg.flags == MQTTFlagsTable[pkg.ctl]:
                pkg.flags = 0x0000
            self.assertRaises(MQTTException, self.do_check, pkg)

    def test_invalid_topics(self):
        pkg = Unsubscribe()
        pkg.add_topic('')
        for topic in TopicModelsTestCase.WRONG_TOPIC_MULTI_WILDCARD:
            pkg.add_topic(topic)
        for topic in TopicModelsTestCase.WRONG_TOPIC_SIMPLE_WILDCARD:
            pkg.add_topic(topic)
        self.do_check(pkg)


class PingReqTestCase(TestCase):

    def do_check(self, pkg):
        pkg.check_integrity()

    def test_invalid_flags(self):
        pkg = PingReq()
        for f in range(int('1111', 2)):
            pkg.flags = f+1
            self.assertRaises(MQTTException, self.do_check, pkg)

    def test_valid(self):
        pkg = PingReq()
        self.do_check(pkg)


class PingRespTestCase(TestCase):

    def do_check(self, pkg):
        pkg.check_integrity()

    def test_invalid_flags(self):
        pkg = PingResp()
        for f in range(int('1111', 2)):
            pkg.flags = f+1
            self.assertRaises(MQTTException, self.do_check, pkg)

    def test_valid(self):
        pkg = PingResp()
        self.do_check(pkg)


class DisconnectTestCase(TestCase):

    def do_check(self, pkg):
        pkg.check_integrity()

    def test_invalid_flags(self):
        pkg = Disconnect()
        for f in range(int('1111', 2)):
            pkg.flags = f+1
            self.assertRaises(MQTTException, self.do_check, pkg)

    def test_valid(self):
        pkg = Disconnect()
        self.do_check(pkg)
