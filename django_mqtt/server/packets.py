from django_mqtt.protocol import *
import struct
import random
import logging as logger


class MQTTException(Exception):
    def __init__(self, msg='', exception=None, errno=None, *args, **kwargs):
        super(MQTTException, self).__init__(*args, **kwargs)
        self.exception = exception
        self.errno = errno
        self.msg = msg

    def __unicode__(self):
        return str(self)

    def __str__(self):
        string = ""
        if self.errno:
            string += "[%s] " % self.errno
        if self.msg:
            string += "%s" % self.msg
        if not string and self.exception:
            string = str(self.exception)
        return string


class MQTTProtocolException(MQTTException):
    def get_nack(self):
        if self.errno in [mqtt.CONNACK_REFUSED_PROTOCOL_VERSION,  # mqtt.CONNACK_ACCEPTED,
                          mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED,
                          mqtt.CONNACK_REFUSED_SERVER_UNAVAILABLE,
                          mqtt.CONNACK_REFUSED_BAD_USERNAME_PASSWORD,
                          mqtt.CONNACK_REFUSED_NOT_AUTHORIZED]:
            conn_ack = ConnAck()
            conn_ack.ret_code = self.errno
            return conn_ack


class BaseMQTT(object):
    remaining_length_fixed = None
    auto_pack_identifier = False

    def __init__(self, ctl):
        """
            :type ctl: int
        """
        self.ctl = ctl
        self._pkgID = None
        self._QoS = None
        self._header = None
        self._flags = 0x00
        if ctl in MQTTFlagsTable and MQTTFlagsTable[ctl]:
            self.flags = MQTTFlagsTable[ctl]

    def get_internal_flags(self):
        """
            :return: int
        """
        return self._flags

    def set_internal_flags(self, value):
        """
            :type value: int
        """
        try:
            self._flags = value & int('00001111', 2)
        except:
            self._flags = 0x00

    flags = property(get_internal_flags, set_internal_flags)

    @property
    def header(self):
        """
            :type: int
            :return:
        """
        if self._header is None:
            return self.ctl | self.flags
        return self._header

    def get_pack_identifier(self):
        """
            :return: int
        """
        if self._pkgID is None:
            if self.ctl in [mqtt.SUBSCRIBE, mqtt.UNSUBSCRIBE,
                            mqtt.PUBACK, mqtt.PUBREC,
                            mqtt.PUBREL, mqtt.PUBCOMP,
                            mqtt.SUBACK, mqtt.UNSUBACK,
                            mqtt.PUBLISH]:
                if self.ctl in [mqtt.SUBSCRIBE, mqtt.UNSUBSCRIBE]:
                    self._pkgID = random.randint(1, 0xffff)
                elif not(self.ctl == mqtt.PUBLISH and self.QoS == MQTT_QoS0):
                    if self.auto_pack_identifier:
                        self._pkgID = random.randint(1, 0xffff)
            elif self.auto_pack_identifier:
                self._pkgID = random.randint(1, 0xffff)
        return self._pkgID

    def set_pack_identifier(self, pkg_id):
        """
            :type pkgID: int
        """
        try:
            self._pkgID = int(pkg_id)
        except Exception:
            self._pkgID = None

    pack_identifier = property(get_pack_identifier, set_pack_identifier)

    def get_qos(self):
        """
            :return: int
        """
        if self._QoS is None:
            return (self.flags & int('0110', 2)) >> 1
        return self._QoS

    def set_qos(self, qos):
        """
            :type pkgID: int
        """
        try:
            self._QoS = qos & int('11', 2)
            self.flags = (self.flags & int('1001', 2)) | (self._QoS << 1)
        except Exception:
            self._QoS = None

    QoS = property(get_qos, set_qos)

    @staticmethod
    def get_remaining(msg):
        """
            :type msg: str
        """
        return int2remaining(len(msg))

    def set_flags(self, *args, **kwargs):
        """
            Help function to set easy the flags options
        """
        raise NotImplemented  # pragma: no cover

    def get_variable_header(self):
        """
            :return: basestring
        """
        if self.ctl in [mqtt.PUBACK, mqtt.PUBREC, mqtt.PUBREL, mqtt.PUBCOMP,
                        mqtt.SUBSCRIBE, mqtt.SUBACK, mqtt.UNSUBSCRIBE, mqtt.UNSUBACK]:
            return struct.pack("!H", self.pack_identifier)
        raise NotImplemented  # pragma: no cover

    def get_payload(self):
        """
            :return: basestring
        """
        if self.ctl in [mqtt.CONNACK, mqtt.PUBACK, mqtt.PUBREC,
                        mqtt.PUBREL, mqtt.PUBCOMP, mqtt.UNSUBACK,
                        mqtt.PINGREQ, mqtt.PINGRESP, mqtt.DISCONNECT]:
            return ""
        raise NotImplemented  # pragma: no cover

    def __str__(self):
        return unicode(self).encode('latin-1')

    def __unicode__(self):
        msg = self.get_variable_header()
        msg += self.get_payload()

        ret = struct.pack("!B", self.header)
        ret += self.get_remaining(msg)
        ret += msg
        return unicode(ret, encoding='latin-1')

    def parse_body(self, body):
        """
            Set values from the body. This body contains all data since remain
            :raise: MQTTException
        """
        raise NotImplemented  # pragma: no cover

    def check_integrity(self):
        """
            :raise: MQTTProtocolException
            :return: None
        """
        if self.remaining_length_fixed is not None:
            remain = len(self.get_payload()) + len(self.get_variable_header())
            if remain != self.remaining_length_fixed:
                raise MQTTException('Integrity error')
        if self.ctl in MQTTFlagsTable:
            reserved_flags_fixed = MQTTFlagsTable[self.ctl]
            if reserved_flags_fixed is not None:
                if self.flags != reserved_flags_fixed:
                    raise MQTTException('Reserved flags should be %s' % hex(reserved_flags_fixed))


