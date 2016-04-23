import ssl
import socket

from django.utils.translation import ugettext_lazy as _
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.db import models
import paho.mqtt.client as mqtt

from django_mqtt.publisher.signals import *
from django_mqtt.protocol import *
from django_mqtt.models import Topic, ClientId


PROTO_MQTT_CONN_OK = mqtt.CONNACK_ACCEPTED
PROTO_MQTT_CONN_ERROR_PROTO_VERSION = mqtt.CONNACK_REFUSED_PROTOCOL_VERSION
PROTO_MQTT_CONN_ERROR_INVALID_CLIENT = mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED
PROTO_MQTT_CONN_ERROR_UNAVAILABLE = mqtt.CONNACK_REFUSED_SERVER_UNAVAILABLE
PROTO_MQTT_CONN_ERROR_BAD_USER = mqtt.CONNACK_REFUSED_BAD_USERNAME_PASSWORD
PROTO_MQTT_CONN_ERROR_NOT_AUTH = mqtt.CONNACK_REFUSED_NOT_AUTHORIZED
PROTO_MQTT_CONN_ERROR_UNKNOWN = 6
PROTO_MQTT_CONN_ERROR_GENERIC = 100
PROTO_MQTT_CONN_ERROR_ADDR_FAILED = 191
PROTO_MQTT_CONN_ERROR_INTERRUPTED = 200
PROTO_MQTT_CONN_ERROR_PERMISSION_DENIED = 201
PROTO_MQTT_CONN_ERROR_FAULT_NETWORK = 202
PROTO_MQTT_CONN_ERROR_INVALID = 203
PROTO_MQTT_CONN_ERROR_BLOCK = 204
PROTO_MQTT_CONN_ERROR_BLOCKING = 205
PROTO_MQTT_CONN_ERROR_IN_USE = 206
PROTO_MQTT_CONN_ERROR_RESET = 207
PROTO_MQTT_CONN_ERROR_SHUTDOWN = 208
PROTO_MQTT_CONN_ERROR_TIMEOUT = 209
PROTO_MQTT_CONN_ERROR_REFUSED = 210
PROTO_MQTT_CONN_ERROR_TOO_LONG = 211
PROTO_MQTT_CONN_ERROR_DOWN = 212
PROTO_MQTT_CONN_ERROR_UNREACHABLE = 213

CERT_REQS = (
    (ssl.CERT_REQUIRED, _('Required')),
    (ssl.CERT_OPTIONAL, _('Optional')),
    (ssl.CERT_NONE, _('None')),
)
PROTO_SSL_VERSION = (
    (ssl.PROTOCOL_TLSv1, 'v1'),
    (ssl.PROTOCOL_SSLv23, 'v2.3'),
)
try:
    PROTO_SSL_VERSION.append((ssl.PROTOCOL_SSLv2, 'v2'))
except AttributeError:
    pass  # This protocol is not available if OpenSSL is compiled with the OPENSSL_NO_SSL2 flag.
try:
    PROTO_SSL_VERSION.append((ssl.PROTOCOL_SSLv3, 'v3'))
except AttributeError:
    pass  # This protocol is not be available if OpenSSL is compiled with the OPENSSL_NO_SSLv3 flag.
