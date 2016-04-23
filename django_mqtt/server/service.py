from django_mqtt.server.packets import *
from django_mqtt.server.models import *
from django_mqtt.models import *

from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import authenticate
from django.db import transaction
from django.conf import settings

from threading import Thread
import logging
import socket


logger = logging.getLogger(__name__)


class MqttServiceThread(Thread):
    def __init__(self, connection, publish_callback=None, *args, **kwargs):
        if not isinstance(connection, socket.socket):
            raise ValueError('socket expected')
        super(MqttServiceThread, self).__init__(*args, **kwargs)
        self._session = None
        self._is_new_session = False
        self._connection = connection
        self._publish_callback = publish_callback
        self._last_publication = None
        self.disconnect = False

    def next_packet(self):
        pkg = parse_raw(self._connection)
        pkg.check_integrity()
        if self._session:
            self._session.ping()
        return pkg

    def notify_publish(self, publish_pk):
        publication = Publication.objects.get(pk=publish_pk)
        self.send_publish(publication.channel.qos, publication.channel.topic, publication.message,
                          pack_identifier=publication.packet_id)

    def send_publish(self, qos, topic, msg, pack_identifier=None):
        if not isinstance(topic, Topic):
            topic, is_new = Topic.objects.get_or_create(name=topic)
        acl = ACL.get_acl(topic, PROTO_MQTT_ACC_SUS)
        if self._session:
            if not self._session.is4me(topic, qos):
                return
            if acl and not acl.has_permission(user=self._session.user):
                return
        elif acl and not acl.has_permission():
            return
        publish_pkg = Publish(topic=topic, msg=msg, qos=qos, pack_identifier=pack_identifier)
        if qos != MQTT_QoS0:
            self._last_publication = publish_pkg
        self._connection.sendall(str(publish_pkg))

    def stop(self):
        self.disconnect = True
        if self._session:
            self._session = None
        if self._connection:
            self._connection.setblocking(0)
            self._connection.shutdown(socket.SHUT_RDWR)
            self._connection.close()
        self._connection = None

    def run(self):
        self.disconnect = False
        try:
            conn_pkg = self.next_packet()
            if not isinstance(conn_pkg, Connect):
                raise MQTTException(_('First packer must be CONNECT'))
            self.process_new_connection(conn_pkg)
            while not self.disconnect:
                pkg = self.next_packet()
                if isinstance(pkg, Connect):
                    self.process_new_connection(pkg)
                elif isinstance(pkg, ConnAck):
                    raise MQTTException(_('Client cannot use ConnAck packer'))
                elif isinstance(pkg, Publish):
                    self.process_new_publish(pkg)
                elif isinstance(pkg, PubAck):
                    if not self._last_publication:
                        raise MQTTException(_('Packer QoS1 not expected'))
                    if self._last_publication.QoS != MQTT_QoS1:
                        raise MQTTException(_('Packer QoS1 not expected'))
                    self._last_publication = None
                elif isinstance(pkg, PubRec):
                    if not self._last_publication:
                        raise MQTTException(_('Packer QoS2 not expected'))
                    if self._last_publication.QoS != MQTT_QoS2:
                        raise MQTTException(_('Packer QoS2 not expected'))
                    resp = PubRel(pack_identifier=pkg.pack_identifier)
                    self._connection.sendall(str(resp))
                elif isinstance(pkg, PubRel):
                    raise MQTTException(_('Packer QoS2 not expected'))
                elif isinstance(pkg, PubComp):
                    if not self._last_publication:
                        raise MQTTException(_('Packer QoS2 not expected'))
                    if self._last_publication.QoS != MQTT_QoS2:
                        raise MQTTException(_('Packer QoS2 not expected'))
                    self._last_publication = None
                elif isinstance(pkg, Subscribe):
                    self.process_subscription(pkg)
                elif isinstance(pkg, SubAck):
                    raise MQTTException(_('Client cannot use SubAck packer'))
                elif isinstance(pkg, Unsubscribe):
                    self.process_unsubscription(pkg)
                elif isinstance(pkg, UnsubAck):
                    raise MQTTException(_('Client cannot use UnsubAck packer'))
                elif isinstance(pkg, PingReq):
                    resp = PingResp()
                    self._connection.sendall(str(resp))
                elif isinstance(pkg, PingResp):
                    raise MQTTException(_('Client cannot use PingResp packer'))
                elif isinstance(pkg, Disconnect):
                    self._session.disconnect()
                    self.disconnect = True
            # TODO manager timeoout or disconecctions
        except MQTTProtocolException as ex:
            logger.exception(ex)
            logging.warning("%s" % ex)
            self.disconnect = True
        except MQTTException as ex:
            logger.exception(ex)
            logging.warning("%s" % ex)
            self.disconnect = True
        finally:
            self.stop()

    def process_unsubscription(self, unsubscription_pkg):
        logger.info('%(client_id)s unsubscription %(topics)s' % {
            'client_id': self._session.client_id,
            'topics': unsubscription_pkg.topic_list
        })
        resp = UnsubAck(pack_identifier=unsubscription_pkg.pack_identifier)
        for topic in unsubscription_pkg.topic_list:
            self._session.unsubscribe(topic)
        self._connection.sendall(str(resp))

    def process_subscription(self, subscription_pkg):
        resp = SubAck(pack_identifier=subscription_pkg.pack_identifier)
        for topic in subscription_pkg.topic_list:
            qos = subscription_pkg.topic_list[topic]
            subs = None
            code = MQTT_SUBACK_FAILURE
            try:
                topic, new_topic = Topic.objects.get_or_create(name=topic)
                acl = ACL.get_acl(topic, PROTO_MQTT_ACC_SUS)
                if self._session and acl and acl.has_permission(user=self._session.user):
                    if qos is MQTT_QoS0:
                        subs, new_subs = Channel.objects.get_or_create(topic=topic, qos=qos)
                        code=MQTT_SUBACK_QoS0
                    elif qos is MQTT_QoS1:
                        subs, new_subs = Channel.objects.get_or_create(topic=topic, qos=qos)
                        code=MQTT_SUBACK_QoS1
                    elif qos is MQTT_QoS2:
                        subs, new_subs = Channel.objects.get_or_create(topic=topic, qos=qos)
                        code=MQTT_SUBACK_QoS2
            except ValidationError as ex:
                logger.exception(ex)
            if subs:
                self._session.subscribe(channel=subs)
            resp.add_response(code)
        self._connection.sendall(str(resp))

    @transaction.atomic
    def process_new_publish_qos2(self, publish_pkg, channel):
        try:
            publication = Publication.objects.get_or_create(channel=channel, remain=publish_pkg.has_retain())
            publication.packet_id = publish_pkg.pack_identifier
            publication.message = publish_pkg.msg
            publication.save()
            resp = PubRec(pack_identifier=publish_pkg.pack_identifier)
            self._connection.sendall(str(resp))

            pkg = self.next_packet()
            if not isinstance(pkg, PubRel):
                raise MQTTException(_('Publish QoS2 protocol failure'))
            if pkg.pack_identifier != publish_pkg.pack_identifier:
                raise MQTTException(_('Publish QoS2 protocol failure %(initial_pack_identifier)s!=%(pack_identifier)s')
                                    % {'pack_identifier': publish_pkg.pack_identifier,
                                       'initial_pack_identifier': pkg.pack_identifier})

            transaction.commit()
            resp = PubComp(pack_identifier=pkg.pack_identifier)
            self._connection.sendall(str(resp))
            if self._publish_callback:
                self._publish_callback(publication.pk)
        except MQTTException as ex:
            logger.warning(_('Rollback publication from user:%(user)s to: %(channel)s') %
                           {'channel': channel, 'user': self._session.user})
            transaction.rollback()
            raise ex

    def process_new_publish(self, publish_pkg):
        topic, is_new = Topic.objects.get_or_create(name=publish_pkg.topic)
        acl = ACL.get_acl(topic, PROTO_MQTT_ACC_PUB)
        if acl and not acl.has_permission(user=self._session.user):
            raise MQTTException(_('Permission error to publish'), errno=mqtt.CONNACK_REFUSED_NOT_AUTHORIZED)
        channel, new_channel = Channel.objects.get_or_create(topic=topic, qos=publish_pkg.QoS)
        publication = Publication.objects.get_or_create(channel=channel, remain=publish_pkg.has_retain())
        logger.info(_('New publish user:%(user)s to: %(channel)s') %
                    {'channel': channel, 'user': self._session.user})
        if publish_pkg.QoS == MQTT_QoS0:
            publication.message = publish_pkg.msg
            publication.save()
            if self._publish_callback:
                self._publish_callback(publication.pk)
        elif publish_pkg.QoS == MQTT_QoS1:
            publication.message = publish_pkg.msg
            publication.save()
            if self._publish_callback:
                self._publish_callback(publication.pk)
            resp = PubAck(pack_identifier=publish_pkg.pack_identifier)
            self._connection.sendall(str(resp))
        elif publish_pkg.QoS == MQTT_QoS2:
            self.process_new_publish_qos2(publish_pkg, channel)

    def process_new_connection(self, conn_pkg):
        conn_ack = None
        try:
            self._session = None
            self._is_new_session = False
            if not isinstance(conn_pkg, Connect):
                raise MQTTException(_('First pkg must be CONNECT package'))

            if conn_pkg.proto_level != 0x04:  # Only allow 3.1.1
                raise MQTTProtocolException(errno=mqtt.CONNACK_REFUSED_PROTOCOL_VERSION)

            topic = None
            acl = None
            if conn_pkg.has_topic():
                if WILDCARD_SINGLE_LEVEL in conn_pkg.topic or WILDCARD_MULTI_LEVEL in conn_pkg.topic:
                    raise MQTTException(_('Topic with wildcadrs'))
                topic, new_topic = Topic.objects.get_or_create(name=conn_pkg.topic)
                acl = ACL.get_acl(topic, PROTO_MQTT_ACC_PUB)
                if acl.topic != topic:
                    logger.info(_('No ACL for %(topic)s, found %(acl)s') % {'topic': topic, 'acl': acl})

            if not conn_pkg.client_id:
                if not conn_pkg.is_clean():
                    raise MQTTProtocolException(_('Empty client not allowed with this flags'),
                                                errno=mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED)
                allow_empty = False
                if hasattr(settings, 'MQTT_ALLOW_EMPTY_CLIENT_ID'):
                    allow_empty = settings.MQTT_ALLOW_EMPTY_CLIENT_ID
                if not allow_empty:
                    raise MQTTProtocolException(_('Empty client not allowed'),
                                                errno=mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED)

            name = None
            if conn_pkg.has_name():
                name = conn_pkg.auth_name
            pwd = None
            if conn_pkg.has_password():
                pwd = conn_pkg.auth_password

            user = None
            if name is not None and pwd is not None:
                user = authenticate(username=name, password=pwd)
                if not user or not user.is_active:
                    raise MQTTProtocolException(_('Not user or inactive'),
                                                errno=mqtt.CONNACK_REFUSED_BAD_USERNAME_PASSWORD)
            elif name is not None:
                try:
                    user = User.objects.get(username=name, is_active=True)
                    # TODO check setting if allow only username auth
                    if acl and not acl.only_username:
                        raise MQTTProtocolException(_('ACL not allow only username auth'),
                                                    errno=mqtt.CONNACK_REFUSED_BAD_USERNAME_PASSWORD)
                except User.DoesNotExist:
                    raise MQTTProtocolException(_('Name not found'), errno=mqtt.CONNACK_REFUSED_BAD_USERNAME_PASSWORD)
                except User.MultipleObjectsReturned:
                    raise MQTTProtocolException(_('Too many name founds'),
                                                errno=mqtt.CONNACK_REFUSED_BAD_USERNAME_PASSWORD)
            elif pwd is not None:
                if acl and not acl.has_permission(password=pwd):
                    raise MQTTProtocolException(_('Password no valid'),
                                                errno=mqtt.CONNACK_REFUSED_BAD_USERNAME_PASSWORD)

            if hasattr(settings, 'MQTT_AUTH_REQUITED') and settings.MQTT_AUTH_REQUITED:
                if user is None:
                    raise MQTTProtocolException(errno=mqtt.CONNACK_REFUSED_NOT_AUTHORIZED)

            # TODO Allow auto create if client id??
            cli_id, is_new_id = ClientId.objects.get_or_create(name=conn_pkg.client_id)
            if not cli_id.has_permission(user):
                raise MQTTProtocolException(_('User nor allowed to use this client id'),
                                            errno=mqtt.CONNACK_REFUSED_NOT_AUTHORIZED)
            if acl:
                if not acl.has_permission(user=user):
                    raise MQTTProtocolException(_('User not allowed'),
                                                errno=mqtt.CONNACK_REFUSED_BAD_USERNAME_PASSWORD)
            else:
                acc = PROTO_MQTT_ACC_PUB if conn_pkg.has_retain() else PROTO_MQTT_ACC_SUS
                if not ACL.get_default(acc, user=user, password=pwd):
                    raise MQTTProtocolException(_('Rejected by default'), errno=mqtt.CONNACK_REFUSED_NOT_AUTHORIZED)

            self._is_new_session = True
            if self._session is not None:
                self._session.active = False
                self._session.save()

            self._session, is_new_session = Session.objects.get_or_create(client_id=cli_id)

            self._session.user = user
            if not is_new_session and self._session.is_alive():
                self._is_new_session = False

            if not self._is_new_session:
                if self._session.user:
                    if user != self._session.user:
                        logger.warning(_('Old user for client id %(client_id)s was '
                                         '%(user)s and now will be %(new_user)s') %
                                       {'client_id': cli_id, 'user': self._session.user, 'new_user': user})
            self._session.save()

            if conn_pkg.has_flag():
                publish_pkg = Publish(topic=topic.name, msg=conn_pkg.msg, qos=MQTT_QoS0, retain=conn_pkg.has_retain())
                self.process_new_publish(publish_pkg)

            conn_ack = ConnAck()
            if conn_pkg.is_clean() or not self._is_new_session:
                conn_ack.set_flags(sp=False)
            else:
                conn_ack.set_flags(sp=True)
            conn_ack.ret_code = mqtt.CONNACK_ACCEPTED
            self._connection.settimeout(conn_pkg.keep_alive)
            logger.info(_('New connection accepted id:%(client_id)s user:%(user)s "keep alive":%(keep_alive)s') %
                        {'client_id': cli_id, 'user': user, 'keep_alive': conn_pkg.keep_alive})
        except MQTTProtocolException as ex:
            conn_ack = ex.get_nack()
            raise MQTTException(exception=ex)
        finally:
            if conn_ack:
                self._connection.sendall(str(conn_ack))
