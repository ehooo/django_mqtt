from datetime import datetime
from datetime import timedelta
import hashlib
import six

from django_mqtt.validators import *
from django.contrib.auth.models import User, Group
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.db.models import Q
from django.db import models


from django_mqtt.protocol import WILDCARD_SINGLE_LEVEL, WILDCARD_MULTI_LEVEL
from django_mqtt.protocol import TOPIC_SEP, TOPIC_BEGINNING_DOLLAR


PROTO_MQTT_ACC_SUS = 1
PROTO_MQTT_ACC_PUB = 2
PROTO_MQTT_ACC = (
    (PROTO_MQTT_ACC_SUS, _('Suscriptor')),
    (PROTO_MQTT_ACC_PUB, _('Publisher')),
)

ALLOW_EMPTY_CLIENT_ID = False
if hasattr(settings, 'MQTT_ALLOW_EMPTY_CLIENT_ID'):
    ALLOW_EMPTY_CLIENT_ID = settings.MQTT_ALLOW_EMPTY_CLIENT_ID


class SecureSave(models.Model):
    class Meta:
        abstract = True

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.full_clean()
        return super(SecureSave, self).save(force_insert=force_insert, force_update=force_update,
                                          using=using, update_fields=update_fields)


class ClientId(SecureSave):
    name = models.CharField(max_length=23, db_index=True, blank=True,
                            validators=[ClientIdValidator(valid_empty=ALLOW_EMPTY_CLIENT_ID)])
    users = models.ManyToManyField(User, blank=True)
    groups = models.ManyToManyField(Group, blank=True)

    def is_public(self):
        return self.users.count() == 0 and self.groups.count() == 0

    def has_permission(self, user):
        if not self.is_public():
            if user:
                if self.users.filter(pk=user.pk):
                    return True
                elif self.groups.filter(pk__in=user.groups.all().values_list('pk')).count() > 0:
                    return True
        return self.is_public()

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name

    def clean(self):
        if not hasattr(settings, 'MQTT_ALLOW_EMPTY_CLIENT_ID') or not settings.MQTT_ALLOW_EMPTY_CLIENT_ID:
            if self.name == '':
                raise ValidationError('Empty client_id not allowed', code='invalid')


class Topic(SecureSave):
    name = models.CharField(max_length=1024, validators=[TopicValidator()], db_index=True, unique=True, blank=False)
    wildcard = models.BooleanField(default=False)
    dollar = models.BooleanField(default=False)

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

    def __lt__(self, other):
        comp = None
        if isinstance(other, Topic):
            comp = other
        elif isinstance(other, six.string_types) or isinstance(other, six.text_type):
            comp = Topic(name=other)
        if not comp or not comp.is_wildcard():
            return False
        return self in comp

    def __len__(self):
        return len(self.name)

    def __gt__(self, other):
        if not self.is_wildcard():
            return False
        if isinstance(other, Topic):
            return other in self
        elif isinstance(other, six.string_types) or isinstance(other, six.text_type):
            return Topic(other) in self
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

        comp_size = len(comp_parts)
        if comp_size < len(my_parts):
            return False
        if not self.name.endswith(WILDCARD_MULTI_LEVEL) and comp_size > len(my_parts):
            return False

        iter_comp = iter(comp_parts)
        for part in my_parts:
            compare = iter_comp.next()
            if part == WILDCARD_SINGLE_LEVEL:
                if comp.is_wildcard() and compare == WILDCARD_MULTI_LEVEL:
                    return False
            elif part == WILDCARD_MULTI_LEVEL:
                return True
            elif part != compare:
                return False
        return True

    def get_candidates(self):
        candidates = Topic.objects.filter(dollar=self.is_dollar(), wildcard=False)
        init = Topic.objects.filter(dollar=self.is_dollar(), wildcard=False)
        topic = self.name
        multi = False
        if topic.endswith(WILDCARD_MULTI_LEVEL):
            topic = topic[:-1]
            multi = True

        parts = topic.split(WILDCARD_SINGLE_LEVEL)
        if len(parts) == 1:
            if len(topic) != 0:
                candidates = candidates.filter(name__startswith=topic)
        elif topic == WILDCARD_SINGLE_LEVEL:
            candidates = candidates.exclude(name__contains=TOPIC_SEP)
        else:
            if multi:
                ini = candidates.filter(name__startswith=parts[0])
                con = candidates.filter(name__contains=parts[-1])
                candidates = candidates.filter(name__startswith=parts[0], name__contains=parts[-1])
            else:
                candidates = candidates.filter(name__startswith=parts[0], name__endswith=parts[-1])
            for part in set(parts[1:-1]):
                candidates = candidates.filter(name__contains=part)
        return candidates

    def __iter__(self):
        if not self.is_wildcard():
            yield self
        else:
            for candidate in self.get_candidates().all():
                if candidate in self:
                    yield candidate

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.wildcard = self.is_wildcard()
        self.dollar = self.is_dollar()
        return super(Topic, self).save(force_insert=force_insert, force_update=force_update,
                                       using=using, update_fields=update_fields)