PROTO_MQTT_VERSION = (
    (mqtt.MQTTv31, 'v3.1'),
    (mqtt.MQTTv311, 'v3.1.1'),
)
PROTO_MQTT_QoS = (
    (MQTT_QoS0, _('QoS 0: Delivered at most once')),
    (MQTT_QoS1, _('QoS 1: Always delivered at least once')),
    (MQTT_QoS2, _('QoS 2: Always delivered exactly once')),
)
PROTO_MQTT_CONN_STATUS = (
    (PROTO_MQTT_CONN_OK, _('Connection successful')),
    (PROTO_MQTT_CONN_ERROR_PROTO_VERSION, _('Connection refused - incorrect protocol version')),
    (PROTO_MQTT_CONN_ERROR_INVALID_CLIENT, _('Connection refused - invalid client identifier')),
    (PROTO_MQTT_CONN_ERROR_UNAVAILABLE, _('Connection refused - server unavailable')),
    (PROTO_MQTT_CONN_ERROR_BAD_USER, _('Connection refused - bad username or password')),
    (PROTO_MQTT_CONN_ERROR_NOT_AUTH, _('Connection refused - not authorised')),
    (PROTO_MQTT_CONN_ERROR_UNKNOWN, _('Unknown')),

    (PROTO_MQTT_CONN_ERROR_GENERIC, _('Connection error')),
    (PROTO_MQTT_CONN_ERROR_ADDR_FAILED, _('Connection error - Get address info failed')),

    (PROTO_MQTT_CONN_ERROR_INTERRUPTED, _('Connection error - The operation was interrupted')),
    (PROTO_MQTT_CONN_ERROR_PERMISSION_DENIED, _('Connection error - Permission denied')),
    (PROTO_MQTT_CONN_ERROR_FAULT_NETWORK, _('Connection error - A fault occurred on the network')),
    (PROTO_MQTT_CONN_ERROR_INVALID, _('Connection error - An invalid operation was attempted')),
    (PROTO_MQTT_CONN_ERROR_BLOCK, _('Connection error - The socket operation would block')),
    (PROTO_MQTT_CONN_ERROR_BLOCKING, _('Connection error - A blocking operation is already in progress')),
    (PROTO_MQTT_CONN_ERROR_IN_USE, _('Connection error - The network address is in use')),
    (PROTO_MQTT_CONN_ERROR_RESET, _('Connection error - The connection has been reset')),
    (PROTO_MQTT_CONN_ERROR_SHUTDOWN, _('Connection error - The network has been shut down')),
    (PROTO_MQTT_CONN_ERROR_TIMEOUT, _('Connection error - The operation timed out')),
    (PROTO_MQTT_CONN_ERROR_REFUSED, _('Connection error - Connection refused')),
    (PROTO_MQTT_CONN_ERROR_TOO_LONG, _('Connection error - The name is too long')),
    (PROTO_MQTT_CONN_ERROR_DOWN, _('Connection error - The host is down')),
    (PROTO_MQTT_CONN_ERROR_UNREACHABLE, _('Connection error - The host is unreachable')),
)


private_location = settings.BASE_DIR
if hasattr(settings, 'MQTT_CERTS_ROOT'):
    private_location = settings.MQTT_CERTS_ROOT
private_fs = FileSystemStorage(location=private_location)


class SecureConf(models.Model):
    """
        :var ca_certs: a string path to the Certificate Authority certificate files that are to be treated as trusted
        by this client.
        If this is the only option given then the client will operate in a similar manner to a web browser.
        That is to say it will require the broker to have a certificate signed by the Certificate Authorities in
        ca_certs and will communicate using TLS v1, but will not attempt any form of authentication.
        This provides basic network encryption but may not be sufficient depending on how the broker is configured.

        :var cert_reqs: allows the certificate requirements that the client imposes on the broker to be changed.
        By default this is ssl.CERT_REQUIRED, which means that the broker must provide a certificate.

        :var tls_version: allows the version of the SSL/TLS protocol used to be specified.
        By default TLS v1 is used. Previous versions (all versions beginning with SSL) are possible but not recommended
        due to possible security problems.

        :var certfile and keyfile: are PEM encoded client certificate and private keys files respectively.
        If these arguments are not None then they will be used as client information for TLS based authentication.
        Support for this feature is broker dependent. Note that if either of these files in encrypted and needs a
        password to decrypt it, Python will ask for the password at the command line.

        :var ciphers: is a string specifying which encryption ciphers are allowable for this connection,
or None to use the defaults.
    """
    ca_certs = models.FileField(upload_to='ca', storage=private_fs)
    cert_reqs = models.IntegerField(choices=CERT_REQS, default=ssl.CERT_REQUIRED)
    tls_version = models.IntegerField(choices=PROTO_SSL_VERSION, default=ssl.PROTOCOL_TLSv1)
    certfile = models.FileField(upload_to='certs', storage=private_fs, blank=True, null=True)
    keyfile = models.FileField(upload_to='keys', storage=private_fs, blank=True, null=True)
    ciphers = models.CharField(max_length=1024, blank=True, null=True, default=None)