class MQTTEmpty(BaseMQTT):
    remaining_length_fixed = int('00000000', 2)

    def set_flags(self, *args, **kwargs):
        return

    def get_payload(self):
        return ""

    def get_variable_header(self):
        return ""

    def parse_body(self, body):
        if not body:
            raise MQTTException('Body must be empty')


class MQTTOnlyPackID(MQTTEmpty):
    remaining_length_fixed = int('00000010', 2)

    def get_variable_header(self):
        try:
            return struct.pack("!H", self.pack_identifier)
        except Exception:
            return struct.pack("!H", 0x00)

    def parse_body(self, body):
        (self._pkgID, ) = struct.unpack("!H", body)

    def check_integrity(self):
        if self.pack_identifier is None:
            raise MQTTException('pack identifier required')
        elif self.pack_identifier == 0:
            raise MQTTException('pack identifier could not be 0x00')
        super(MQTTOnlyPackID, self).check_integrity()


class Connect(BaseMQTT):

    def __init__(self, client_id=None, qos=None, keep_alive=0x0f, proto_level=0x04,
                 topic=None, msg=None, auth_name=None, auth_password=None):
        """
            :type clientId: str
            :param clientId: from 1 to 23 chars only 0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ
            :type qos: int
            :param qos: Quality of Service
            :type keep_alive: int
            :param keep_alive: Positive
            :type proto_level: int
            :param proto_level:
            :type topic: str
            :param topic: Optional
            :type msg: str
            :param msg: Optional
            :type auth_name: str
            :param auth_name: Optional
            :type auth_password: str
            :param auth_password: Optional, could be raw bytes
            :return:
        """
        super(Connect, self).__init__(mqtt.CONNECT)
        self.proto_name = "MQTT"
        self.proto_level = proto_level
        self.conn_flags = 0x00
        self.keep_alive = keep_alive
        self.client_id = client_id
        self._topic = None
        self._msg = None
        flags = {}
        flags['qos'] = qos
        flags['name'] = auth_name
        flags['password'] = auth_password
        self.auth_name = None
        self.auth_password = None
        self.set_flags(**flags)
        self.msg = msg
        self.topic = topic

    def get_msg(self):
        return self._msg

    def set_msg(self, msg):
        self._msg = msg
        if msg is None:
            self.set_flags(flag=False)
        else:
            if self.topic is None:
                self.set_flags(flag=False)
            else:
                self.set_flags(flag=True)

    msg = property(get_msg, set_msg)

    def get_topic(self):
        return self._topic

    def set_topic(self, topic):
        self._topic = topic
        if topic is None:
            self.set_flags(retain=False)
        else:
            try:
                self._topic = gen_string(topic, exception=True)
            except Exception:
                self._topic = gen_string(topic)
            if self.msg is None:
                self.set_flags(flag=False)
            else:
                self.set_flags(flag=True)
        self._topic = topic

    topic = property(get_topic, set_topic)

    def has_retain(self):
        return (self.conn_flags & MQTT_CONN_FLAGS_RETAIN) == MQTT_CONN_FLAGS_RETAIN

    def has_flag(self):
        return (self.conn_flags & MQTT_CONN_FLAGS_FLAG) == MQTT_CONN_FLAGS_FLAG

    def has_msg(self):
        return bool(self.has_flag() and self._msg)

    def has_topic(self):
        return bool(self.has_flag() and self._topic)

    def has_name(self):
        return (self.conn_flags & MQTT_CONN_FLAGS_NAME) == MQTT_CONN_FLAGS_NAME

    def has_user(self):
        return self.has_name()

    def has_password(self):
        return (self.conn_flags & MQTT_CONN_FLAGS_PASSWORD) == MQTT_CONN_FLAGS_PASSWORD

    def is_clean(self):
        return (self.conn_flags & MQTT_CONN_FLAGS_CLEAN) == MQTT_CONN_FLAGS_CLEAN

    def set_flags(self, name=None, password=None, retain=None, qos=None, flag=None, clean=None, *args, **kwargs):
        if name:
            self.conn_flags |= MQTT_CONN_FLAGS_NAME
            self.auth_name = unicode(name)
        elif name is not None:
            self.conn_flags &= MQTT_CONN_FLAGS_NAME ^ 0xff
        if password:
            self.conn_flags |= MQTT_CONN_FLAGS_PASSWORD
            self.auth_password = password
        elif password is not None:
            self.conn_flags &= MQTT_CONN_FLAGS_PASSWORD ^ 0xff
        if retain:
            flag = True
            self.conn_flags |= MQTT_CONN_FLAGS_RETAIN
        elif retain is not None:
            self.conn_flags &= MQTT_CONN_FLAGS_RETAIN ^ 0xff
            if self.msg is None or self.topic is None:
                flag = False
        if flag:
            self.conn_flags |= MQTT_CONN_FLAGS_FLAG
        elif flag is not None:
            self.conn_flags &= MQTT_CONN_FLAGS_FLAG ^ 0xff
            self.conn_flags &= MQTT_CONN_FLAGS_RETAIN ^ 0xff
        if clean:
            self.conn_flags |= MQTT_CONN_FLAGS_CLEAN
        elif clean is not None:
            self.conn_flags &= MQTT_CONN_FLAGS_CLEAN ^ 0xff
        if qos is not None:
            self.conn_flags = (self.conn_flags & ((int('11', 2) << 3) ^ 0xff))
            self._QoS = (qos & int('11', 2))
            self.conn_flags |= self._QoS << 3
        if self._QoS is None:
            self._QoS = MQTT_QoS0

        self.conn_flags |= (self._QoS << 3)

    def get_payload(self, ignore_flags=False):
        payload = gen_string(self.client_id)
        if ignore_flags or self.has_flag():
            payload += gen_string(self.topic)
            payload += gen_string(self.msg)
        if ignore_flags or self.has_name():
            payload += gen_string(self.auth_name)
        if ignore_flags or self.has_password():
            str_size = len(self.auth_password)
            fmt = "!H"+("B"*str_size)
            payload += struct.pack(fmt, str_size, *self.auth_password)
        return payload

    def get_variable_header(self):
        msg = gen_string(self.proto_name)
        msg += struct.pack("!B", self.proto_level)
        msg += struct.pack("!B", self.conn_flags)
        msg += struct.pack("!H", self.keep_alive)
        return msg

    def parse_body(self, body):
        (size, ) = struct.unpack_from("!H", body)
        self.proto_name = get_string(body)
        padding = size + 2
        self.proto_level, self.conn_flags, self.keep_alive = struct.unpack_from("!BBH", body, padding)
        padding += 4
        s = body[padding:]
        self.client_id = get_string(body[padding:])
        (size, ) = struct.unpack_from("!H", body, padding)
        padding += 2 + size
        if self.has_flag():
            self._topic = get_string(body[padding:])
            (size, ) = struct.unpack_from("!H", body, padding)
            padding += 2 + size
            (size, ) = struct.unpack_from("!H", body, padding)
            padding += 2
            fmt = "!"+("B"*size)
            self._msg = struct.unpack_from(fmt, body, padding)
            padding += 2 + size
        if self.has_name():
            self.auth_name = get_string(body[padding:])
            (size, ) = struct.unpack_from("!H", body, padding)
            padding += 2 + size
        if self.has_password():
            (size, ) = struct.unpack_from("!H", body, padding)
            padding += 2
            self.auth_password = body[padding: padding+size]
            padding += size

        if len(body) > padding:
            raise MQTTException('Body too big size(%s) expected(%s)' % (len(body), padding))

    def check_integrity(self):
        super(Connect, self).check_integrity()
        if self.proto_name != "MQTT":
            raise MQTTException('Protocol not valid')
        if self.has_retain() and not self.has_flag():
            raise MQTTException("Inconsistency in flags")
        if self.has_flag():
            if not self.topic or self.topic == '\x00\x00':
                raise MQTTException("Topic required according flags")
            elif MQTT_NONE_CHAR in self.topic:
                raise MQTTException("Charter 0x0000 not allowed")
            if self.msg is None:
                raise MQTTException("Message required according flags")
        if self.has_name():
            if not self.auth_name:
                raise MQTTException('UserName required according flags')
            if MQTT_NONE_CHAR in self.auth_name:
                raise MQTTException("Charter 0x0000 not allowed")
        if self.has_password() and not self.auth_password:
            raise MQTTException('Password required according flags')
        if self.QoS not in [MQTT_QoS0, MQTT_QoS1, MQTT_QoS2]:
            raise MQTTException('Protocol QoS not valid')
        if self.proto_level not in [mqtt.MQTTv31, mqtt.MQTTv311]:
            raise MQTTException('Protocol level not valid', errno=mqtt.CONNACK_REFUSED_PROTOCOL_VERSION)
        if not self.is_clean():
            if not self.client_id:
                raise MQTTProtocolException("Client Id must be between 1 and 23",
                                            errno=mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED)
            size_client_id = len(self.client_id)
            if size_client_id > 0:
                if size_client_id > 23 or size_client_id < 1:
                    raise MQTTProtocolException("Client Id must be between 1 and 23",
                                                errno=mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED)
                match = MQTT_CLIENT_ID_RE.match(self.client_id)
                if match is None:
                    raise MQTTProtocolException("Client Id must be charters " + MQTT_CLIENT_ID_RE.pattern,
                                                errno=mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED)


