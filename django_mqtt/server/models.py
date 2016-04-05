from django_mqtt.publisher.signals import *
from django_mqtt.models import *
from django_mqtt.protocol import MQTT_QoS0, MQTT_QoS1, MQTT_QoS2

from datetime import timedelta

from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User, Group
from django.utils import timezone
from django.conf import settings
from django.db import models

SESSION_TIMEOUT = 60
if hasattr(settings, 'MQTT_SESSION_TIMEOUT'):
    SESSION_TIMEOUT = settings.MQTT_SESSION_TIMEOUT

PROTO_MQTT_QoS = (
    (MQTT_QoS0, _('QoS 0: Delivered at most once')),
    (MQTT_QoS1, _('QoS 1: Always delivered at least once')),
    (MQTT_QoS2, _('QoS 2: Always delivered exactly once')),
)


class Channel(models.Model):
    qos = models.IntegerField(choices=PROTO_MQTT_QoS, default=MQTT_QoS0)
    topic = models.ForeignKey(Topic)

    class Meta:
        unique_together = ('qos', 'topic')

    def __unicode__(self):
        return unicode('QoS%(qos)s - %(topic)s' % {'qos': self.qos, 'topic': self.topic})

    def __str__(self):
        return str('QoS%(qos)s - %(topic)s' % {'qos': self.qos, 'topic': self.topic})


class Session(models.Model):
    client_id = models.OneToOneField(ClientId)
    user = models.ForeignKey(User, blank=True, null=True)

    active = models.BooleanField(default=True)
    init_conn = models.DateTimeField(auto_now_add=True, editable=False)
    last_conn = models.DateTimeField(auto_now_add=True)
    last_update = models.DateTimeField(auto_now_add=True)

    keep_alive = models.IntegerField(default=0)

    subscriptions = models.ManyToManyField(Channel)
    unsubscriptions = models.ManyToManyField(Topic)

    def subscribe(self, channel=None, topic=None, qos=MQTT_QoS0):
        if not isinstance(channel, Channel):
            if not isinstance(topic, Topic):
                if isinstance(topic, six.string_types) or isinstance(topic, six.text_type):
                    topic, is_new = Topic.objects.get_or_create(name=topic)
                else:
                    raise ValueError('Channel or topic required')
            channel, is_new = Channel.objects.get_or_create(topic=topic, qos=qos)
        self.subscriptions.add(channel)
        self.unsubscriptions.remove(channel.topic)

    def unsubscribe(self, topic):
        if not isinstance(topic, Topic):
            if isinstance(topic, six.string_types) or isinstance(topic, six.text_type):
                topic, is_new = Topic.objects.get_or_create(name=topic)
            else:
                raise ValueError('topic must be string or Topic')
        candidates = self.subscriptions.filter(topic=topic)
        if candidates.exists():
            for ch in candidates:
                self.subscriptions.remove(ch)
        self.unsubscriptions.add(topic)

    def disconnect(self, clear=True):
        self.active = False
        Session.objects.filter(pk=self.pk, active=True).update(active=self.active)
        if clear:
            self.subscriptions.clear()
            self.unsubscriptions.clear()

    def ping(self):
        self.active = True
        self.last_update = timezone.now()
        Session.objects.filter(pk=self.pk).update(last_update=self.last_update, active=self.active)

    def is_alive(self, clear=False):
        if self.active:
            keep_until = self.last_update + timedelta(seconds=self.keep_alive)
            if keep_until < timezone.now():
                self.disconnect(clear)
        return self.active

    def __unicode__(self):
        return unicode('%(client_id)s - %(user)s' % {'client_id': self.client_id, 'user': self.user})

    def __str__(self):
        return str('%(client_id)s - %(user)s' % {'client_id': self.client_id, 'user': self.user})

    def is4me(self, topic, qos):
        if isinstance(topic, six.string_types) or isinstance(topic, six.text_type):
            topic, is_new = Topic.objects.get_or_create(name=topic)
        elif not isinstance(topic, Topic):
            raise ValueError('topic must be Topic or String')
        if not self.is_alive():
            return False
        not_cadidate = []
        for not_topic in self.unsubscriptions.all():
            if not not_topic.is_wildcard():
                if topic == not_topic:
                    return False
            elif topic in not_topic:
                not_cadidate.append(not_topic)

        acl = ACL.get_acl(topic, PROTO_MQTT_ACC_SUS)
        if acl and not acl.has_permission(self.user):
            return False
        candidates = []
        for channel in self.subscriptions.filter(qos__gte=qos):
            if not channel.topic.is_wildcard():
                if topic == channel.topic:
                    return True
            elif topic in channel.topic:
                if len(not_cadidate) > 0:
                    for not_topic in not_cadidate:
                        if not_topic > channel.topic:
                            candidates.append(channel.topic)
                else:
                    return True
        if len(candidates) > 0:
            return True
        return False


class Publication(models.Model):
    channel = models.ForeignKey(Channel)
    remain = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now=True)
    message = models.BinaryField(blank=True, null=True)
    packet_id = models.IntegerField(default=-1)

    class Meta:
        unique_together = ('channel', 'remain')

    def __unicode__(self):
        return unicode('%(date)s: %(channel)s' % {'channel': self.channel, 'date': self.date})

    def __str__(self):
        return str('%(date)s: %(channel)s' % {'channel': self.channel, 'date': self.date})
