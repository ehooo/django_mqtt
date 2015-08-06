from django_mqtt import models

from django.contrib import admin


class SecureConfAdmin(admin.ModelAdmin):
    search_fields = ('ca_certs', 'ciphers')
    list_filter = ('cert_reqs', 'tls_version')


class ServerAdmin(admin.ModelAdmin):
    search_fields = ('host',)
    list_filter = ('protocol',)
    readonly_fields = ('status',)


class AuthAdmin(admin.ModelAdmin):
    search_fields = ('user',)


class ClientAdmin(admin.ModelAdmin):
    pass


class DataLogAdmin(admin.ModelAdmin):
    search_fields = ('topic', 'payload')
    list_filter = ('qos', 'datetime', 'retain')
    readonly_fields = ('datetime',)
    ordering = ('-datetime',)
    date_hierarchy = 'datetime'


admin.site.register(models.MQTTSecureConf, SecureConfAdmin)
admin.site.register(models.MQTTServer, ServerAdmin)
admin.site.register(models.MQTTAuth, AuthAdmin)
admin.site.register(models.MQTTClient, ClientAdmin)
admin.site.register(models.MQTTData, DataLogAdmin)
