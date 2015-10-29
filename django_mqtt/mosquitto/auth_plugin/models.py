from django.conf import settings
from django.db import models

PROTO_MQTT_ACC_SUS = 1
PROTO_MQTT_ACC_PUB = 2
PROTO_MQTT_ACC = (
    (PROTO_MQTT_ACC_SUS, 'Suscriptor'),
    (PROTO_MQTT_ACC_PUB, 'Publisher'),
)


class MQTT_ACL(models.Model):
    allow = models.BooleanField(default=True)
    topic = models.CharField(max_length=1024)
    acc = models.IntegerField(choices=PROTO_MQTT_ACC)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True)