class ConnAck(BaseMQTT):
    remaining_length_fixed = int('00000010', 2)

    def __init__(self, ret_code=mqtt.CONNACK_ACCEPTED):
        super(ConnAck, self).__init__(mqtt.CONNACK)
        self.conn_flags = 0x00
        self.ret_code = ret_code

    def set_flags(self, sp=False, *args, **kwargs):
        self.conn_flags = 0
        if sp:
            self.conn_flags |= MQTT_CONN_FLAGS_SESSION_PRESENT
        else:
            self.conn_flags &= MQTT_CONN_FLAGS_SESSION_PRESENT ^ 0xff

    def has_sp(self):
        return self.conn_flags & MQTT_CONN_FLAGS_SESSION_PRESENT

    def has_session_present(self):
        return self.has_sp()

    def get_variable_header(self):
        msg = struct.pack("!B", self.conn_flags)
        msg += struct.pack("!B", self.ret_code)
        return msg

    def parse_body(self, body):
        self.conn_flags, self.ret_code = struct.unpack("!BB", body)

    def check_integrity(self):
        super(ConnAck, self).check_integrity()
        if self.ret_code not in [mqtt.CONNACK_ACCEPTED, mqtt.CONNACK_REFUSED_SERVER_UNAVAILABLE,
                                 mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED, mqtt.CONNACK_REFUSED_PROTOCOL_VERSION,
                                 mqtt.CONNACK_REFUSED_NOT_AUTHORIZED, mqtt.CONNACK_REFUSED_BAD_USERNAME_PASSWORD]:
            raise MQTTException('ConnAck Code error %s not valid' % self.ret_code)
        if self.has_sp() and self.ret_code != mqtt.CONNACK_ACCEPTED:
            raise MQTTException('Session present only valid with accepted response')
        if self.ret_code:
            raise MQTTProtocolException('ConnAck Error', errno=self.ret_code)


