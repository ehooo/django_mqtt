from django_mqtt.mosquitto.auth_plugin import models

from django.contrib import admin


class AclAdmin(admin.ModelAdmin):
    search_fields = ('topic', )
    list_filter = ('acc', 'allow', )
    ordering = ('topic', )
    list_display = ('topic', 'allow', 'acc', 'user')

admin.site.register(models.MQTT_ACL, AclAdmin)
