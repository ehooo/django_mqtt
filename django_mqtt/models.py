from datetime import datetime
from datetime import timedelta
import random
import six

from django.core.validators import RegexValidator, MinLengthValidator
from django.contrib.auth.models import User, Group
from django.conf import settings
from django.db import models


from django_mqtt.protocol import WILDCARD_SINGLE_LEVEL, WILDCARD_MULTI_LEVEL
from django_mqtt.protocol import TOPIC_SEP, TOPIC_BEGINNING_DOLLAR


PROTO_MQTT_ACC_SUS = 1
PROTO_MQTT_ACC_PUB = 2
PROTO_MQTT_ACC = (
    (PROTO_MQTT_ACC_SUS, 'Suscriptor'),
    (PROTO_MQTT_ACC_PUB, 'Publisher'),
)


class Topic(models.Model):
    name = models.CharField(max_length=1024, validators=[
        MinLengthValidator(1),
    ], db_index=True, unique=True)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, Topic):
            return self.name == other.name
        elif isinstance(other, six.string_types) or isinstance(other, six.text_type):
            return self.name == other
        return False

    def is_wildcard(self):
        return WILDCARD_MULTI_LEVEL in self.name or WILDCARD_SINGLE_LEVEL in self.name

    def is_dollar(self):
        return self.name.startswith(TOPIC_BEGINNING_DOLLAR)

    def __contains__(self, item):
        comp = None
        if isinstance(item, Topic):
            comp = item
        elif isinstance(item, six.string_types) or isinstance(item, six.text_type):
            comp = Topic(name=item)
        if not comp:
            return False

        if self == comp:
            return True
        elif not self.is_wildcard():
            return False
        elif (self.is_dollar() and not comp.is_dollar()) or (comp.is_dollar() and not self.is_dollar()):
            return False

        my_parts = self.name.split(TOPIC_SEP)
        comp_parts = comp.name.split(TOPIC_SEP)
        if self.is_dollar():
            if my_parts[0] != comp_parts[0]:
                return False
        pos = -1
        comp_size = len(comp_parts)
        for part in my_parts:
            pos += 1
            if pos >= comp_size:
                return False
            if part == WILDCARD_SINGLE_LEVEL:
                continue
            elif part == WILDCARD_MULTI_LEVEL:
                return True
            if part != comp_parts[pos]:
                return False

        if comp_size == len(my_parts):
            return True
        return False


class ACL(models.Model):
    allow = models.BooleanField(default=True)
    topic = models.ForeignKey(Topic)  # There is many of acc options by topic
    acc = models.IntegerField(choices=PROTO_MQTT_ACC)
    users = models.ManyToManyField(User)
    groups = models.ManyToManyField(Group)

    class Meta:
        unique_together = ('topic', 'acc')

    @classmethod
    def get_acls(cls, topic, acc):
        comp = None
        if isinstance(topic, Topic):
            comp = topic
        elif isinstance(topic, six.string_types) or isinstance(topic, six.text_type):
            comp = Topic(name=topic)
        if not comp:
            return cls.objects.none()
        acls = cls.objects.filter(acc=acc)
        if comp.is_dollar():
            pass

    @classmethod
    def get_default(cls, acc, user=None):
        """
            :type user: django.contrib.auth.models.User
            :param user:
            :return: bool
        """
        allow = False
        if hasattr(settings, 'MQTT_ACL_ALLOW'):
            allow = settings.MQTT_ACL_ALLOW
        if allow and hasattr(settings, 'MQTT_ACL_ALLOW_ANONIMOUS'):
            if user is None:
                allow = settings.MQTT_ACL_ALLOW_ANONIMOUS
            elif user.is_anonymous():
                allow = settings.MQTT_ACL_ALLOW_ANONIMOUS
        try:
            broadcast_topic = Topic.objects.get(name='#')
            broadcast = cls.objects.get(topic=broadcast_topic, acc=acc)
            if broadcast.is_public():
                allow = broadcast.allow
            elif broadcast.users.filter(pk=user.pk).count() > 0:
                allow = broadcast.allow
            elif broadcast.groups.filter(pk__in=user.groups.all().values_list('pk')).count() > 0:
                allow = broadcast.allow
            else:
                allow = not broadcast.allow
        except cls.DoesNotExist:
            pass
        except Topic.DoesNotExist:
            pass
        return allow

    def is_public(self):
        return self.users.count() == 0 and self.groups.count()