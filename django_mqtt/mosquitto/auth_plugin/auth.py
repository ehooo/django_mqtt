
from django_mqtt.models import ACL, PROTO_MQTT_ACC


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
    if user and not user.is_active:
        return False

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

