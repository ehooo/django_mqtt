from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
import django.dispatch

import paho.mqtt.client as mqtt
import ssl
import socket

mqtt_publish = django.dispatch.Signal(providing_args=["client", "userdata", "mid"])
mqtt_disconnect = django.dispatch.Signal(providing_args=["client", "userdata", "rc"])


def get_mqtt_client(client):
    if not isinstance(client, MQTTClient):
        raise AttributeError('client must by instance of %s' % MQTTClient.__class__)
    cli = mqtt.Client(client.client_id, client.clean_session, protocol=client.server.protocol)

    if client.server.secure:
        tls_args = {
            'cert_reqs': client.server.secure.cert_reqs,
            'tls_version': client.server.secure.tls_version,
            'ciphers': client.server.secure.ciphers
        }
        if client.server.secure.certfile:  # TODO check the path
            tls_args['certfile'] = client.server.secure.certfile.name
        if client.server.secure.keyfile:
            tls_args['keyfile'] = client.server.secure.keyfile.path
        cli.tls_set(client.server.secure.ca_certs, **tls_args)

    if client.auth:
        cli.username_pw_set(client.auth.user, client.auth.password)
    return cli


def update_mqtt_data(sender, **kwargs):
    is_new = False
    obj = kwargs["instance"]
    if isinstance(obj, MQTTData):
        if kwargs["created"]:
            is_new = True
        if is_new:
            pass
        cli = get_mqtt_client(obj.client)
        try:
            cli.connect(obj.client.server.host, obj.client.server.port, obj.client.keepalive)
            (rc, mid) = cli.publish(obj.topic, obj.payload, obj.qos, obj.retain)

            obj.client.server.status = rc
            obj.client.server.save()
            mqtt_publish.send(sender=MQTTClient.__class__, client=obj.client, userdata=cli._userdata, mid=mid)
            cli.loop_write()
            if not obj.client.client_id:
                obj.client.client_id = cli._client_id
                obj.client.save()
            cli.disconnect()
            mqtt_disconnect.send(sender=MQTTServer.__class__, client=obj.client, userdata=cli._userdata, rc=rc)
        except socket.gaierror as ex:
            # See PROTO_MQTT_CONN_ERROR
            if ex.errno == 11004:
                obj.client.server.status = 191
            else:
                obj.client.server.status = 100
            obj.client.server.save()
        except IOError as ex:
            # See in socket: WSA error codes
            if ex.errno == 10004:
                obj.client.server.status = 200
            elif ex.errno == 10013:
                obj.client.server.status = 201
            elif ex.errno == 10014:
                obj.client.server.status = 202
            elif ex.errno == 10022:
                obj.client.server.status = 203
            elif ex.errno == 10035:
                obj.client.server.status = 204
            elif ex.errno == 10036:
                obj.client.server.status = 205
            elif ex.errno == 10048:
                obj.client.server.status = 206
            elif ex.errno == 10054:
                obj.client.server.status = 207
            elif ex.errno == 10058:
                obj.client.server.status = 208
            elif ex.errno == 10060:
                obj.client.server.status = 209
            elif ex.errno == 10061:
                obj.client.server.status = 210
            elif ex.errno == 10063:
                obj.client.server.status = 211
            elif ex.errno == 10064:
                obj.client.server.status = 212
            elif ex.errno == 10065:
                obj.client.server.status = 213
            else:
                obj.client.server.status = 100
            obj.client.server.save()


CERT_REQS = (
    (ssl.CERT_REQUIRED, 'Required'),
    (ssl.CERT_OPTIONAL, 'Optional'),
    (ssl.CERT_NONE, 'None'),
)
PROTO_SSL_VERSION = (
    (ssl.PROTOCOL_TLSv1, 'v1'),
    (ssl.PROTOCOL_SSLv2, 'v2'),
    (ssl.PROTOCOL_SSLv23, 'v2.3'),
    (ssl.PROTOCOL_SSLv3, 'v3'),
)
PROTO_MQTT_VERSION = (
    (mqtt.MQTTv31, 'v3.1'),
    (mqtt.MQTTv311, 'v3.1.1'),
)
PROTO_MQTT_QoS = (
    (0, 'QoS 0: Delivered at most once'),
    (1, 'QoS 1: Always delivered at least once'),
    (2, 'QoS 2: Always delivered exactly once'),
)
PROTO_MQTT_CONN_ERROR = (
    (0, 'Connection successful'),
    (1, 'Connection refused - incorrect protocol version'),
    (2, 'Connection refused - invalid client identifier'),
    (3, 'Connection refused - server unavailable'),
    (4, 'Connection refused - bad username or password'),
    (5, 'Connection refused - not authorised'),
    (6, 'Unknow'),

    (100, 'Connection error'),
    (191, 'Connection error - Get address info failed'),

    (200, 'Connection error - The operation was interrupted'),
    (201, 'Connection error - Permission denied'),
    (202, 'Connection error - A fault occurred on the network'),
    (203, 'Connection error - An invalid operation was attempted'),
    (204, 'Connection error - The socket operation would block'),
    (205, 'Connection error - A blocking operation is already in progress'),
    (206, 'Connection error - The network address is in use'),
    (207, 'Connection error - The connection has been reset'),
    (208, 'Connection error - The network has been shut down'),
    (209, 'Connection error - The operation timed out'),
    (210, 'Connection error - Connection refused'),
    (211, 'Connection error - The name is too long'),
    (212, 'Connection error - The host is down'),
    (213, 'Connection error - The host is unreachable'),
)