class ACL(models.Model):
    allow = models.BooleanField(default=True)
    topic = models.ForeignKey(Topic)  # There is many of acc options by topic
    acc = models.IntegerField(choices=PROTO_MQTT_ACC)
    users = models.ManyToManyField(User, blank=True)
    groups = models.ManyToManyField(Group, blank=True)
    password = models.CharField(max_length=512, blank=True, null=True,
                                help_text='Only valid for connect')
    only_username = models.NullBooleanField(default=None,
                                            help_text='Only valid for connect')

    class Meta:
        unique_together = ('topic', 'acc')

    @classmethod
    def get_default(cls, acc, user=None, password=None):  # TODO rename
        """
            :type user: django.contrib.auth.models.User
            :param user:
            :return: bool
        """
        allow = False
        if hasattr(settings, 'MQTT_ACL_ALLOW'):
            allow = settings.MQTT_ACL_ALLOW
        if allow and hasattr(settings, 'MQTT_ACL_ALLOW_ANONIMOUS'):
            if user is None or user.is_anonymous():
                allow = settings.MQTT_ACL_ALLOW_ANONIMOUS
        try:
            broadcast_topic = Topic.objects.get(name=WILDCARD_MULTI_LEVEL)
            broadcast = cls.objects.get(topic=broadcast_topic, acc=acc)
            allow = broadcast.has_permission(user=user, password=password)
        except cls.DoesNotExist:
            pass
        except Topic.DoesNotExist:
            pass
        return allow

    def __gt__(self, other):
        if isinstance(other, ACL):
            return self.topic > other.topic

    def __lt__(self, other):
        if isinstance(other, ACL):
            return self.topic < other.topic

    @classmethod
    def get_acl(cls, topic, acc=PROTO_MQTT_ACC_PUB):
        if isinstance(topic, six.string_types) or isinstance(topic, six.text_type):
            topic, is_new = Topic.objects.get_or_create(name=topic)
        elif not isinstance(topic, Topic):
            raise ValueError('topic must be Topic or String')
        candidates = []
        try:
            candidates = [ACL.objects.get(topic=topic, acc=acc)]
        except ACL.DoesNotExist:
            for candidate in cls.objects.filter(topic__wildcard=True, acc=acc):
                if topic in candidate.topic:
                    candidates.append(candidate)
        if len(candidates) == 0:
            return None
        return min(candidates)

    def is_public(self):
        return self.users.count() == 0 and self.groups.count() == 0 and not self.password

    def has_permission(self, user=None, password=None):
        allow = False
        if self.is_public():
            allow = self.allow
        else:
            if user:
                if user in self.users.all() or\
                   self.groups.filter(pk__in=user.groups.all().values_list('pk')).count() > 0:
                    allow = self.allow
                else:
                    allow = not self.allow
            if self.password and password:
                allow = self.password == password
        return allow

    def __unicode__(self):
        return "ACL %s for %s" % (dict(PROTO_MQTT_ACC)[self.acc], self.topic)

    def __str__(self):
        return "ACL %s for %s" % (dict(PROTO_MQTT_ACC)[self.acc], self.topic)
