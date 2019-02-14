
from django_mqtt.models import ACL, PROTO_MQTT_ACC
from django.conf import settings


def has_permission(user, topic, acc=None, clientid=None):
    """
    :param user: Active user
    :type user: django.contrib.auth.models.User
    :param topic:
    :type topic: str
    :param acc:
    :type acc: int
    :param clientid:
    :type clientid: django_mqtt.models.ClientId
    :return: If user have permission to access to topic
    :rtype: bool
    """

    allow = False
    if hasattr(settings, 'MQTT_ACL_ALLOW'):
        allow = settings.MQTT_ACL_ALLOW
    if hasattr(settings, 'MQTT_ACL_ALLOW_ANONIMOUS'):
        if user is None or user.is_anonymous():
            allow = settings.MQTT_ACL_ALLOW_ANONIMOUS & allow
            if not allow:
                return allow

    if user and not user.is_active:
        return allow

    acls = ACL.objects.filter(topic__name=topic)
    if acc not in dict(PROTO_MQTT_ACC).keys():
        acc = None

    if acc and acls.filter(acc=acc).exists():
        acl = acls.filter(acc=acc).get()
        allow = acl.has_permission(user=user)
    else:
        allow = ACL.get_default(acc, user=user)

        # TODO search best candidate

    return allow