class Server(models.Model):
    """
        :var hostname : a string containing the address of the broker to connect to. Defaults to localhost.

        :var port : the port to connect to the broker on. Defaults to 1883.

        :var secure : the secure configuration. Default None.

        :var protocol : Setting of the MQTT version to use for this client. Can be mqtt.MQTTv31 or mqttt.MQTTv311
        If the broker reports that the client connected with an invalid protocol version,
        the client will automatically attempt to reconnect using v3.1 instead. Default mqttt.MQTTv311
    """
    host = models.CharField(max_length=1024)
    port = models.IntegerField(default=1883)
    secure = models.ForeignKey(SecureConf, null=True, blank=True)
    protocol = models.IntegerField(choices=PROTO_MQTT_VERSION, default=mqtt.MQTTv311)
    status = models.IntegerField(choices=PROTO_MQTT_CONN_STATUS, default=PROTO_MQTT_CONN_ERROR_UNKNOWN)

    class Meta:
        unique_together = ['host', 'port']

    def __str__(self):
        return "mqtt://%s:%s" % (self.host, self.port)

    def __unicode__(self):
        return "mqtt://%s:%s" % (self.host, self.port)


class Auth(models.Model):
    """
        :var user : a string containing user name

        :var password : a string containing user password
    """
    user = models.CharField(max_length=1024)
    password = models.CharField(max_length=1024, blank=True, null=True)

    def __str__(self):
        return "%s:%s" % (self.user, '*' * len(self.password))

    def __unicode__(self):
        return "%s:%s" % (self.user, '*' * len(self.password))


class Client(models.Model):
    """
        :var server : the server data for send information.

        :var server : the server data for send information.

        :var keepalive : the keepalive timeout value for the client. Defaults to 60 seconds.

        :var clean_session : is a boolean that determines the client type. If True, the broker will remove all
        information about this client when it disconnects.
        If False, the client is a persistent client and subscription information and queued messages will be retained
        when the client disconnects.
    """
    server = models.ForeignKey(Server)
    auth = models.ForeignKey(Auth, blank=True, null=True)
    client_id = models.ForeignKey(ClientId, null=True, blank=True)

    keepalive = models.IntegerField(default=60)
    clean_session = models.BooleanField(default=True)

    def __str__(self):
        return "%s - %s" % (self.client_id, self.server)

    def __unicode__(self):
        return "%s - %s" % (self.client_id, self.server)

    def get_mqtt_client(self, empty_client_id=False):
        client_id = None
        clean = True
        if self.client_id:
            client_id = self.client_id.name
            clean = self.clean_session
            if not self.clean_session and empty_client_id:
                client_id = None
        cli = mqtt.Client(client_id, clean, protocol=self.server.protocol)
        if self.server.secure:  # TODO use it! pragma: no cover
            tls_args = {
                'cert_reqs': self.server.secure.cert_reqs,
                'tls_version': self.server.secure.tls_version,
                'ciphers': self.server.secure.ciphers
            }
            if self.server.secure.certfile:
                tls_args['certfile'] = self.server.secure.certfile.name
            if self.server.secure.keyfile:
                tls_args['keyfile'] = self.server.secure.keyfile.path
            cli.tls_set(self.server.secure.ca_certs, **tls_args)

        if self.auth:
            cli.username_pw_set(self.auth.user, self.auth.password)
        return cli


