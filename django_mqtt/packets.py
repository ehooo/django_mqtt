from .protocol import *
import struct
import os


class BaseMQTT():
    def __init__(self, ctl):
        self.ctl = ctl
        self.flags = 0x00
        if ctl in MQTTFlagsTable and MQTTFlagsTable[ctl]:
            self.flags = MQTTFlagsTable[ctl]
        self._pkgID = None
        self._QoS = None
        self._header = None

    @property
    def header(self):
        if self._header is None:
            return (self.ctl << 4) | self.flags
        return self._header

    @property
    def pack_identifier(self):
        if self._pkgID is None:
            if self.ctl in [MQTT_CTRL_SUBSCRIBE, MQTT_CTRL_UNSUBSCRIBE,
                            MQTT_CTRL_PUBACK, MQTT_CTRL_PUBREC,
                            MQTT_CTRL_PUBREL, MQTT_CTRL_PUBCOMP,
                            MQTT_CTRL_SUBACK, MQTT_CTRL_UNSUBACK,
                            MQTT_CTRL_PUBLISH]:
                self._pkgID = os.urandom(16)
                while self._pkgID != 0:
                    if self.ctl == MQTT_CTRL_PUBLISH and self.get_QoS() != 0:
                        break
                    elif self.ctl not in [MQTT_CTRL_SUBSCRIBE, MQTT_CTRL_UNSUBSCRIBE]:
                        break
                    self._pkgID = os.urandom(16)
        return self._pkgID

    def set_pack_identifier(self, pkgID):
        self._pkgID = pkgID

    def get_QoS(self):
        if self._QoS is None:
            return (self.flags & int('0110', 2)) >> 1
        return self._QoS

    def get_remaining(self, msg):
        return int2remaining(len(msg))

    def set_flags(self, *args, **kwargs):
        raise NotImplemented

    def variable_header(self):
        if self.ctl in [MQTT_CTRL_PUBACK, MQTT_CTRL_PUBREC, MQTT_CTRL_PUBREL, MQTT_CTRL_PUBCOMP,
                        MQTT_CTRL_SUBSCRIBE, MQTT_CTRL_SUBACK, MQTT_CTRL_UNSUBSCRIBE, MQTT_CTRL_UNSUBACK]:
            return struct.pack("!H", self.pack_identifier)
        raise NotImplemented

    def payload(self):
        if self.ctl in [MQTT_CTRL_CONNACK, MQTT_CTRL_PUBACK, MQTT_CTRL_PUBREC,
                        MQTT_CTRL_PUBREL, MQTT_CTRL_PUBCOMP, MQTT_CTRL_UNSUBACK,
                        MQTT_CTRL_PINGREQ, MQTT_CTRL_PINGRESP, MQTT_CTRL_DISCONNECT]:
            return ""
        raise NotImplemented

    def __unicode__(self):
        msg = self.variable_header()
        msg += self.payload()

        ret = struct.pack("!B", self.header)
        ret += self.get_remaining(msg)
        ret += msg
        return ret

    def parse_body(self, body):
        raise NotImplemented


class MQTTEmpty(BaseMQTT):

    def set_flags(self, qos=None, dup=False, retain=False):
        if dup:
            self.flags |= MQTTFlagsDUP
        elif dup is None:
            self.flags ^= MQTTFlagsDUP
        if retain:
            self.flags |= MQTTFlagsRETAIN
        elif retain is None:
            self.flags ^= MQTTFlagsRETAIN
        if qos:
            self.flags = (self.flags & ~(int('11', 2) << 1))
            self._QoS = (qos & int('11', 2))
        if self._QoS is None:
            self._QoS = MQTT_QoS0
        self.flags |= (self._QoS << 1)

    def payload(self):
        return ""

    def parse_body(self, body):
        if body or len(body) > 0:
            raise ValueError('Body must be empty')


class MQTTOnlyPackID(MQTTEmpty):

    def variable_header(self):
        return struct.pack("!H", self.pack_identifier)

    def parse_body(self, body):
        (self._pkgID, ) = struct.unpack("!H", body)


