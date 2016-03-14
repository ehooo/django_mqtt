from django_mqtt.protocol import *
import logging
import struct
import os


class MQTTException(Exception):
    def __init__(self, msg='', exception=None, disconnect=True, errno=None, *args, **kwargs):
        super(MQTTException, self).__init__(*args, **kwargs)
        self.disconnect = disconnect
        self.exception = exception
        self.errno = errno
        self.msg = msg

    def __unicode__(self):
        return str(self)

    def __str__(self):
        string = ""
        if self.errno:
            string += "[%s]" % self.errno
        if self.msg:
            string += " %s" % self.msg
        if not string and self.exception:
            string = str(self.exception)
        return string


class MQTTProtocolException(MQTTException):
    def get_nack(self):
        if self.errno in [mqtt.CONNACK_REFUSED_NOT_AUTHORIZED,
                          mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED,
                          mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED,
                          mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED,
                          mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED,
                          mqtt.CONNACK_REFUSED_PROTOCOL_VERSION]:
            conn_ack = ConnAck()
            conn_ack.ret_code = self.errno
            return conn_ack


class BaseMQTT(object):
    remaining_length_fixed = None

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
            return (self.ctl << 4) | self.flags
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
                self._pkgID = os.urandom(16)
                if self.ctl == mqtt.PUBLISH and self.QoS == 0:
                    self._pkgID = None  # TODO check possible error
                elif self.ctl not in [mqtt.SUBSCRIBE, mqtt.UNSUBSCRIBE]:
                    self._pkgID = None  # TODO check possible error
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
        self._QoS = qos

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
        raise NotImplemented

    def get_variable_header(self):
        """
            :return: basestring
        """
        if self.ctl in [mqtt.PUBACK, mqtt.PUBREC, mqtt.PUBREL, mqtt.PUBCOMP,
                        mqtt.SUBSCRIBE, mqtt.SUBACK, mqtt.UNSUBSCRIBE, mqtt.UNSUBACK]:
            return struct.pack("!H", self.pack_identifier)
        raise NotImplemented

    def get_payload(self):
        """
            :return: basestring
        """
        if self.ctl in [mqtt.CONNACK, mqtt.PUBACK, mqtt.PUBREC,
                        mqtt.PUBREL, mqtt.PUBCOMP, mqtt.UNSUBACK,
                        mqtt.PINGREQ, mqtt.PINGRESP, mqtt.DISCONNECT]:
            return ""
        raise NotImplemented

    def __unicode__(self):
        msg = self.get_variable_header()
        msg += self.get_payload()

        ret = struct.pack("!B", self.header)
        ret += self.get_remaining(msg)
        ret += msg
        return ret

    def parse_body(self, body):
        """
            Set values from the body. This body contains all data since remain
            :raise: MQTTException
        """
        raise NotImplemented

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
        pass

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
        return struct.pack("!H", self.pack_identifier)

    def parse_body(self, body):
        (self._pkgID, ) = struct.unpack("!H", body)


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
        self.proto_name = gen_string("MQTT")
        self.proto_level = proto_level
        self.conn_flags = 0x00
        self.keep_alive = keep_alive
        self.client_id = client_id
        self._topic = topic
        self._msg = msg
        flags = {}
        if self._msg is not None or self._topic is not None:
            flags['retain'] = True
        flags['qos'] = qos
        flags['name'] = auth_name
        flags['password'] = auth_password
        self.auth_name = None
        self.auth_password = None
        self.set_flags(**flags)

    def get_msg(self):
        return self._msg

    def set_msg(self, msg):
        self._msg = msg
        if msg is None:
            self.set_flags(retain=False)
        else:
            if self.topic is None:
                self.set_flags(retain=False)
            else:
                self.set_flags(retain=True)

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
            except Exception as ex:
                logging.warn('topic contains not valid format %s' % (ex, ))
                self._topic = gen_string(topic)
            if self.msg is None:
                self.set_flags(retain=False)
            else:
                self.set_flags(retain=True)
        self._topic = topic

    topic = property(get_topic, set_topic)

    def has_retain(self):
        return self.conn_flags & MQTT_CONN_FLAGS_RETAIN

    def has_msg(self):
        return self.has_retain() and self._msg

    def has_topic(self):
        return self.has_retain() and self._topic

    def has_name(self):
        return self.conn_flags & MQTT_CONN_FLAGS_NAME

    def has_user(self):
        return self.has_name()

    def has_password(self):
        return self.conn_flags & MQTT_CONN_FLAGS_PASSWORD

    def is_clean(self):
        return self.conn_flags & MQTT_CONN_FLAGS_CLEAN

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
            self.conn_flags |= MQTT_CONN_FLAGS_RETAIN
        elif retain is not None:
            self.conn_flags &= MQTT_CONN_FLAGS_RETAIN ^ 0xff
        if flag:
            self.conn_flags |= MQTT_CONN_FLAGS_FLAG
        elif flag is not None:
            self.conn_flags &= MQTT_CONN_FLAGS_FLAG ^ 0xff
        if clean:
            self.conn_flags |= MQTT_CONN_FLAGS_CLEAN
        elif clean is not None:
            self.conn_flags &= MQTT_CONN_FLAGS_CLEAN ^ 0xff
        if qos:
            self.conn_flags = (self.conn_flags & ((int('11', 2) << 3) ^ 0xff))
            self._QoS = (qos & int('11', 2))
        if self._QoS is None:
            self._QoS = MQTT_QoS0

        self.conn_flags |= (self._QoS << 3)

    def get_payload(self, ignore_flags=False):
        payload = gen_string(self.client_id)
        if ignore_flags or self.has_retain():
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
        msg = self.proto_name
        msg += struct.pack("!B", self.proto_level)
        msg += struct.pack("!B", self.conn_flags)
        msg += struct.pack("!H", self.keep_alive)
        return msg

    def parse_body(self, body):
        self.proto_level, self.conn_flags, self.keep_alive = struct.unpack_from("!BBH", body, 0)
        padding = 4
        if not self.is_clean():
            self.client_id = get_string(body[padding:])
            (size, ) = struct.unpack_from("!H", body, padding)
            padding += 2 + size
        if self.has_retain():
            self._topic = get_string(body[padding:])
            (size, ) = struct.unpack_from("!H", body, padding)
            padding += 2 + size
            self._msg = get_string(body[padding:])
            (size, ) = struct.unpack_from("!H", body, padding)
            padding += 2 + size
        if self.has_name():
            self.auth_name = get_string(body[padding:])
            (size, ) = struct.unpack_from("!H", body, padding)
            padding += 2 + size
        if self.has_password():
            self.auth_password = body[padding:]
            (size, ) = struct.unpack_from("!H", body, padding)
            padding += 2 + size
        if len(body) > padding:
            raise MQTTException('Body too big')

    def check_integrity(self):
        super(Connect, self).check_integrity()
        if self.proto_name != gen_string("MQTT"):
            raise MQTTException('Protocol not valid')
        if not self.is_clean():
            if self.client_id is None:
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
        if self.has_retain():
            if self.topic is None:
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
        if self.proto_level not in [mqtt.MQTTv31, mqtt.MQTTv311]:
            raise MQTTException('Protocol level not valid')
        if self.QoS == 0x03:
            raise MQTTException('Protocol QoS not valid')