class Publish(BaseMQTT):
    def __init__(self, topic="", msg="", qos=None, dup=False, retain=False, pack_identifier=None):
        super(Publish, self).__init__(mqtt.PUBLISH)
        self.set_flags(qos, dup, retain)
        self.topic = topic
        self.msg = msg
        self.pack_identifier = pack_identifier

    def set_flags(self, qos=None, dup=None, retain=None, *args, **kwargs):
        if dup:
            self.flags |= MQTTFlagsDUP
        elif dup is not None:
            self.flags &= MQTTFlagsDUP ^ 0xff
        if retain:
            self.flags |= MQTTFlagsRETAIN
        elif retain is not None:
            self.flags &= MQTTFlagsRETAIN ^ 0xff
        if qos:
            self.flags = (self.flags & ~(int('11', 2) << 1))
            self._QoS = (qos & int('11', 2))
        if self._QoS is None:
            self._QoS = MQTT_QoS0
        self.flags |= (self._QoS << 1)

    def has_dup(self):
        return self.flags & MQTTFlagsDUP

    def has_retain(self):
        return self.flags & MQTTFlagsRETAIN

    def get_payload(self, ignore_flags=False, exception=False):
        return gen_string(self.msg)

    def get_variable_header(self):
        msg = gen_string(self.topic)
        if self.QoS != MQTT_QoS0:
            try:
                msg += struct.pack("!H", self.pack_identifier)
            except Exception:
                msg += struct.pack("!H", 0x00)
        return msg

    def parse_body(self, body):
        self.topic = get_string(body)
        padding = 0
        (size, ) = struct.unpack_from("!H", body, padding)
        padding += 2 + size
        if self.QoS != MQTT_QoS0:
            (self._pkgID, ) = struct.unpack_from("!H", body[padding:])
            padding += 2
        self.msg = get_string(body[padding:])
        (size, ) = struct.unpack_from("!H", body, padding)
        padding += 2 + size
        if len(body) > padding:
            raise MQTTException('Body too big')

    def check_integrity(self):
        if self.QoS == MQTT_QoS0:
            if self.has_dup():
                raise MQTTException('Publish with QoS 0 should not have DUP')
            if self._pkgID:
                raise MQTTException('Publish with QoS 0 should not have pack identifier')
        elif not self._pkgID:
            raise MQTTException('Publish should have pack identifier')
        if not self.topic:
            raise MQTTException('Topic should not be empty')
        if WILDCARD_SINGLE_LEVEL in self.topic or WILDCARD_MULTI_LEVEL in self.topic:
            raise MQTTException('Not allowed wildcards')
        super(Publish, self).check_integrity()