class MQTTConnect(BaseMQTT):
    def __init__(self, clientId=None, qos=None, keep_alive=0x0f, proto_level=0x04,
                 topic="", msg="", auth_name=None, auth_password=None):
        super(BaseMQTT, self).__init__(MQTT_CTRL_CONNECT)
        self.proto_name = gen_string("MQTT")
        self.proto_level = proto_level
        self.conn_flags = 0x00
        self.keep_alive = keep_alive
        self.clientId = clientId
        self._topic = topic
        self._msg = msg
        flags = {}
        if self._msg or self._topic:
            flags['retain'] = True
        flags['qos'] = qos
        flags['name'] = auth_name
        flags['password'] = auth_password
        self.auth_name = None
        self.auth_password = None
        self.set_flags(**flags)

    @property
    def msg(self):
        return self._msg
    @msg.setter
    def set_msg(self, msg):
        if msg is None:
            msg = ""
        if msg or self._topic:
            self.set_flags(retain=True)
        else:
            self.set_flags(retain=False)
        self._msg = msg

    @property
    def topic(self):
        return self._topic
    @msg.setter
    def set_topic(self, topic):
        if topic is None:
            topic = ""
        if topic or self._msg:
            self.set_flags(retain=True)
        else:
            self.set_flags(retain=False)
        self._topic = topic

    def set_flags(self, name=None, password=None, retain=None, qos=None, flag=None, clean=None):
        if name:
            self.conn_flags |= MQTT_CONN_FLAGS_NAME
            self.auth_name = unicode(name)
        elif name is not None:
            self.conn_flags ^= MQTT_CONN_FLAGS_NAME
        if password:
            self.conn_flags |= MQTT_CONN_FLAGS_PASSWORD
            self.auth_password = unicode(password)
        elif password is not None:
            self.conn_flags ^= MQTT_CONN_FLAGS_PASSWORD
        if retain:
            self.conn_flags |= MQTT_CONN_FLAGS_RETAIN
        elif retain is not None:
            self.conn_flags ^= MQTT_CONN_FLAGS_RETAIN
        if flag:
            self.conn_flags |= MQTT_CONN_FLAGS_FLAG
        elif flag is not None:
            self.conn_flags ^= MQTT_CONN_FLAGS_FLAG
        if clean:
            self.conn_flags |= MQTT_CONN_FLAGS_CLEAN
        elif clean is not None:
            self.conn_flags ^= MQTT_CONN_FLAGS_CLEAN
        if qos:
            self.conn_flags = (self.conn_flags & ~(int('11', 2) << 3))
            self._QoS = (qos & int('11', 2))
        if self._QoS is None:
            self._QoS = MQTT_QoS0

        self.conn_flags |= (self._QoS << 3)

    def payload(self, ignore_flags=False, exception=False):
        payload = gen_string(self.clientId)
        if ignore_flags or not (self.conn_flags & MQTT_CONN_FLAGS_CLEAN):
            if exception and self.clientId and len(self.clientId) == 0:
                raise ValueError("ClientIds must be between 1 and 23")
        if ignore_flags or self.conn_flags & MQTT_CONN_FLAGS_RETAIN:
            payload += gen_string(self._topic)
            payload += gen_string(self._msg)
        if ignore_flags or self.conn_flags & MQTT_CONN_FLAGS_NAME:
            payload += gen_string(self.auth_name)
        if ignore_flags or self.conn_flags & MQTT_CONN_FLAGS_PASSWORD:
            payload += gen_string(self.auth_password)
        return payload

    def variable_header(self):
        msg = self.proto_name
        msg += struct.pack("!B", self.proto_level)
        msg += struct.pack("!B", self.conn_flags)
        msg += struct.pack("!H", self.keep_alive)
        return msg

    def parse_body(self, body):
        self.proto_level, self.conn_flags, self.keep_alive = struct.unpack_from("!BBH", body, 0)
        padding = 4
        if not (self.conn_flags & MQTT_CONN_FLAGS_CLEAN):
            self.clientId = get_string(body[padding:])
            (size, ) = struct.unpack_from("!H", body, padding)
            padding += 2 + size
        if self.conn_flags & MQTT_CONN_FLAGS_RETAIN:
            self._topic = get_string(body[padding:])
            (size, ) = struct.unpack_from("!H", body, padding)
            padding += 2 + size
            self._msg = get_string(body[padding:])
            (size, ) = struct.unpack_from("!H", body, padding)
            padding += 2 + size
        if self.conn_flags & MQTT_CONN_FLAGS_NAME:
            self.auth_name = get_string(body[padding:])
            (size, ) = struct.unpack_from("!H", body, padding)
            padding += 2 + size
        if self.conn_flags & MQTT_CONN_FLAGS_PASSWORD:
            self.auth_password = get_string(body[padding:])
            (size, ) = struct.unpack_from("!H", body, padding)
            padding += 2 + size
        if len(body) > padding:
            raise ValueError('Body too big')