private_fs = FileSystemStorage(location=settings.PRIVATE_ROOT)


class MQTTSecureConf(models.Model):
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
    ca_certs = models.CharField(max_length=1024)
    cert_reqs = models.IntegerField(choices=CERT_REQS, default=ssl.CERT_REQUIRED)
    tls_version = models.IntegerField(choices=PROTO_SSL_VERSION, default=ssl.PROTOCOL_TLSv1)
    certfile = models.FileField(upload_to='certs', storage=private_fs, blank=True, null=True)
    keyfile = models.FileField(upload_to='keys', storage=private_fs, blank=True, null=True)
    ciphers = models.CharField(max_length=1024, blank=True, null=True, default=None)


class MQTTServer(models.Model):
    """
        :var hostname : a string containing the address of the broker to connect to. Defaults to localhost.

        :var port : the port to connect to the broker on. Defaults to 1883.

        :var secure : the secure configuration. Default None.

        :var protocol : Setting of the MQTT version to use for this client. Can be mqtt.MQTTv31 or mqttt.MQTTv311
        If the broker reports that the client connected with an invalid protocol version,
        the client will automatically attempt to reconnect using v3.1 instead. Default mqttt.MQTTv311
    """
    host = models.CharField(max_length=1024, blank=True, null=True)
    port = models.IntegerField(default=1883)
    secure = models.ForeignKey(MQTTSecureConf, null=True, blank=True)
    protocol = models.IntegerField(choices=PROTO_MQTT_VERSION, default=mqtt.MQTTv311)
    status = models.IntegerField(choices=PROTO_MQTT_CONN_ERROR, default=6)

    def __str__(self):
        return "mqtt://%s:%s" % (self.host, self.port)

    def __unicode__(self):
        return "mqtt://%s:%s" % (self.host, self.port)


class MQTTAuth(models.Model):
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


class MQTTClient(models.Model):
    """
        :var server : the server data for send information.

        :var server : the server data for send information.

        :var keepalive : the keepalive timeout value for the client. Defaults to 60 seconds.

        :var clean_session : is a boolean that determines the client type. If True, the broker will remove all
        information about this client when it disconnects.
        If False, the client is a persistent client and subscription information and queued messages will be retained
        when the client disconnects.
    """
    server = models.ForeignKey(MQTTServer)
    auth = models.ForeignKey(MQTTAuth, blank=True, null=True)
    client_id = models.CharField(max_length=1024, blank=True, null=True)

    keepalive = models.IntegerField(default=60)
    clean_session = models.BooleanField(default=True)

    def __str__(self):
        return "%s - %s" % (self.client_id, self.server)

    def __unicode__(self):
        return "%s - %s" % (self.client_id, self.server)


class MQTTData(models.Model):
    """
        :var client : the client id to send information.

        :var topic : the server topic.

        :var keepalive : the keepalive timeout value for the client. Defaults to 60 seconds.

        :var qos : Quality of Service code

        :var payload : The payload to send

        :var retain : If retain the data

        :var datetime : Datetime of last change
    """
    client = models.ForeignKey(MQTTClient)
    topic = models.CharField(max_length=1024)
    qos = models.IntegerField(choices=PROTO_MQTT_QoS, default=0)
    payload = models.TextField(blank=True, null=True)
    retain = models.BooleanField(default=False)
    datetime = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['client', 'topic']

    def __str__(self):
        return "%s - %s - %s" % (self.payload, self.topic, self.client)

    def __unicode__(self):
        return "%s - %s - %s" % (self.payload, self.topic, self.client)

post_save.connect(receiver=update_mqtt_data, sender=MQTTData, dispatch_uid='django_mqtt_update_signal')