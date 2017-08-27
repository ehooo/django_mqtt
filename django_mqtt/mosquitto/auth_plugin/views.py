from django.http import HttpResponse, HttpResponseForbidden
from django.views.generic.base import View
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model

from django_mqtt.models import Topic, ClientId, ACL, PROTO_MQTT_ACC
from django_mqtt.mosquitto.auth_plugin.auth import has_permission


class Auth(View):
    http_method_names = ['post', 'head', 'options']

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(Auth, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        """ HTTP response 200 to allow, 403 in other case
        Access if exist ACL with:
            - ACC, TOPIC and PASSWORD not matter the user
            - USERNAME and PASSWORD for an existing active user and with topic and acc

        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        data = {}
        if hasattr(request, 'POST'):
            data = request.POST
        elif hasattr(request, 'DATA'):  # pragma: no cover
            data = request.DATA

        topics = Topic.objects.filter(name=data.get('topic'))
        try:
            acc = int(data.get('acc', None))
        except:
            acc = None
        allow = False
        if topics.exists() and acc in dict(PROTO_MQTT_ACC).keys():
            topic = topics.get()
            acls = ACL.objects.filter(acc=acc, topic=topic,
                                      password__isnull=False, password=data.get('password'))
            if acls.exists():
                allow = True
        if not allow:
            user = authenticate(username=data.get('username'), password=data.get('password'))
            allow = has_permission(user, data.get('topic', '#'), acc)

        if not allow:
            return HttpResponseForbidden('')
        return HttpResponse('')


class Superuser(View):
    http_method_names = ['post', 'head', 'options']

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super(Superuser, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """ HTTP response 200 to user exist and is_superuser, 403 in other case
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        data = {}
        if hasattr(request, 'POST'):
            data = request.POST
        elif hasattr(request, 'DATA'):  # pragma: no cover
            data = request.DATA

        user_model = get_user_model()
        try:
            user = user_model.objects.get(username=data.get('username'), is_active=True)
            if user.is_superuser:
                return HttpResponse('')
        except user_model.DoesNotExist:
            pass
        return HttpResponseForbidden('')


class Acl(View):
    http_method_names = ['post', 'head', 'options']

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(Acl, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        """ HTTP response 200 to allow, 403 in other case
        see function django_mqtt.mosquitto.auth_plugin.utils.has_permission

        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        data = {}
        if hasattr(request, 'POST'):
            data = request.POST
        elif hasattr(request, 'DATA'):  # pragma: no cover
            data = request.DATA

        user = None
        users = get_user_model().objects.filter(username=data.get('username'), is_active=True)
        if users.exists():
            user = users.latest('pk')

        topic = None
        topics = Topic.objects.filter(name=data.get('topic', '#'))
        if topics.exists():
            topic = topics.get()

        clientid = None
        clientids = ClientId.objects.filter(name=data.get('clientid'))
        if clientids.exists():
            clientid = clientids.get()

        try:
            acc = int(data.get('acc', None))
        except:
            acc = None

        if not has_permission(user, topic, acc=acc, clientid=clientid):
            return HttpResponseForbidden('')
        return HttpResponse('')
