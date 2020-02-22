from django.contrib.admin import AdminSite
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from django_mqtt.admin import AclAdmin
from django_mqtt.models import (
    ACL,
    PROTO_MQTT_ACC_SUS,
    Topic
)


class ACLAdminTestCase(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser('admin', 'admin@test.com', 'admin')
        user_group = User.objects.create_user('test_group', 'test_group@test.com', 'test_group')
        group = Group.objects.create(name='MQTT')
        user_group.groups.add(group)
        topic = Topic.objects.create(name='/test')
        self.acl = ACL.objects.create(topic=topic, acc=PROTO_MQTT_ACC_SUS, allow=True)

    def test_get_password_no(self):
        model_admin = AclAdmin(model=ACL, admin_site=AdminSite())
        self.assertEqual(model_admin.get_password(self.acl), 'no')

    def test_get_password_yes(self):
        model_admin = AclAdmin(model=ACL, admin_site=AdminSite())
        self.acl.set_password('1234')
        self.assertEqual(model_admin.get_password(self.acl), 'yes')

    def test_get_change_password(self):
        url = reverse('admin:django_mqtt_acl_password_change', args=(self.acl.pk,))
        self.client.force_login(self.admin_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, 'admin/django_mqtt/acl/change_password.html')

    def test_change_password(self):
        plain_password = '1234'
        data = {
            'password1': plain_password,
            'password2': plain_password,
        }
        url = reverse('admin:django_mqtt_acl_password_change', args=(self.acl.pk,))
        self.assertFalse(self.acl.has_usable_password())
        self.client.force_login(self.admin_user)
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 302)

        acl = ACL.objects.get(pk=self.acl.pk)
        self.assertTrue(acl.has_usable_password())
        self.assertNotEqual(acl.password, plain_password)
        self.assertTrue(acl.check_password(plain_password))

    def test_wrong_change_password(self):
        data = {
            'password1': '1234',
            'password2': '4321',
        }
        url = reverse('admin:django_mqtt_acl_password_change', args=(self.acl.pk,))
        self.client.force_login(self.admin_user)
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 200)
        form = response.context_data.get('form')
        self.assertIn('password_mismatch', form.error_messages)

    def test_change_password_no_acl(self):
        url = reverse('admin:django_mqtt_acl_password_change', args=('test',))
        self.client.force_login(self.admin_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
