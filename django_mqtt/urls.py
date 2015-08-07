from django.conf.urls import patterns, url
import django_mqtt.views as views

urlpatterns = patterns(
    '',
    url(r'^auth$', views.MQTTAuth.as_view(), name='auth'),
    url(r'^superuser$', views.MQTTSuperuser.as_view(), name='superuser'),
    url(r'^acl$', views.MQTTAcl.as_view(), name='acl'),
)
