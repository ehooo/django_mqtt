
from django.test import TestCase

from django_mqtt.models import *
from django.core.exceptions import ValidationError


class TopicModelsTestCase(TestCase):
    WRONG_TOPIC_SIMPLE_WILDCARD = ['a+', 'a+/', 'a/a+', 'a/+a']
    WRONG_TOPIC_MULTI_WILDCARD = ['#/', 'a#', 'a#/', 'a/#a', 'a/a#']

    def test_topic_simple_wildcard(self):
        topic = Topic.objects.create(name='+')
        self.assertEqual('' in topic, False)  # TODO FIXME??
        self.assertEqual('test' in topic, True)
        self.assertEqual('/test' in topic, False)
        self.assertEqual('/test/sd' in topic, False)
        topic = Topic.objects.create(name='/test/+/two')
        self.assertEqual('/test/a/two' in topic, True)
        self.assertEqual('/test/b/two' in topic, True)
        self.assertEqual('/test' in topic, False)
        self.assertEqual('/test/a/twos' in topic, False)
        self.assertEqual('/test/b/two/3' in topic, False)
        topic = Topic.objects.create(name='test/+/two')
        self.assertEqual('test/a/two' in topic, True)
        self.assertEqual('test/b/two' in topic, True)
        self.assertEqual('test' in topic, False)
        self.assertEqual('test/a/twos' in topic, False)
        self.assertEqual('test/b/two/3' in topic, False)

    def test_wrong_topic_simple_wildcard(self):
        for topic in self.WRONG_TOPIC_SIMPLE_WILDCARD:
            self.assertRaises(ValidationError, Topic.objects.create, name=topic)

    def test_topic_multi_wildcard(self):
        topic = Topic.objects.create(name='#')
        self.assertEqual('test/a/two' in topic, True)
        self.assertEqual('test/b/two' in topic, True)
        self.assertEqual('test' in topic, True)
        self.assertEqual('test/a/twos' in topic, True)
        self.assertEqual('test/b/two/3' in topic, True)
        self.assertEqual('/test/a/two' in topic, True)
        self.assertEqual('/test/b/two' in topic, True)
        self.assertEqual('/test' in topic, True)
        self.assertEqual('/test/a/twos' in topic, True)
        self.assertEqual('/test/b/two/3' in topic, True)
        topic = Topic.objects.create(name='/#')
        self.assertEqual('/test/a/two' in topic, True)
        self.assertEqual('/test/b/two' in topic, True)
        self.assertEqual('/test' in topic, True)
        self.assertEqual('/test/a/twos' in topic, True)
        self.assertEqual('/test/b/two/3' in topic, True)
        self.assertEqual('test' in topic, False)
        self.assertEqual('test/a/twos' in topic, False)
        self.assertEqual('test/b/two/3' in topic, False)

    def test_wrong_topic_multi_wildcard(self):
        for topic in self.WRONG_TOPIC_MULTI_WILDCARD:
            self.assertRaises(ValidationError, Topic.objects.create, name=topic)

    def test_topic_wildcard(self):
        Topic.objects.create(name='/test/+/two/#')
        Topic.objects.create(name='/+/#')
        Topic.objects.create(name='+/#')

    def test_wrong_topic_wildcard(self):
        self.assertRaises(ValidationError, Topic.objects.create, name='#+/')
        self.assertRaises(ValidationError, Topic.objects.create, name='+#/')

    def test_topic_dollar(self):
        plus = Topic.objects.create(name='$SYS/+')
        multi = Topic.objects.create(name='$SYS/#')
        self.assertEqual(plus in multi, True)
        self.assertEqual(multi in plus, False)
        self.assertRaises(ValidationError, Topic.objects.create, name='$+')
        self.assertRaises(ValidationError, Topic.objects.create, name='$#')
        topic = Topic.objects.create(name='$/+')
        self.assertEqual('+/+' in topic, False)
        self.assertEqual('+/#' in topic, False)
        self.assertEqual('$/test' in topic, True)
        self.assertEqual('$/test/one' in topic, False)
        topic = Topic.objects.create(name='$/#')
        self.assertEqual('+/+' in topic, False)
        self.assertEqual('+/#' in topic, False)
        self.assertEqual('$/test' in topic, True)
        self.assertEqual('$/test/one' in topic, True)
        topic = Topic.objects.get_or_create(name='+')
        dollar = Topic.objects.create(name='$')
        self.assertEqual(dollar in topic, False)
        self.assertRaises(ValidationError, Topic.objects.create, name='$/')

    def test_topic(self):
        Topic.objects.create(name='test')
        Topic.objects.create(name='test/one')
        Topic.objects.create(name='test/one/two')
        Topic.objects.create(name='/test')
        Topic.objects.create(name='/test/one')
        Topic.objects.create(name='/test/one/two')

        self.assertRaises(ValidationError, Topic.objects.create, name='//')
        self.assertRaises(ValidationError, Topic.objects.create, name='/')


