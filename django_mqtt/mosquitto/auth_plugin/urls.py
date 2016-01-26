from django.conf.urls import url
import django_mqtt.mosquitto.auth_plugin.views as views

urlpatterns = [
    url(r'^auth$', views.MQTTAuth.as_view(), name='mqtt_auth'),
    url(r'^superuser$', views.MQTTSuperuser.as_view(), name='mqtt_superuser'),
    url(r'^acl$', views.MQTTAcl.as_view(), name='mqtt_acl'),
]
