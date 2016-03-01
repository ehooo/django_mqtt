from django_mqtt import models

from django.contrib import admin


class AclAdmin(admin.ModelAdmin):
    search_fields = ('topic', )
    list_filter = ('acc', 'allow', )
    ordering = ('topic', )
    list_display = ('topic', 'allow', 'acc', 'user')


class TopicAdmin(admin.ModelAdmin):
    search_fields = ('name', )

admin.site.register(models.ACL, AclAdmin)
admin.site.register(models.Topic, TopicAdmin)
