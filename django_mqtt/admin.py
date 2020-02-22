from django.conf.urls import url
from django.contrib import admin, messages
from django.contrib.admin.options import IS_POPUP_VAR
from django.contrib.admin.utils import unquote
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.encoding import force_text
from django.utils.html import escape
from django.utils.translation import ugettext, ugettext_lazy as _
from django.views.decorators.debug import sensitive_post_parameters

from django_mqtt import models
from django_mqtt.forms import ACLChangeForm, AdminPasswordChangeForm

sensitive_post_parameters_m = method_decorator(sensitive_post_parameters())


class AclAdmin(admin.ModelAdmin):
    search_fields = ('topic__name', )
    list_filter = ('acc', 'allow', )
    ordering = ('topic', )
    list_display = ('topic', 'allow', 'acc', 'get_password')

    change_password_form = AdminPasswordChangeForm
    form = ACLChangeForm

    def get_password(self, obj):
        return _('yes') if obj.password else _('no')

    get_password.short_description = 'password'

    def get_urls(self):
        return [
           url(
                r'^(.+)/password/$',
                self.admin_site.admin_view(self.user_change_password),
                name='django_mqtt_acl_password_change',
            ),
        ] + super(AclAdmin, self).get_urls()

    @sensitive_post_parameters_m
    def user_change_password(self, request, object_id, form_url=''):
        if not self.has_change_permission(request):
            raise PermissionDenied
        acl = self.get_object(request, unquote(object_id))
        if acl is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') % {
                'name': force_text(self.model._meta.verbose_name),
                'key': escape(object_id),
            })
        if request.method == 'POST':
            form = self.change_password_form(acl, request.POST)
            if form.is_valid():
                form.save()
                change_message = self.construct_change_message(request, form, None)
                self.log_change(request, acl, change_message)
                msg = ugettext('Password changed successfully.')
                messages.success(request, msg)
                return HttpResponseRedirect(
                    reverse(
                        '%s:%s_%s_change' % (
                            self.admin_site.name,
                            acl._meta.app_label,
                            acl._meta.model_name,
                        ),
                        args=(acl.pk,),
                    )
                )
        else:
            form = self.change_password_form(acl)

        fieldsets = [(None, {'fields': list(form.base_fields)})]
        adminForm = admin.helpers.AdminForm(form, fieldsets, {})

        context = {
            'title': _('Change password: %s') % escape(acl),
            'adminForm': adminForm,
            'form_url': form_url,
            'form': form,
            'is_popup': (IS_POPUP_VAR in request.POST or
                         IS_POPUP_VAR in request.GET),
            'add': True,
            'change': False,
            'has_delete_permission': False,
            'has_change_permission': True,
            'has_absolute_url': False,
            'opts': self.model._meta,
            'original': acl,
            'save_as': False,
            'show_save': True,
        }
        context.update(self.admin_site.each_context(request))

        request.current_app = self.admin_site.name

        return TemplateResponse(
            request,
            'admin/django_mqtt/acl/change_password.html',
            context,
        )


class TopicAdmin(admin.ModelAdmin):
    search_fields = ('name', )
    list_filter = ('dollar', 'wildcard', )
    list_display = ('name', 'dollar', 'wildcard')


class ClientIdAdmin(admin.ModelAdmin):
    search_fields = ('name', )


admin.site.register(models.ACL, AclAdmin)
admin.site.register(models.Topic, TopicAdmin)
admin.site.register(models.ClientId, ClientIdAdmin)
