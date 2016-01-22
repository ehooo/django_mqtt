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

    def payload(self):
        if self.ctl in [MQTT_CTRL_CONNACK, MQTT_CTRL_PUBACK, MQTT_CTRL_PUBREC,
                        MQTT_CTRL_PUBREL, MQTT_CTRL_PUBCOMP, MQTT_CTRL_UNSUBACK,
                        MQTT_CTRL_PINGREQ, MQTT_CTRL_PINGRESP, MQTT_CTRL_DISCONNECT]:
            return ""
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
        self.flags |= (self._QoS << 1)

    def payload(self):
        return ""

    def __unicode__(self):
        ret = struct.pack("!B", self.header)
        ret += self.get_remaining(0)
        return ret


class MQTTOnlyPackID(MQTTEmpty):

    def __unicode__(self):
        msg = struct.pack("!H", self.pack_identifier)

        ret = struct.pack("!B", self.header)
        ret += self.get_remaining(msg)
        ret += msg
        return ret


class MQTTConnect(BaseMQTT):
    def __init__(self, clientId, keep_alive=0x00, proto_level=0x04):
        super(BaseMQTT, self).__init__(MQTT_CTRL_CONNECT)
        self._QoS = MQTT_QoS0
        self.proto_name = gen_string("MQTT")
        self.proto_level = proto_level
        self.conn_flags = 0x00
        self.keep_alive = keep_alive
        self.clientId = clientId
        self.topic = ""
        self.msg = ""
        self.auth_name = ""
        self.auth_password = ""

    def set_flags(self, name=False, password=False, retain=False, qos=None, flag=False, clean=False):
        if name:
            self.conn_flags |= MQTT_CONN_FLAGS_NAME
        elif name is None:
            self.conn_flags ^= MQTT_CONN_FLAGS_NAME
        if password:
            self.conn_flags |= MQTT_CONN_FLAGS_PASSWORD
        elif password is None:
            self.conn_flags ^= MQTT_CONN_FLAGS_PASSWORD
        if retain:
            self.conn_flags |= MQTT_CONN_FLAGS_RETAIN
        elif retain is None:
            self.conn_flags ^= MQTT_CONN_FLAGS_RETAIN
        if flag:
            self.conn_flags |= MQTT_CONN_FLAGS_FLAG
        elif flag is None:
            self.conn_flags ^= MQTT_CONN_FLAGS_FLAG
        if clean:
            self.conn_flags |= MQTT_CONN_FLAGS_CLEAN
        elif clean is None:
            self.conn_flags ^= MQTT_CONN_FLAGS_CLEAN
        if qos:
            self.conn_flags = (self.conn_flags & ~(int('11', 2) << 3))
            self._QoS = (qos & int('11', 2))

        self.conn_flags |= (self._QoS << 3)

    def payload(self, ignore_flags=False, exception=False):
        payload = gen_string(self.clientId)
        if ignore_flags or not (self.conn_flags & MQTT_CONN_FLAGS_CLEAN):
            if exception and len(self.clientId) == 0:
                raise ValueError("ClientIds must be between 1 and 23")
        if ignore_flags or self.conn_flags & MQTT_CONN_FLAGS_RETAIN:
            payload += gen_string(self.topic)
            payload += gen_string(self.msg)
        if ignore_flags or self.conn_flags & MQTT_CONN_FLAGS_NAME:
            payload += gen_string(self.auth_name)
        if ignore_flags or self.conn_flags & MQTT_CONN_FLAGS_PASSWORD:
            payload += gen_string(self.auth_password)
        return payload

    def __unicode__(self):
        msg = self.proto_name
        msg += struct.pack("!B", self.proto_level)
        msg += struct.pack("!B", self.conn_flags)
        msg += struct.pack("!H", self.keep_alive)
        msg += self.payload()

        ret = struct.pack("!B", self.header)
        ret += self.get_remaining(msg)
        ret += msg
        return ret


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

    def __unicode__(self):
        msg = struct.pack("!B", self.conn_flags)
        msg += struct.pack("!B", self.ret_code)

        ret = struct.pack("!B", self.header)
        ret += self.get_remaining(msg)
        ret += msg
        return ret


class MQTTPublish(BaseMQTT):
    def __init__(self, qos=None, dup=False, retain=False):
        super(BaseMQTT, self).__init__(MQTT_CTRL_PUBLISH)
        if qos is None:
            qos = MQTT_QoS0
        self.set_flags(qos, dup, retain)
        self.topic = ""
        self.msg = ""

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
        self.flags |= (self._QoS << 1)

    def payload(self, ignore_flags=False, exception=False):
        return gen_string(self.msg)

    def __unicode__(self):
        msg = gen_string(self.topic)
        if self._QoS != MQTT_QoS0:
            msg += struct.pack("!H", self.pack_identifier)
        msg += self.payload()

        ret = struct.pack("!B", self.header)
        ret += self.get_remaining(msg)
        ret += msg
        return ret


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

    def __unicode__(self):
        msg = struct.pack("!H", self.pack_identifier)
        for topic in self.topic_list:
            msg += gen_string(topic)
            msg += struct.pack("!B", self.topic_list[topic])

        ret = struct.pack("!B", self.header)
        ret += self.get_remaining(msg)
        ret += msg
        return ret


class MQTTSubAck(BaseMQTT):
    def __init__(self):
        super(BaseMQTT, self).__init__(MQTT_CTRL_SUBACK)
        self.code_list = []

    def add_response(self, response_code):
        self.code_list.append(response_code)

    def __unicode__(self):
        msg = struct.pack("!H", self.pack_identifier)
        for code in self.code_list:
            msg += struct.pack("!B", code)

        ret = struct.pack("!B", self.header)
        ret += self.get_remaining(msg)
        ret += msg
        return ret


class MQTTUnsubcribe(BaseMQTT):
    def __init__(self):
        super(BaseMQTT, self).__init__(MQTT_CTRL_UNSUBSCRIBE)
        self.topic_list = []

    def add_topic(self, topic):
        self.topic_list.append(topic)

    def __unicode__(self):
        msg = struct.pack("!H", self.pack_identifier)
        for topic in self.topic_list:
            msg += gen_string(topic)

        ret = struct.pack("!B", self.header)
        ret += self.get_remaining(msg)
        ret += msg
        return ret


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

