from django.test import TestCase
from django_mqtt.publisher.models import *
from django_mqtt.server.service import *
from django_mqtt.server.packets import *
from threading import Thread


class FakeServer(Thread):
    is_running = False

    def run(self):
        try:
            self.is_running = True
            self.bind_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_IP)
            self.bind_socket.bind(('127.0.0.1', 1883))
            self.bind_socket.listen(1)

            while self.is_running:
                sock, from_addr = self.bind_socket.accept()
                responser = MqttServiceThread(sock, publish_callback=None)
                responser.run()
        except socket.error as ex:
            pass
        except Exception as ex:
            logger.exception(ex)
        finally:
            self.is_running = False

    def stop(self):
        if hasattr(self, 'bind_socket'):
            self.bind_socket.close()
            del(self.bind_socket)

HOST, PORT = '127.0.0.1', 1883


class PublishTestCase(TestCase):
    def setUp(self):
        super(PublishTestCase, self).setUp()
        self.server = FakeServer()
        self.server.start()
        import time
        time.sleep(0.1)

    def tearDown(self):
        self.server.is_running = False
        self.server.stop()
        super(PublishTestCase, self).tearDown()

    def test_public(self):
        cli = mqtt.Client('test_client', clean_session=True, protocol=mqtt.MQTTv311)
        cli.connect(HOST, PORT, 255)
        (rc, mid) = cli.publish('/test/pub', 'Test in connect', MQTT_QoS2, True)
        print "rc:", rc, "\tmid:", mid

    def test_in_connect(self):
        pkg = Connect(client_id='test_client', keep_alive=255)
        pkg.set_flags(clean=True)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_IP)
        sock.connect((HOST, PORT))

        sock.sendall(str(pkg))
        self.assertRaises(MQTTException, parse_raw, sock)  # TODO FIXME
        # pkg = parse_raw(sock)
        # self.assertEqual(isinstance(pkg, ConnAck), True)
        sock.close()


class SubscriberTestCase(TestCase):
    pass