class ClientIdModelsTestCase(TestCase):
    WRONG_CLIENT_ID_WILDCARD = ['012345678901234567890123456789', '/', '+', '#']

    def test_client_id(self):
        if hasattr(settings, 'MQTT_ALLOW_EMPTY_CLIENT_ID') and settings.MQTT_ALLOW_EMPTY_CLIENT_ID:  # pragma: no cover
            ClientId.objects.create(name='')
        ClientId.objects.create(name='1234')
        ClientId.objects.create(name='test')
        ClientId.objects.create(name='test123')
        ClientId.objects.create(name=gen_client_id())

    def test_wrong_client_id(self):
        if not hasattr(settings, 'MQTT_ALLOW_EMPTY_CLIENT_ID') or\
           not settings.MQTT_ALLOW_EMPTY_CLIENT_ID:  # pragma: no cover
            self.assertRaises(ValidationError, ClientId.objects.create, name='')
        for client_id in self.WRONG_CLIENT_ID_WILDCARD:
            self.assertRaises(ValidationError, ClientId.objects.create, name=client_id)


class ACLModelsTestCase(TestCase):
    def setUp(self):
        user_login = User.objects.create_user('test', 'test@test.com', 'test')
        user_group = User.objects.create_user('test_group', 'test_group@test.com', 'test_group')
        group = Group.objects.create(name='MQTT')
        user_group.groups.add(group)
        User.objects.create_superuser('admin', 'admin@test.com', 'admin')
        self.topic_public_publish, is_new = Topic.objects.get_or_create(name='/test/publisher/allow')
        self.topic_forbidden_publish, is_new = Topic.objects.get_or_create(name='/test/publisher/disallow')
        self.topic_private_publish, is_new = Topic.objects.get_or_create(name='/test/subscriber/login')
        self.topic_public_subs, is_new = Topic.objects.get_or_create(name='/test/subscriber/allow')
        self.topic_forbidden_subs, is_new = Topic.objects.get_or_create(name='/test/subscriber/disallow')
        self.topic_private_subs, is_new = Topic.objects.get_or_create(name='/test/subscriber/login')
        ACL.objects.create(
            allow=True, topic=self.topic_public_publish,
            acc=PROTO_MQTT_ACC_PUB)
        ACL.objects.create(
            allow=False, topic=self.topic_forbidden_publish,
            acc=PROTO_MQTT_ACC_PUB)
        acl = ACL.objects.create(allow=True, topic=self.topic_private_publish,
                                 acc=PROTO_MQTT_ACC_PUB)
        acl.groups.add(group)
        acl.users.add(user_login)
        ACL.objects.create(
            allow=True, topic=self.topic_public_subs,
            acc=PROTO_MQTT_ACC_SUS)
        ACL.objects.create(
            allow=False, topic=self.topic_forbidden_subs,
            acc=PROTO_MQTT_ACC_SUS)
        acl = ACL.objects.create(
            allow=True, topic=self.topic_private_subs,
            acc=PROTO_MQTT_ACC_SUS)
        acl.groups.add(group)
        acl.users.add(user_login)

    def test_wildcard_acl(self):
        pass



