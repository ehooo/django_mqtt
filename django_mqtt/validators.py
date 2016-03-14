
from django.utils.translation import ugettext_lazy as _
from django.utils.deconstruct import deconstructible
from django.core.exceptions import ValidationError
from django.utils.encoding import force_text
from django_mqtt.protocol import *


@deconstructible
class ClientIdValidator(object):
    regex = MQTT_CLIENT_ID_RE
    message = _('Enter a valid value.')
    code = 'invalid'
    valid_empty = False

    def __init__(self, valid_empty=None):
        if valid_empty is not None:
            self.valid_empty = bool(valid_empty)

    def __call__(self, value):
        """
        Validates that the input matches with valid client id, otherwise raises ValidationError.
        """
        if self.valid_empty and len(value) == 0:
            return
        found = self.regex.search(force_text(value))
        if not found:
            raise ValidationError(self.message, code=self.code)
        cli = found.group('client')
        if cli != value:
            raise ValidationError(self.message, code=self.code)

client_id_validator = ClientIdValidator()


@deconstructible
class TopicValidator(object):
    regex = MQTT_TOPIC_RE
    messages = {
        'only_wildcards': _('Only wildcards are allowed'),
        'not_wildcards': _('Wildcards are not allowed'),
        'wrong_wildcards': _('Validator config error, topic always invalid'),
    }
    message = _('Enter a valid value.')
    code = 'invalid'
    only_wildcards = False
    not_wildcards = False

    def __init__(self, only_wildcards=None, not_wildcards=None):
        if only_wildcards is not None:
            self.only_wildcards = bool(only_wildcards)
        if not_wildcards is not None:
            self.not_wildcards = bool(not_wildcards)

    def __call__(self, value):
        """
            Validates that the input matches with valid client id, otherwise raises ValidationError.
        """
        topic = force_text(value)
        if self.not_wildcards and self.only_wildcards:
            raise ValidationError(self.messages['wrong_wildcards'], code='wrong_wildcards')
        elif WILDCARD_MULTI_LEVEL in topic or WILDCARD_SINGLE_LEVEL in topic:  # Is wildcard?
            if self.not_wildcards:
                raise ValidationError(self.messages['not_wildcards'], code='not_wildcards')
        elif self.only_wildcards:
            raise ValidationError(self.messages['only_wildcards'], code='only_wildcards')

        found = self.regex.search(topic)
        if not found:
            raise ValidationError(self.message, code=self.code)
        if found.group('topic') != value:
            raise ValidationError(self.message, code=self.code)

topic_validator = TopicValidator()
