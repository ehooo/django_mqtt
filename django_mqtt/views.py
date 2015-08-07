from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.generic.base import View
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth import authenticate


class MQTTAuth(View):
    http_method_names = ['post', 'head', 'options']

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(MQTTAuth, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        user = authenticate(username=request.DATA.get('username'), password=request.DATA.get('password'))
        if not user:
            return HttpResponseForbidden('')
        return HttpResponse('')


class MQTTSuperuser(View):
    http_method_names = ['post', 'head', 'options']
    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super(MQTTSuperuser, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        try:
            user = User.objects.get(username=request.DATA.get('username'))
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
        user = None
        try:
            user = User.objects.get(username=request.DATA.get('username'))
        except User.DoesNotExist:
            pass
        if not user:
            return HttpResponseForbidden('')
        topic = request.DATA.get('topic')
        if not topic:
            return HttpResponseBadRequest('')
        acc = request.DATA.get('acc')
        if not acc or acc not in [1, 2]:  # 1 == SUB, 2 == PUB
            return HttpResponseBadRequest('')
        # TODO check on DB for ACL

        return HttpResponse('')