class PubAck(MQTTOnlyPackID):
    def __init__(self, pack_identifier=None):
        super(PubAck, self).__init__(mqtt.PUBACK)
        self._QoS = MQTT_QoS1
        self.pack_identifier = pack_identifier


class PubRec(MQTTOnlyPackID):
    def __init__(self, pack_identifier=None):
        super(PubRec, self).__init__(mqtt.PUBREC)
        self._QoS = MQTT_QoS2
        self.pack_identifier = pack_identifier


class PubRel(MQTTOnlyPackID):
    reserved_flags_fixed = int('0010', 2)

    def __init__(self, pack_identifier=None):
        super(PubRel, self).__init__(mqtt.PUBREL)
        self._QoS = MQTT_QoS2
        self.pack_identifier = pack_identifier


class PubComp(MQTTOnlyPackID):
    def __init__(self, pack_identifier=None):
        super(PubComp, self).__init__(mqtt.PUBCOMP)
        self._QoS = MQTT_QoS2
        self.pack_identifier = pack_identifier


class Subscribe(BaseMQTT):
    def __init__(self, pack_identifier=None):
        super(Subscribe, self).__init__(mqtt.SUBSCRIBE)
        self.topic_list = {}
        self.topic_order = []
        self.pack_identifier = pack_identifier

    def add_topic(self, topic, qos):
        self.topic_list[topic] = (qos & int('11', 2))
        if topic in self.topic_order:
            self.topic_order.remove(topic)
        self.topic_order.append(topic)

    def get_payload(self):
        msg = ''
        for topic in self.topic_order:
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
            raise MQTTException('Body too big is %s but expered %s' % (padding, len(body)))

    def check_integrity(self):
        if not self._pkgID:
            raise MQTTException('pack identifier required')
        for qos in set(self.topic_list.values()):
            if qos not in [MQTT_QoS0, MQTT_QoS1, MQTT_QoS2]:
                raise MQTTException('QoS reserved flags malformed value %s' % (qos, ))
        super(Subscribe, self).check_integrity()


