from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [
    # Examples:
    # url(r'^$', 'test_web.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', admin.site.urls),
    url(r'^mqtt/', include('django_mqtt.mosquitto.auth_plugin.urls', namespace='mqtt')),
]
