import random
import re
import struct

import paho.mqtt.client as mqtt
import six

MQTTTypes = [
    0,
    mqtt.CONNECT,
    mqtt.CONNACK,
    mqtt.PUBLISH,
    mqtt.PUBACK,
    mqtt.PUBREC,
    mqtt.PUBREL,
    mqtt.PUBCOMP,
    mqtt.SUBSCRIBE,
    mqtt.SUBACK,
    mqtt.UNSUBSCRIBE,
    mqtt.UNSUBACK,
    mqtt.PINGREQ,
    mqtt.PINGRESP,
    mqtt.DISCONNECT,
    15
]

MQTT_CLIENT_ID_RE = re.compile('(?P<client>[0-9a-zA-Z]{1,23})')
MQTT_TOPIC_RE = re.compile(
    r'(?P<topic>(/(?=[^/]))?(?P<path>(?P<dir_name>[^+#/]+|\+)/)*(?P<end>#|\+|[^+#/]+))(?!.)',
    flags=re.DOTALL
)

MQTT_QoS0 = int('00', 2)
MQTT_QoS1 = int('01', 2)
MQTT_QoS2 = int('10', 2)

MQTTQoS = [MQTT_QoS0, MQTT_QoS1, MQTT_QoS2, int('11', 2)]

MQTTFlagsDUP = int('1000', 2)
MQTTFlagsQoS = int('0110', 2)
MQTTFlagsRETAIN = int('0001', 2)

MQTTFlagsTable = {
    mqtt.CONNECT: int('0000', 2),
    mqtt.CONNACK: int('0000', 2),
    mqtt.PUBLISH: None,
    mqtt.PUBACK: int('0000', 2),
    mqtt.PUBREC: int('0000', 2),
    mqtt.PUBREL: int('0010', 2),
    mqtt.PUBCOMP: int('0000', 2),
    mqtt.SUBSCRIBE: int('0010', 2),
    mqtt.SUBACK: int('0000', 2),
    mqtt.UNSUBSCRIBE: int('0010', 2),
    mqtt.UNSUBACK: int('0000', 2),
    mqtt.PINGREQ: int('0000', 2),
    mqtt.PINGRESP: int('0000', 2),
    mqtt.DISCONNECT: int('0000', 2)
}

MQTT_CONN_FLAGS_NAME = int('10000000', 2)
MQTT_CONN_FLAGS_PASSWORD = int('01000000', 2)
MQTT_CONN_FLAGS_RETAIN = int('00100000', 2)
MQTT_CONN_FLAGS_QoS = int('00011000', 2)
MQTT_CONN_FLAGS_FLAG = int('00000100', 2)
MQTT_CONN_FLAGS_CLEAN = int('00000010', 2)

MQTT_CONN_FLAGS_SESSION_PRESENT = int('00000001', 2)

MQTT_SUBACK_QoS0 = MQTT_QoS0
MQTT_SUBACK_QoS1 = MQTT_QoS1
MQTT_SUBACK_QoS2 = MQTT_QoS2
MQTT_SUBACK_FAILURE = 0x80

TOPIC_SEP = '/'
TOPIC_BEGINNING_DOLLAR = '$'
WILDCARD_SINGLE_LEVEL = '+'
WILDCARD_MULTI_LEVEL = '#'
MQTT_NONE_CHAR = b'\x00\x00'


def remaining2list(remain, exception=False):
    bytes_remain = []
    if not exception:
        if remain is None:
            return bytes_remain
        elif remain < 0:
            return bytes_remain
    else:
        if remain is None:
            raise TypeError('None not allowed')
        elif remain < 0:
            raise ValueError('remain must positive')
    dec = int(remain)
    if dec == 0:
        bytes_remain.append(0)
    while dec > 0:
        _enc = int(dec % 128)
        dec = int(dec / 128)
        if dec > 0:
            _enc = int(_enc | 128)
        bytes_remain.append(_enc)
    return bytes_remain


def int2remaining(remain, exception=False):
    if exception:
        if remain is None:
            raise TypeError('None not allowed')
        elif remain < 0:
            raise ValueError('remain must positive')
    bytes_remain = remaining2list(remain)
    fmt = "!"+("B"*len(bytes_remain))
    return struct.pack(fmt, *bytes_remain)


def get_remaining(buff, start_at=0, exception=False):
    if not buff:
        if exception:
            raise TypeError('required Buff')
        return None
    byte_size = struct.calcsize("!B")
    multiplier = 1
    end = start_at
    remain = 0
    try:
        read, = struct.unpack_from("!B", buff, end * byte_size)
        if read <= 0x7f:
            if 1 != len(buff):
                if exception:
                    raise struct.error('Buffer bigger than remain')
                return -1
            return read & 127
        while read > 0x7f:
            remain += (read & 127) * multiplier
            multiplier *= 128
            end += 1
            read, = struct.unpack_from("!B", buff, end * byte_size)
        end += 1
        remain += (read & 127) * multiplier
    except struct.error as ex:
        if exception:
            raise ex
        return -1
    if end != len(buff):
        if exception:
            raise struct.error
        return -1
    return remain


def get_string(buff, exception=False):
    if buff is None:
        if exception:
            raise TypeError('None not allowed')
        return ''
    if not buff or len(buff) < 2:
        if exception:
            raise TypeError('required Buff')
        return ''
    try:
        str_size, = struct.unpack_from("!H", buff[:2])
        fmt = "!"+("B"*str_size)
        utf8_str = struct.unpack_from(fmt, buff, struct.calcsize("!H"))
        if six.PY2:  # pragma: no cover
            byte_str = map(chr, utf8_str)
            utf8_str = ''.join(byte_str)
            utf8_str = utf8_str.decode('utf8')
        else:  # pragma: no cover
            utf8_str = bytes(utf8_str)
        if MQTT_NONE_CHAR in utf8_str:
            if exception:
                raise ValueError('char 0x0000 not allowed')
            utf8_str = utf8_str.replace(MQTT_NONE_CHAR, b'')
        if six.PY3:  # pragma: no cover
            utf8_str = utf8_str.decode()
        return utf8_str
    except UnicodeDecodeError as er:
        if exception:
            raise er
    except struct.error as er:
        if exception:
            raise er
    return ''


def gen_string(uni_str, exception=False):
    if uni_str is None:
        if exception:
            raise TypeError('None not allowed')
        return b''
    if not hasattr(uni_str, 'encode'):
        if exception:
            raise TypeError('uni_str required function encode(format)')
        return b''
    try:
        utf8_str = uni_str.encode('utf8')
        if MQTT_NONE_CHAR in utf8_str:
            if exception:
                raise ValueError('char 0x0000 not allowed')
            utf8_str = utf8_str.replace(MQTT_NONE_CHAR, b'')
        str_size = len(utf8_str)
        fmt = "!H"+("B"*str_size)
        if six.PY2:  # pragma: no cover
            byte_str = map(ord, utf8_str)
        else:  # pragma: no cover
            byte_str = tuple(utf8_str)
        return struct.pack(fmt, str_size, *byte_str)
    except UnicodeDecodeError as ex:
        if exception:
            raise ex
    except TypeError as ex:
        if exception:
            raise ex
    return b''


def gen_client_id():
    rand = random.SystemRandom()
    client_id = ''
    for s in range(rand.randint(1, 23)):
        client_id += rand.choice('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
    return client_id
