import struct
import six

MQTT_CTRL_CONNECT = 1
MQTT_CTRL_CONNACK = 2
MQTT_CTRL_PUBLISH = 3
MQTT_CTRL_PUBACK = 4
MQTT_CTRL_PUBREC = 5
MQTT_CTRL_PUBREL = 6
MQTT_CTRL_PUBCOMP = 7
MQTT_CTRL_SUBSCRIBE = 8
MQTT_CTRL_SUBACK = 9
MQTT_CTRL_UNSUBSCRIBE = 10
MQTT_CTRL_UNSUBACK = 11
MQTT_CTRL_PINGREQ = 12
MQTT_CTRL_PINGRESP = 13
MQTT_CTRL_DISCONNECT = 14

MQTTTypes = [
    0,
    MQTT_CTRL_CONNECT,
    MQTT_CTRL_CONNACK,
    MQTT_CTRL_PUBLISH,
    MQTT_CTRL_PUBACK,
    MQTT_CTRL_PUBREC,
    MQTT_CTRL_PUBREL,
    MQTT_CTRL_PUBCOMP,
    MQTT_CTRL_SUBSCRIBE,
    MQTT_CTRL_SUBACK,
    MQTT_CTRL_UNSUBSCRIBE,
    MQTT_CTRL_UNSUBACK,
    MQTT_CTRL_PINGREQ,
    MQTT_CTRL_PINGRESP,
    MQTT_CTRL_DISCONNECT,
    15
]

MQTT_QoS0 = int('00', 2)
MQTT_QoS1 = int('01', 2)
MQTT_QoS2 = int('10', 2)

MQTTQoS = [MQTT_QoS0, MQTT_QoS1, MQTT_QoS2, int('11', 2)]

MQTTFlagsDUP = int('1000', 2)
MQTTFlagsQoS = int('0110', 2)
MQTTFlagsRETAIN = int('0001', 2)

MQTTFlagsTable = {
    MQTT_CTRL_CONNECT: int('0000', 2),
    MQTT_CTRL_CONNACK: int('0000', 2),
    MQTT_CTRL_PUBLISH: None,
    MQTT_CTRL_PUBACK: int('0000', 2),
    MQTT_CTRL_PUBREC: int('0000', 2),
    MQTT_CTRL_PUBREL: int('0010', 2),
    MQTT_CTRL_PUBCOMP: int('0000', 2),
    MQTT_CTRL_SUBSCRIBE: int('0010', 2),
    MQTT_CTRL_SUBACK: int('0000', 2),
    MQTT_CTRL_UNSUBSCRIBE: int('0010', 2),
    MQTT_CTRL_UNSUBACK: int('0000', 2),
    MQTT_CTRL_PINGREQ: int('0000', 2),
    MQTT_CTRL_PINGRESP: int('0000', 2),
    MQTT_CTRL_DISCONNECT: int('0000', 2)
}

MQTT_CONN_FLAGS_NAME = int('10000000', 2)
MQTT_CONN_FLAGS_PASSWORD = int('01000000', 2)
MQTT_CONN_FLAGS_RETAIN = int('00100000', 2)
MQTT_CONN_FLAGS_QoS = int('00011000', 2)
MQTT_CONN_FLAGS_FLAG = int('00000100', 2)
MQTT_CONN_FLAGS_CLEAN = int('00000010', 2)

MQTT_CONN_FLAGS_SESSION_PRESENT = int('00000001', 2)

MQTT_CONN_OK = 0x00
MQTT_CONN_UNACCEPTABLE_PROTO = 0x01
MQTT_CONN_ID_REJECT = 0x02
MQTT_CONN_SERVER_UNAVAILABLE = 0x03
MQTT_CONN_BAD_AUTH = 0x04
MQTT_CONN_NOT_AUTH = 0x05

MQTT_SUBACK_QoS0 = MQTT_QoS0
MQTT_SUBACK_QoS1 = MQTT_QoS1
MQTT_SUBACK_QoS2 = MQTT_QoS2
MQTT_SUBACK_FAILURE = 0x80


def remaining2list(remain):
    bytes_remain = []
    dec = int(remain)
    while dec > 0:
        _enc = int(dec % 128)
        dec = int(dec / 128)
        if dec > 0:
            _enc = int(_enc | 128)
        bytes_remain.append(_enc)
    return bytes_remain


def int2remaining(remain):
    bytes_remain = remaining2list(remain)
    fmt = "!"+("B"*len(bytes_remain))
    return struct.pack(fmt, *bytes_remain)


def get_remaining(buff, exception=False):
    byte_size = struct.calcsize("!B")
    multiplier = 1
    end = 0
    remain = 0
    try:
        read, = struct.unpack_from("!B", buff, end * byte_size)
        while read > 0x7f:
            remain += (read & 127) * multiplier
            multiplier *= 128
            end += 1
            read, = struct.unpack_from("!B", buff, end * byte_size)
        remain += (read & 127) * multiplier
    except struct.error as ex:
        if exception:
            raise ex
    return remain


def get_string(buff):
    str_size, = struct.unpack_from("!H", buff)
    fmt = "!"+("B"*str_size)
    str_bytes = struct.unpack_from(fmt, buff, struct.calcsize("!H"))
    uni_str = six.StringIO()
    for char in str_bytes:
        uni_str.write(unichr(char))
    return uni_str.getvalue()


def gen_string(uni_str):
    str_size = len(uni_str)
    fmt = "!H"+("B"*str_size)
    byte_str = map(lambda x: ord(x), uni_str)
    return struct.pack(fmt, str_size, *byte_str)