class ConnAck(BaseMQTT):
    remaining_length_fixed = int('00000010', 2)

    def __init__(self):
        super(ConnAck, self).__init__(mqtt.CONNACK)
        self.conn_flags = 0x00
        self.ret_code = mqtt.CONNACK_ACCEPTED

    def set_flags(self, sp=False, *args, **kwargs):
        self.conn_flags = 0
        if sp:
            self.conn_flags |= MQTT_CONN_FLAGS_SESSION_PRESENT
        else:
            self.conn_flags ^= MQTT_CONN_FLAGS_SESSION_PRESENT

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
        if self.ret_code:
            raise MQTTProtocolException('ConnAck Error', errno=self.ret_code)


class Publish(BaseMQTT):
    def __init__(self, topic="", msg="", qos=None, dup=False, retain=False):
        super(Publish, self).__init__(mqtt.PUBLISH)
        self.set_flags(qos, dup, retain)
        self.topic = topic
        self.msg = msg

    def set_flags(self, qos=None, dup=None, retain=None, *args, **kwargs):
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

    def get_payload(self, ignore_flags=False, exception=False):
        return gen_string(self.msg)

    def get_variable_header(self):
        msg = gen_string(self.topic)
        if self.QoS != MQTT_QoS0:
            msg += struct.pack("!H", self.pack_identifier)
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
        if self.QoS == MQTT_QoS0 and self.pack_identifier:
            raise MQTTException('Publish with QoS 0 should not have pack identifier')
        elif not self.pack_identifier:
            raise MQTTException('Publish should have pack identifier')
        super(Publish, self).check_integrity()


