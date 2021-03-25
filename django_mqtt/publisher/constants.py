import ssl

import paho.mqtt.client as mqtt

from django.utils.translation import ugettext_lazy as _
from django_mqtt.protocol import MQTT_QoS0, MQTT_QoS1, MQTT_QoS2

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

# See in socket: WSA error codes
IO_ERROR_MAP = {
    10004: PROTO_MQTT_CONN_ERROR_INTERRUPTED,
    10013: PROTO_MQTT_CONN_ERROR_PERMISSION_DENIED,
    10014: PROTO_MQTT_CONN_ERROR_FAULT_NETWORK,
    10022: PROTO_MQTT_CONN_ERROR_INVALID,
    10035: PROTO_MQTT_CONN_ERROR_BLOCK,
    10036: PROTO_MQTT_CONN_ERROR_BLOCKING,
    10048: PROTO_MQTT_CONN_ERROR_IN_USE,
    10054: PROTO_MQTT_CONN_ERROR_RESET,
    10058: PROTO_MQTT_CONN_ERROR_SHUTDOWN,
    10060: PROTO_MQTT_CONN_ERROR_TIMEOUT,
    10061: PROTO_MQTT_CONN_ERROR_REFUSED,
    10063: PROTO_MQTT_CONN_ERROR_TOO_LONG,
    10064: PROTO_MQTT_CONN_ERROR_DOWN,
    10065: PROTO_MQTT_CONN_ERROR_UNREACHABLE,
}

CERT_REQUIRED = int(ssl.CERT_REQUIRED)
CERT_OPTIONAL = int(ssl.CERT_OPTIONAL)
CERT_NONE = int(ssl.CERT_NONE)
CERT_REQS = (
    (CERT_REQUIRED, _('Required')),
    (CERT_OPTIONAL, _('Optional')),
    (CERT_NONE, _('None')),
)
PROTOCOL_TLSv1 = int(ssl.PROTOCOL_TLSv1)
PROTOCOL_SSLv23 = int(ssl.PROTOCOL_SSLv23)
PROTO_SSL_VERSION = [
    (PROTOCOL_TLSv1, 'v1'),
    (PROTOCOL_SSLv23, 'v2.3'),
]
if hasattr(ssl, 'PROTOCOL_SSLv2'):
    PROTO_SSL_VERSION.append((int(ssl.PROTOCOL_SSLv2), 'v2'))
    # This protocol is not available if OpenSSL is compiled with the OPENSSL_NO_SSL2 flag.
if hasattr(ssl, 'PROTOCOL_SSLv3'):
    PROTO_SSL_VERSION.append((int(ssl.PROTOCOL_SSLv3), 'v3'))
    # This protocol is not be available if OpenSSL is compiled with the OPENSSL_NO_SSLv3 flag.

MQTTv31 = int(mqtt.MQTTv31)
MQTTv311 = int(mqtt.MQTTv311)
PROTO_MQTT_VERSION = [
    (MQTTv31, 'v3.1'),
    (MQTTv311, 'v3.1.1'),
]
if hasattr(mqtt, 'MQTTv5'):
    PROTO_SSL_VERSION.append((int(mqtt.MQTTv5), 'v5'))

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