class SubAck(BaseMQTT):
    reserved_flags_fixed = int('0010', 2)

    def __init__(self, pack_identifier=None):
        super(SubAck, self).__init__(mqtt.SUBACK)
        self.code_list = []
        self.pack_identifier = pack_identifier

    def add_response(self, response_code):
        self.code_list.append(response_code)

    def get_variable_header(self):
        return struct.pack("!H", self.pack_identifier)

    def get_payload(self):
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
            raise MQTTException('Body too big')

    def check_integrity(self):
        if not self._pkgID:
            raise MQTTException('pack identifier required')
        for code in self.code_list:
            if code not in [MQTT_SUBACK_QoS0, MQTT_SUBACK_QoS1, MQTT_SUBACK_QoS2, MQTT_SUBACK_FAILURE]:
                raise MQTTException('Code %s not allowed' % (code, ))
        super(SubAck, self).check_integrity()


class Unsubscribe(BaseMQTT):
    reserved_flags_fixed = int('0010', 2)

    def __init__(self, pack_identifier=None):
        super(Unsubscribe, self).__init__(mqtt.UNSUBSCRIBE)
        self.topic_list = []
        self.pack_identifier = pack_identifier

    def add_topic(self, topic):
        self.topic_list.append(topic)

    def get_variable_header(self):
        return struct.pack("!H", self.pack_identifier)

    def get_payload(self):
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
            raise MQTTException('Body too big')

    def check_integrity(self):
        if not self.topic_list:
            raise MQTTException('Unsubcribe must contains at last one topic')
        super(Unsubscribe, self).check_integrity()


class UnsubAck(MQTTOnlyPackID):
    def __init__(self, pack_identifier=None):
        super(UnsubAck, self).__init__(mqtt.UNSUBACK)
        self.pack_identifier = pack_identifier


class PingReq(MQTTEmpty):
    def __init__(self):
        super(PingReq, self).__init__(mqtt.PINGREQ)


class PingResp(MQTTEmpty):
    def __init__(self):
        super(PingResp, self).__init__(mqtt.PINGRESP)


class Disconnect(MQTTEmpty):
    def __init__(self):
        super(Disconnect, self).__init__(mqtt.DISCONNECT)


MQTTClassTable = {
    mqtt.CONNECT: Connect,
    mqtt.CONNACK: ConnAck,
    mqtt.PUBLISH: Publish,
    mqtt.PUBACK: PubAck,
    mqtt.PUBREC: PubRec,
    mqtt.PUBREL: PubRel,
    mqtt.PUBCOMP: PubComp,
    mqtt.SUBSCRIBE: Subscribe,
    mqtt.SUBACK: SubAck,
    mqtt.UNSUBSCRIBE: Unsubscribe,
    mqtt.UNSUBACK: UnsubAck,
    mqtt.PINGREQ: PingReq,
    mqtt.PINGRESP: PingResp,
    mqtt.DISCONNECT: Disconnect
}


def parse_raw(connection):
    try:
        header = ord(connection.recv(1))
        ctrl = header & 0xf0
        flags = header & 0x0f
        if ctrl not in MQTTClassTable:
            raise MQTTException('%s not control type supported' % ctrl)

        remain = 0
        multiplier = 1
        read = ord(connection.recv(1))
        while read > 0x7f:
            remain += (read & 127) * multiplier
            multiplier *= 128
            read = ord(connection.recv(1))
        remain += (read & 127) * multiplier
        body = connection.recv(remain)

        cls = MQTTClassTable[ctrl]()
        cls.flags = flags
        cls.parse_body(body)
        return cls
    except struct.error as s_ex:
        logger.exception(s_ex)
        raise MQTTException('Invalid format', exception=s_ex)
    except UnicodeDecodeError as u_ex:
        logger.exception(u_ex)
        raise MQTTException('Invalid encode', exception=u_ex)
    except ValueError as v_ex:
        logger.exception(v_ex)
        raise MQTTException('Invalid value', exception=v_ex)
    except TypeError as t_ex:
        logger.exception(t_ex)
        raise MQTTException('Invalid type', exception=t_ex)