class PubAck(MQTTOnlyPackID):
    def __init__(self):
        super(PubAck, self).__init__(mqtt.PUBACK)
        self._QoS = MQTT_QoS1


class PubRec(MQTTOnlyPackID):
    def __init__(self):
        super(PubRec, self).__init__(mqtt.PUBREC)
        self._QoS = MQTT_QoS2


class PubRel(MQTTOnlyPackID):
    reserved_flags_fixed = int('0010', 2)

    def __init__(self):
        super(PubRel, self).__init__(mqtt.PUBREL)
        self._QoS = MQTT_QoS2

    def check_integrity(self):
        super(PubRel, self).check_integrity()


class PubComp(MQTTOnlyPackID):
    def __init__(self):
        super(PubComp, self).__init__(mqtt.PUBCOMP)
        self._QoS = MQTT_QoS2


class Subscribe(BaseMQTT):
    def __init__(self):
        super(Subscribe, self).__init__(mqtt.SUBSCRIBE)
        self.topic_list = {}

    def add_topic(self, topic, qos):
        self.topic_list[topic] = (qos & int('11', 2))

    def get_variable_header(self):
        return struct.pack("!H", self.pack_identifier)

    def get_payload(self):
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
            raise MQTTException('Body too big is %s but expered %s' % (padding, len(body)))

    def check_integrity(self):
        for qos in set(self.topic_list.values()):
            if (qos & int('11111100', 2)) == 0:
                raise MQTTException('QoS reserved flags malformed value %s' % (qos, ))
        super(Subscribe, self).check_integrity()


class SubAck(BaseMQTT):
    reserved_flags_fixed = int('0010', 2)

    def __init__(self):
        super(SubAck, self).__init__(mqtt.SUBACK)
        self.code_list = []

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


class Unsubscribe(BaseMQTT):
    reserved_flags_fixed = int('0010', 2)

    def __init__(self):
        super(Unsubscribe, self).__init__(mqtt.UNSUBSCRIBE)
        self.topic_list = []

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


class UnsubAck(MQTTOnlyPackID):
    def __init__(self):
        super(UnsubAck, self).__init__(mqtt.UNSUBACK)


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
        header = connection.recv(1)
        ctrl = (header & 0xf0) >> 4
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
            raise MQTTException('%s not control type supported' % ctrl)
        cls = MQTTClassTable[ctrl]()
        cls.flags = flags
        cls.parse_body(body)
        return cls
    except struct.error as s_ex:
        raise MQTTException(exception=s_ex)
    except UnicodeDecodeError as u_ex:
        raise MQTTException(exception=u_ex)
    except ValueError as v_ex:
        raise MQTTException(exception=v_ex)
    except TypeError as t_ex:
        raise MQTTException(exception=t_ex)