class Data(models.Model):
    """
        :var client : the client id to send information.

        :var topic : the server topic.

        :var keepalive : the keepalive timeout value for the client. Defaults to 60 seconds.

        :var qos : Quality of Service code

        :var payload : The payload to send

        :var retain : If retain the data

        :var datetime : Datetime of last change
    """
    client = models.ForeignKey(Client)
    topic = models.ForeignKey(Topic)
    qos = models.IntegerField(choices=PROTO_MQTT_QoS, default=0)
    payload = models.BinaryField(blank=True, null=True)
    retain = models.BooleanField(default=False)
    datetime = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['client', 'topic']

    def __str__(self):
        return "%s - %s - %s" % (self.payload, self.topic, self.client)

    def __unicode__(self):
        return "%s - %s - %s" % (self.payload, self.topic, self.client)

    def update_remote(self):
        cli = self.client.get_mqtt_client(empty_client_id=self.client.client_id is None)
        try:
            mqtt_connect.send(sender=Server.__class__, client=self.client)
            cli.connect(self.client.server.host, self.client.server.port, self.client.keepalive)
            mqtt_pre_publish.send(sender=Data.__class__, client=self.client,
                                  topic=self.topic, payload=self.payload, qos=self.qos, retain=self.retain)
            (rc, mid) = cli.publish(self.topic.name, payload=self.payload, qos=self.qos, retain=self.retain)
            self.client.server.status = rc
            self.client.server.save()
            mqtt_publish.send(sender=Client.__class__, client=self.client, userdata=cli._userdata, mid=mid)
            cli.loop_write()
            if not self.client.clean_session and not self.client.client_id:
                name = cli._client_id.split('/')[-1]  # Filter for auto-gen in format paho/CLIENT_ID
                cli_id, is_new = ClientId.objects.get_or_create(name=name)
                self.client.client_id = cli_id
                self.client.save()
            cli.disconnect()
            mqtt_disconnect.send(sender=Server.__class__, client=self.client, userdata=cli._userdata, rc=rc)
        except socket.gaierror as ex:  # pragma: no cover
            if ex.errno == 11004:
                self.client.server.status = PROTO_MQTT_CONN_ERROR_ADDR_FAILED
            else:
                self.client.server.status = PROTO_MQTT_CONN_ERROR_GENERIC
            self.client.server.save()
        except IOError as ex:  # pragma: no cover
            # See in socket: WSA error codes
            if ex.errno == 10004:
                self.client.server.status = PROTO_MQTT_CONN_ERROR_INTERRUPTED
            elif ex.errno == 10013:
                self.client.server.status = PROTO_MQTT_CONN_ERROR_PERMISSION_DENIED
            elif ex.errno == 10014:
                self.client.server.status = PROTO_MQTT_CONN_ERROR_FAULT_NETWORK
            elif ex.errno == 10022:
                self.client.server.status = PROTO_MQTT_CONN_ERROR_INVALID
            elif ex.errno == 10035:
                self.client.server.status = PROTO_MQTT_CONN_ERROR_BLOCK
            elif ex.errno == 10036:
                self.client.server.status = PROTO_MQTT_CONN_ERROR_BLOCKING
            elif ex.errno == 10048:
                self.client.server.status = PROTO_MQTT_CONN_ERROR_IN_USE
            elif ex.errno == 10054:
                self.client.server.status = PROTO_MQTT_CONN_ERROR_RESET
            elif ex.errno == 10058:
                self.client.server.status = PROTO_MQTT_CONN_ERROR_SHUTDOWN
            elif ex.errno == 10060:
                self.client.server.status = PROTO_MQTT_CONN_ERROR_TIMEOUT
            elif ex.errno == 10061:
                self.client.server.status = PROTO_MQTT_CONN_ERROR_REFUSED
            elif ex.errno == 10063:
                self.client.server.status = PROTO_MQTT_CONN_ERROR_TOO_LONG
            elif ex.errno == 10064:
                self.client.server.status = PROTO_MQTT_CONN_ERROR_DOWN
            elif ex.errno == 10065:
                self.client.server.status = PROTO_MQTT_CONN_ERROR_UNREACHABLE
            else:
                self.client.server.status = PROTO_MQTT_CONN_ERROR_GENERIC
            self.client.server.save()
