from __future__ import absolute_import

from django.utils.translation import ugettext_lazy as _
from django.core.management.base import BaseCommand, CommandError

from django_mqtt.server.packets import *

import socket


def gen_empty_conn_clientId():
    mqtt_packers = []
    mqtt_packers.append(MQTTConnect(""))
    mqtt_packers.append(MQTTConnect("", keep_alive=0x00))
    mqtt_packers.append(MQTTConnect("", proto_level=0x00))
    mqtt_packers.append(MQTTConnect("", topic="/test/"))
    mqtt_packers.append(MQTTConnect("", msg="test"))
    mqtt_packers.append(MQTTConnect("", topic="/test/", msg="test"))
    mqtt_packers.append(MQTTConnect("", auth_name="user"))
    mqtt_packers.append(MQTTConnect("", auth_password="pasword"))

    wrong_flag = MQTTConnect("")
    wrong_flag.flags = 0x1
    mqtt_packers.append(wrong_flag)
    wrong_flag = MQTTConnect("", topic="/test/")
    wrong_flag.flags = 0x1
    mqtt_packers.append(wrong_flag)
    wrong_flag = MQTTConnect("", msg="test")
    wrong_flag.flags = 0x1
    mqtt_packers.append(wrong_flag)
    wrong_flag = MQTTConnect("", topic="/test/", msg="test")
    wrong_flag.flags = 0x1
    mqtt_packers.append(wrong_flag)
    wrong_flag = MQTTConnect("", auth_name="user")
    wrong_flag.flags = 0x1
    mqtt_packers.append(wrong_flag)
    wrong_flag = MQTTConnect("", auth_password="pasword")
    wrong_flag.flags = 0x1
    mqtt_packers.append(wrong_flag)
    wrong_flag = MQTTConnect("", topic="/test/")
    wrong_flag.flags = 0x1
    mqtt_packers.append(wrong_flag)

    wrong_flag = MQTTConnect("")
    wrong_flag.set_flags(name=True)
    mqtt_packers.append(wrong_flag)
    wrong_flag = MQTTConnect("")
    wrong_flag.set_flags(name=True, password=True)
    mqtt_packers.append(wrong_flag)
    wrong_flag = MQTTConnect("")
    wrong_flag.set_flags(name=True, password=True, retain=True)
    mqtt_packers.append(wrong_flag)
    wrong_flag = MQTTConnect("")
    wrong_flag.set_flags(name=True, password=True, retain=True, qos=int('11', 2))
    mqtt_packers.append(wrong_flag)
    wrong_flag = MQTTConnect("")
    wrong_flag.set_flags(name=True, password=True, retain=True, qos=int('11', 2), flag=True)
    mqtt_packers.append(wrong_flag)
    wrong_flag = MQTTConnect("")
    wrong_flag.set_flags(name=True, password=True, retain=True, qos=int('11', 2), flag=True, clean=True)
    mqtt_packers.append(wrong_flag)

    return mqtt_packers


def gen_empty_conn_clientId():
    mqtt_packers = []
    mqtt_packers.append(MQTTConnect("test"))
    mqtt_packers.append(MQTTConnect("test", keep_alive=0x00))
    mqtt_packers.append(MQTTConnect("test", proto_level=0x00))
    mqtt_packers.append(MQTTConnect("test", topic="/test/"))
    mqtt_packers.append(MQTTConnect("test", msg="test"))
    mqtt_packers.append(MQTTConnect("test", auth_name="user"))
    mqtt_packers.append(MQTTConnect("test", auth_password="pasword"))
    return mqtt_packers



class Command(BaseCommand):
    help = _('Server protocol test')

    def add_arguments(self, parser):
        parser.add_argument('host', action='store',
                            type=str, dest='host', required=True,
                            help=unicode(_('Sibcribe topic'))
                            )
        parser.add_argument('--port', nargs='?', action='store',
                            type=int, default=None, dest='port',
                            help=unicode(_('Host port, 1883 or 8883 if --ssl'))
                            )
        parser.add_argument('--ssl', nargs=0, action='store_true',
                            type=bool, default=False, dest='ssl',
                            help=unicode(_('User SSL'))
                            )

    def handle(self, *args, **options):
        port = options['port']
        if options['ssl']:
            if port is None:
                port = 8883
        if port is None:
            port = 1883
        server_data = (options['host'], port)
        pass

    def test_wrong_connect(self, server):
        pass

    def test_wrong_connect(self, server):
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.connect(server)

        unicode(mqtt_conn)
        conn.sendall('Hello, world')
        data = s.recv(1024)