class MQTTConnAck(BaseMQTT):
    def __init__(self):
        super(BaseMQTT, self).__init__(MQTT_CTRL_CONNACK)
        self.conn_flags = 0x00
        self.ret_code = MQTT_CONN_OK

    def set_flags(self, sp=False):
        self.conn_flags = 0
        if sp:
            self.conn_flags |= MQTT_CONN_FLAGS_SESSION_PRESENT
        else:
            self.conn_flags ^= MQTT_CONN_FLAGS_SESSION_PRESENT

    def variable_header(self):
        msg = struct.pack("!B", self.conn_flags)
        msg += struct.pack("!B", self.ret_code)
        return msg

    def parse_body(self, body):
        self.conn_flags, self.ret_code = struct.unpack("!BB", body)


class MQTTPublish(BaseMQTT):
    def __init__(self, topic="", msg="", qos=None, dup=False, retain=False):
        super(BaseMQTT, self).__init__(MQTT_CTRL_PUBLISH)
        self.set_flags(qos, dup, retain)
        self.topic = topic
        self.msg = msg

    def set_flags(self, qos=None, dup=None, retain=None):
        if dup:
            self.flags |= MQTTFlagsDUP
        elif dup is not None:
            self.flags ^= MQTTFlagsDUP
        if retain:
            self.flags |= MQTTFlagsRETAIN
        elif retain is not None:
            self.flags ^= MQTTFlagsRETAIN
        if qos:
            self.flags = (self.flags & ~(int('11', 2) << 1))
            self._QoS = (qos & int('11', 2))
        if self._QoS is None:
            self._QoS = MQTT_QoS0
        self.flags |= (self._QoS << 1)

    def payload(self, ignore_flags=False, exception=False):
        return gen_string(self.msg)

    def variable_header(self):
        msg = gen_string(self.topic)
        if self.get_QoS() != MQTT_QoS0:
            msg += struct.pack("!H", self.pack_identifier)
        return msg

    def parse_body(self, body):
        self.topic = get_string(body)
        padding = 0
        (size, ) = struct.unpack_from("!H", body, padding)
        padding += 2 + size
        if self.get_QoS() != MQTT_QoS0:
            (self._pkgID, ) = struct.unpack_from("!H", body[padding:])
            padding += 2
        self.msg = get_string(body[padding:])
        (size, ) = struct.unpack_from("!H", body, padding)
        padding += 2 + size
        if len(body) > padding:
            raise ValueError('Body too big')


class MQTTPubAck(MQTTOnlyPackID):
    def __init__(self):
        super(MQTTOnlyPackID, self).__init__(MQTT_CTRL_PUBACK)
        self._QoS = MQTT_QoS1


class MQTTPubRec(MQTTOnlyPackID):
    def __init__(self):
        super(MQTTOnlyPackID, self).__init__(MQTT_CTRL_PUBREC)
        self._QoS = MQTT_QoS2


class MQTTPubRel(MQTTOnlyPackID):
    def __init__(self):
        super(MQTTOnlyPackID, self).__init__(MQTT_CTRL_PUBREL)
        self._QoS = MQTT_QoS2


class MQTTPubComp(MQTTOnlyPackID):
    def __init__(self):
        super(MQTTOnlyPackID, self).__init__(MQTT_CTRL_PUBCOMP)
        self._QoS = MQTT_QoS2


class MQTTSubcribe(BaseMQTT):
    def __init__(self):
        super(BaseMQTT, self).__init__(MQTT_CTRL_SUBSCRIBE)
        self.topic_list = {}

    def add_topic(self, topic, qos):
        self.topic_list[topic] = (qos & int('11', 2))

    def variable_header(self):
        return struct.pack("!H", self.pack_identifier)

    def payload(self):
        msg = ''
        for topic in self.topic_list:
            msg += gen_string(topic)
            msg += struct.pack("!B", self.topic_list[topic])
        return msg

    def parse_body(self, body):
        padding = 0
        (self._pkgID, ) = struct.unpack_from("!H", body, padding)
        padding += 2
        while padding < len(body):
            topic = get_string(body[padding:])
            (size, ) = struct.unpack_from("!H", body, padding)
            padding += 2 + size
            (qos, ) = struct.unpack_from("!B", body, padding)
            padding += 1
            self.add_topic(topic, qos)
        if len(body) > padding:
            raise ValueError('Body too big')


