from django.http import HttpResponse, HttpResponseForbidden
from django.views.generic.base import View
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.conf import settings

from django_mqtt.mosquitto.auth_plugin.models import MQTT_ACL


class MQTTAuth(View):
    http_method_names = ['post', 'head', 'options']

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(MQTTAuth, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        if hasattr(request, 'POST'):
            data = request.POST
        elif hasattr(request, 'DATA'):
            data = request.DATA

        user = authenticate(username=data.get('username'), password=data.get('password'))
        if not user or not user.is_active:
            return HttpResponseForbidden('')
        return HttpResponse('')


class MQTTSuperuser(View):
    http_method_names = ['post', 'head', 'options']

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super(MQTTSuperuser, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        if hasattr(request, 'POST'):
            data = request.POST
        elif hasattr(request, 'DATA'):
            data = request.DATA
        try:
            user = User.objects.get(username=data.get('username'))
            if user.is_superuser:
                return HttpResponse('')
        except User.DoesNotExist:
            pass
        return HttpResponseForbidden('')


class MQTTAcl(View):
    http_method_names = ['post', 'head', 'options']

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(MQTTAcl, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        if hasattr(request, 'POST'):
            data = request.POST
        elif hasattr(request, 'DATA'):
            data = request.DATA
        allow = False
        if hasattr(settings, 'MQTT_ACL_ALLOW'):
            allow = settings.MQTT_ACL_ALLOW
        try:
            acl = MQTT_ACL.objects.filter(acc=data.get('acc', None), topic=data.get('topic', None))
            def_acl = acl.filter(user__isnull=True).first()
            if def_acl:
                allow = def_acl.allow
            user = User.objects.get(username=data.get('username'))
            user_allow = acl.filter(user=user).first()
            if user_allow:
                allow = user_allow.allow
        except User.DoesNotExist:
            if allow and hasattr(settings, 'MQTT_ACL_ALLOW_ANONIMOUS'):
                allow = settings.MQTT_ACL_ALLOW_ANONIMOUS
        if not allow:
            return HttpResponseForbidden('')
        return HttpResponse('')
