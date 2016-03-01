from django.http import HttpResponse, HttpResponseForbidden
from django.views.generic.base import View
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.db.models import Q
from django.contrib.auth import authenticate
from django.conf import settings

from django_mqtt.models import *


class Auth(View):
    http_method_names = ['post', 'head', 'options']

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(Auth, self).dispatch(*args, **kwargs)

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


class Superuser(View):
    http_method_names = ['post', 'head', 'options']

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super(Superuser, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        if hasattr(request, 'POST'):
            data = request.POST
        elif hasattr(request, 'DATA'):
            data = request.DATA
        try:
            user = User.objects.get(username=data.get('username'), is_active=True)
            if user.is_superuser:
                return HttpResponse('')
        except User.DoesNotExist:
            pass
        return HttpResponseForbidden('')


class Acl(View):
    http_method_names = ['post', 'head', 'options']

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(Acl, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        if hasattr(request, 'POST'):
            data = request.POST
        elif hasattr(request, 'DATA'):
            data = request.DATA
        allow = False
        if hasattr(settings, 'MQTT_ACL_ALLOW'):
            allow = settings.MQTT_ACL_ALLOW

        topic, new_topic = Topic.objects.get_or_create(name=data.get('topic', '#'))
        acc = data.get('acc', None)
        user = None
        user_ = User.objects.filter(username=data.get('username'), is_active=True)
        if user_.count() > 0:
            user = user_[0]

        acl = None
        if not new_topic:
            acl_ = ACL.objects.filter(acc=acc, topic=topic)  # ACL only count have one or none
            if acl_.count() > 0:
                acl = acl_[0]

        if acl is None:
            allow = ACL.get_default(acc=acc, user=user)
            # TODO search best candidate

        if acl:
            if acl.is_public():
                allow = acl.allow
            elif user and acl.users.filter(pk=user.pk).count() > 0:
                allow = acl.allow
            elif user and acl.groups.filter(pk__in=user.groups.all().values_list('pk')).count() > 0:
                allow = acl.allow
            else:
                allow = not acl.allow

        if allow and hasattr(settings, 'MQTT_ACL_ALLOW_ANONIMOUS'):
            if user is None:
                allow = settings.MQTT_ACL_ALLOW_ANONIMOUS
            elif user.is_anonymous():
                allow = settings.MQTT_ACL_ALLOW_ANONIMOUS

        if not allow:
            return HttpResponseForbidden('')
        return HttpResponse('')
