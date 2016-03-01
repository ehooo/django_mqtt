from django.contrib import admin

from django_mqtt.publisher import models


class SecureConfAdmin(admin.ModelAdmin):
    search_fields = ('ca_certs', 'ciphers')
    list_filter = ('cert_reqs', 'tls_version')
    list_display = ('ca_certs', 'cert_reqs', 'tls_version', 'ciphers')


class ServerAdmin(admin.ModelAdmin):
    search_fields = ('host',)
    list_filter = ('protocol',)
    readonly_fields = ('status',)
    list_display = ('host', 'port', 'protocol', 'status')


class AuthAdmin(admin.ModelAdmin):
    search_fields = ('user',)
    list_display = ('user', )


class ClientAdmin(admin.ModelAdmin):
    list_display = ('client_id', 'keepalive', 'clean_session')


class DataLogAdmin(admin.ModelAdmin):
    search_fields = ('topic', 'payload')
    list_filter = ('qos', 'datetime', 'retain')
    readonly_fields = ('datetime',)
    ordering = ('-datetime',)
    date_hierarchy = 'datetime'
    list_display = ('topic', 'qos', 'retain', 'datetime')

admin.site.register(models.SecureConf, SecureConfAdmin)
admin.site.register(models.Server, ServerAdmin)
admin.site.register(models.Auth, AuthAdmin)
admin.site.register(models.Client, ClientAdmin)
admin.site.register(models.Data, DataLogAdmin)
