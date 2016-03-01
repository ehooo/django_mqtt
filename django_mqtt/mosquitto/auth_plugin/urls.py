from django.conf.urls import url
import django_mqtt.mosquitto.auth_plugin.views as views

urlpatterns = [
    url(r'^auth$', views.Auth.as_view(), name='mqtt_auth'),
    url(r'^superuser$', views.Superuser.as_view(), name='mqtt_superuser'),
    url(r'^acl$', views.Acl.as_view(), name='mqtt_acl'),
]
