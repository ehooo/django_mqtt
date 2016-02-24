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


class MQTTProcolException(MQTTException):

    def get_nack(self, sp=False):
        if self.errno in [mqtt.CONNACK_REFUSED_NOT_AUTHORIZED,
                          mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED,
                          mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED,
                          mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED,
                          mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED,
                          mqtt.CONNACK_REFUSED_PROTOCOL_VERSION]:
            conn_ack = MQTTConnAck()
            conn_ack.ret_code = self.errno
            conn_ack.set_flags(sp)
            return conn_ack


class BaseMQTT(object):
    remaining_length_fixed = None
    reserved_flags_fixed = None

    def __init__(self, ctl):
        self.ctl = ctl
        self._pkgID = None
        self._QoS = None
        self._header = None
        self._flags = 0x00
        if ctl in MQTTFlagsTable and MQTTFlagsTable[ctl]:
            self.flags = MQTTFlagsTable[ctl]

    @property
    def flags(self):
        return self._flags

    @flags.setter
    def set_internal_flags(self, value):
        try:
            self._flags = value & int('00001111')
        except:
            self._flags = 0x00

    @property
    def header(self):
        if self._header is None:
            return (self.ctl << 4) | self.flags
        return self._header

    @property
    def pack_identifier(self):
        if self._pkgID is None:
            if self.ctl in [mqtt.SUBSCRIBE, mqtt.UNSUBSCRIBE,
                            mqtt.PUBACK, mqtt.PUBREC,
                            mqtt.PUBREL, mqtt.PUBCOMP,
                            mqtt.SUBACK, mqtt.UNSUBACK,
                            mqtt.PUBLISH]:
                self._pkgID = os.urandom(16)
                if self.ctl == mqtt.PUBLISH and self.QoS == 0:
                    self._pkgID = None
                elif self.ctl not in [mqtt.SUBSCRIBE, mqtt.UNSUBSCRIBE]:
                    self._pkgID = None
        return self._pkgID

    @pack_identifier.setter
    def set_pack_identifier(self, pkgID):
        try:
            self._pkgID = int(pkgID)
        except:
            self._pkgID = None

    @property
    def QoS(self):
        if self._QoS is None:
            return (self.flags & int('0110', 2)) >> 1
        return self._QoS

    @QoS.setter
    def set_QoS(self, qos):
        self._QoS = qos

    def get_remaining(self, msg):
        return int2remaining(len(msg))

    def set_flags(self, *args, **kwargs):
        raise NotImplemented

    def get_variable_header(self):
        if self.ctl in [mqtt.PUBACK, mqtt.PUBREC, mqtt.PUBREL, mqtt.PUBCOMP,
                        mqtt.SUBSCRIBE, mqtt.SUBACK, mqtt.UNSUBSCRIBE, mqtt.UNSUBACK]:
            return struct.pack("!H", self.pack_identifier)
        raise NotImplemented

    def get_payload(self):
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
        raise NotImplemented

    def check_integrity(self):
        if self.remaining_length_fixed is not None:
            remain = len(self.get_payload()) + len(self.get_variable_header())
            if remain != self.remaining_length_fixed:
                raise MQTTProcolException('Integrity error')
        if self.reserved_flags_fixed is not None:
            if self.flags != self.reserved_flags_fixed:
                raise MQTTProcolException('Reserved flags should be 0')


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
            raise MQTTProcolException('Body must be empty')


class MQTTOnlyPackID(MQTTEmpty):
    remaining_length_fixed = int('00000010', 2)

    def get_variable_header(self):
        return struct.pack("!H", self.pack_identifier)

    def parse_body(self, body):
        (self._pkgID, ) = struct.unpack("!H", body)


class MQTTConnect(BaseMQTT):
    def __init__(self, clientId=None, qos=None, keep_alive=0x0f, proto_level=0x04,
                 topic="", msg="", auth_name=None, auth_password=None):
        super(MQTTConnect, self).__init__(mqtt.CONNECT)
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
        try:
            gen_string(msg, exception=True)
        except:
            msg = ""
        if msg or self.topic:
            self.set_flags(retain=True)
        else:
            self.set_flags(retain=False)
        self._msg = msg

    @property
    def topic(self):
        return self._topic

    @msg.setter
    def set_topic(self, topic):
        try:
            gen_string(topic, exception=True)
        except:
            topic = ""
        if topic or self.msg:
            self.set_flags(retain=True)
        else:
            self.set_flags(retain=False)
        self._topic = topic

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

    def get_payload(self, ignore_flags=False):
        payload = gen_string(self.clientId)
        if ignore_flags or self.has_retain():
            payload += gen_string(self.topic)
            payload += gen_string(self.msg)
        if ignore_flags or self.has_name():
            payload += gen_string(self.auth_name)
        if ignore_flags or self.has_password():
            payload += gen_string(self.auth_password)
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
            self.clientId = get_string(body[padding:])
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
            self.auth_password = get_string(body[padding:])  # FIXME allow binary passwords
            (size, ) = struct.unpack_from("!H", body, padding)
            padding += 2 + size
        if len(body) > padding:
            raise MQTTProcolException('Body too big')

    def check_integrity(self):
        super(MQTTConnect, self).check_integrity()
        if not self.is_clean():
            if not self.clientId:
                raise MQTTProcolException("ClientIds must be between 1 and 23",
                                          errno=mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED)
            size_clientId = len(self.clientId)
            if size_clientId > 23 or size_clientId < 1:
                raise MQTTProcolException("ClientIds must be between 1 and 23",
                                          errno=mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED)
        if self.has_name() and not self.auth_name:
            raise MQTTException('UserName required according flags')
        if self.has_password() and not self.auth_password:
            raise MQTTException('Password required according flags')


