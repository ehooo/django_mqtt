
from django.test import TestCase

from django_mqtt.models import *


class ModelsTestCase(TestCase):

    def test_wrong_remaining2list(self):
        multi = Topic.objects.get_or_create(name='#')
        single = Topic.objects.get_or_create(name='+')
        dollar = Topic.objects.get_or_create(name='$')
        dollar = Topic.objects.get_or_create(name='$SYS/+')
        dollar = Topic.objects.get_or_create(name='$SYS/#')
        test = Topic.objects.get_or_create(name='test')
        test_ = Topic.objects.get_or_create(name='test/one')
        test__ = Topic.objects.get_or_create(name='test/one/two')
        test_s = Topic.objects.get_or_create(name='test/+/two')