class MQTTSubAck(BaseMQTT):
    def __init__(self):
        super(BaseMQTT, self).__init__(MQTT_CTRL_SUBACK)
        self.code_list = []

    def add_response(self, response_code):
        self.code_list.append(response_code)

    def variable_header(self):
        return struct.pack("!H", self.pack_identifier)

    def payload(self):
        msg = ''
        for code in self.code_list:
            msg += struct.pack("!B", code)
        return msg

    def parse_body(self, body):
        padding = 0
        (self._pkgID, ) = struct.unpack_from("!H", body, padding)
        padding += 2
        while padding < len(body):
            (response_code, ) = struct.unpack_from("!B", body, padding)
            padding += 1
            self.add_response(response_code)
        if len(body) > padding:
            raise ValueError('Body too big')



class MQTTUnsubcribe(BaseMQTT):
    def __init__(self):
        super(BaseMQTT, self).__init__(MQTT_CTRL_UNSUBSCRIBE)
        self.topic_list = []

    def add_topic(self, topic):
        self.topic_list.append(topic)

    def variable_header(self):
        return struct.pack("!H", self.pack_identifier)

    def payload(self):
        msg = ''
        for topic in self.topic_list:
            msg += gen_string(topic)
        return msg

    def parse_body(self, body):
        padding = 0
        (self._pkgID, ) = struct.unpack_from("!H", body, padding)
        padding += 2
        while padding < len(body):
            topic = get_string(body[padding:])
            (size, ) = struct.unpack_from("!H", body, padding)
            padding += 2 + size
            self.add_topic(topic)
        if len(body) > padding:
            raise ValueError('Body too big')


class MQTTUnsubAck(MQTTOnlyPackID):
    def __init__(self):
        super(MQTTOnlyPackID, self).__init__(MQTT_CTRL_UNSUBACK)


class MQTTPingReq(MQTTEmpty):
    def __init__(self):
        super(BaseMQTT, self).__init__(MQTT_CTRL_PINGREQ)


class MQTTPingResp(MQTTEmpty):
    def __init__(self):
        super(BaseMQTT, self).__init__(MQTT_CTRL_PINGRESP)


class MQTTDisconect(MQTTEmpty):
    def __init__(self):
        super(BaseMQTT, self).__init__(MQTT_CTRL_DISCONNECT)


MQTTClassTable = {
    MQTT_CTRL_CONNECT: MQTTConnect,
    MQTT_CTRL_CONNACK: MQTTConnAck,
    MQTT_CTRL_PUBLISH: MQTTPublish,
    MQTT_CTRL_PUBACK: MQTTPubAck,
    MQTT_CTRL_PUBREC: MQTTPubRec,
    MQTT_CTRL_PUBREL: MQTTPubRel,
    MQTT_CTRL_PUBCOMP: MQTTPubComp,
    MQTT_CTRL_SUBSCRIBE: MQTTSubcribe,
    MQTT_CTRL_SUBACK: MQTTSubAck,
    MQTT_CTRL_UNSUBSCRIBE: MQTTUnsubcribe,
    MQTT_CTRL_UNSUBACK: MQTTUnsubAck,
    MQTT_CTRL_PINGREQ: MQTTPingReq,
    MQTT_CTRL_PINGRESP: MQTTPingResp,
    MQTT_CTRL_DISCONNECT: MQTTDisconect
}


def parse_raw(connection):
    header = connection.recv(1)
    ctrl = header & 0xf0
    flags = header & 0x0f

    remain = 0
    multiplier = 1
    read = connection.recv(1)
    while read > 0x7f:
        remain += (read & 127) * multiplier
        multiplier *= 128
        read = connection.recv(1)
    remain += (read & 127) * multiplier
    body = connection.recv(remain)

    if ctrl not in MQTTClassTable:
        return
    cls = MQTTClassTable[ctrl]()
    cls.flags = flags
    cls.parse_body(body)
    return cls