class MQTTConnAck(BaseMQTT):
    remaining_length_fixed = int('00000010', 2)

    def __init__(self):
        super(MQTTConnAck, self).__init__(mqtt.CONNACK)
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
        super(MQTTConnAck, self).check_integrity()
        if self.ret_code not in [mqtt.CONNACK_ACCEPTED, mqtt.CONNACK_REFUSED_SERVER_UNAVAILABLE,
                                 mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED, mqtt.CONNACK_REFUSED_PROTOCOL_VERSION,
                                 mqtt.CONNACK_REFUSED_NOT_AUTHORIZED, mqtt.CONNACK_REFUSED_BAD_USERNAME_PASSWORD]:
            raise MQTTProcolException('ConnAck Code error %s not valid' % self.ret_code)
        if self.ret_code:
            raise MQTTProcolException('ConnAck Error', errno=self.ret_code)


class MQTTPublish(BaseMQTT):
    def __init__(self, topic="", msg="", qos=None, dup=False, retain=False):
        super(MQTTPublish, self).__init__(mqtt.PUBLISH)
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
            raise MQTTProcolException('Body too big')

    def check_integrity(self):
        if self.QoS == MQTT_QoS0 and self.pack_identifier:
            raise MQTTProcolException('Publish with QoS 0 should not have pack identifier')
        elif not self.pack_identifier:
            raise MQTTProcolException('Publish should have pack identifier')
        super(MQTTPublish, self).check_integrity()


class MQTTPubAck(MQTTOnlyPackID):
    def __init__(self):
        super(MQTTPubAck, self).__init__(mqtt.PUBACK)
        self._QoS = MQTT_QoS1


class MQTTPubRec(MQTTOnlyPackID):
    def __init__(self):
        super(MQTTPubRec, self).__init__(mqtt.PUBREC)
        self._QoS = MQTT_QoS2


class MQTTPubRel(MQTTOnlyPackID):
    reserved_flags_fixed = int('0010', 2)

    def __init__(self):
        super(MQTTPubRel, self).__init__(mqtt.PUBREL)
        self._QoS = MQTT_QoS2

    def check_integrity(self):
        super(MQTTPubRel, self).check_integrity()



class MQTTPubComp(MQTTOnlyPackID):
    def __init__(self):
        super(MQTTPubComp, self).__init__(mqtt.PUBCOMP)
        self._QoS = MQTT_QoS2


class MQTTSubcribe(BaseMQTT):
    def __init__(self):
        super(MQTTSubcribe, self).__init__(mqtt.SUBSCRIBE)
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
            raise MQTTProcolException('Body too big')


class MQTTSubAck(BaseMQTT):
    reserved_flags_fixed = int('0010', 2)

    def __init__(self):
        super(MQTTSubAck, self).__init__(mqtt.SUBACK)
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
            raise MQTTProcolException('Body too big')


class MQTTUnsubcribe(BaseMQTT):
    reserved_flags_fixed = int('0010', 2)

    def __init__(self):
        super(MQTTUnsubcribe, self).__init__(mqtt.UNSUBSCRIBE)
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
            raise MQTTProcolException('Body too big')


class MQTTUnsubAck(MQTTOnlyPackID):
    def __init__(self):
        super(MQTTUnsubAck, self).__init__(mqtt.UNSUBACK)


class MQTTPingReq(MQTTEmpty):
    def __init__(self):
        super(MQTTPingReq, self).__init__(mqtt.PINGREQ)


class MQTTPingResp(MQTTEmpty):
    def __init__(self):
        super(MQTTPingResp, self).__init__(mqtt.PINGRESP)


class MQTTDisconect(MQTTEmpty):
    reserved_flags_fixed = int('0000', 2)

    def __init__(self):
        super(MQTTDisconect, self).__init__(mqtt.DISCONNECT)


MQTTClassTable = {
    mqtt.CONNECT: MQTTConnect,
    mqtt.CONNACK: MQTTConnAck,
    mqtt.PUBLISH: MQTTPublish,
    mqtt.PUBACK: MQTTPubAck,
    mqtt.PUBREC: MQTTPubRec,
    mqtt.PUBREL: MQTTPubRel,
    mqtt.PUBCOMP: MQTTPubComp,
    mqtt.SUBSCRIBE: MQTTSubcribe,
    mqtt.SUBACK: MQTTSubAck,
    mqtt.UNSUBSCRIBE: MQTTUnsubcribe,
    mqtt.UNSUBACK: MQTTUnsubAck,
    mqtt.PINGREQ: MQTTPingReq,
    mqtt.PINGRESP: MQTTPingResp,
    mqtt.DISCONNECT: MQTTDisconect
}


def parse_raw(connection):
    cls = None
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
            raise MQTTProcolException('%s not control type supported' % ctrl)
        cls = MQTTClassTable[ctrl]()
        cls.flags = flags
        cls.parse_body(body)
    except struct.error as s_ex:
        logging.exception(s_ex)
        raise MQTTProcolException(exception=s_ex)
    except UnicodeDecodeError as u_ex:
        logging.exception(u_ex)
        raise MQTTProcolException(exception=u_ex)
    except ValueError as v_ex:
        logging.exception(v_ex)
        raise MQTTProcolException(exception=v_ex)
    return cls
