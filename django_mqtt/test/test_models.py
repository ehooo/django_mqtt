from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django_mqtt.models import (
    ACL,
    PROTO_MQTT_ACC_PUB,
    PROTO_MQTT_ACC_SUS,
    WILDCARD_MULTI_LEVEL,
    ClientId,
    Topic
)
from django_mqtt.protocol import gen_client_id


class TopicModelsTestCase(TestCase):
    WRONG_TOPIC_SIMPLE_WILDCARD = ['a+', 'a+/', 'a/a+', 'a/+a']
    WRONG_TOPIC_MULTI_WILDCARD = ['#/', 'a#', 'a#/', 'a/#a', 'a/a#']

    def test_topic_simple_wildcard(self):
        topic_plus = Topic.objects.create(name='+')
        self.assertEqual('' in topic_plus, False)
        self.assertEqual('test' in topic_plus, True)
        self.assertEqual('/test' in topic_plus, False)
        self.assertEqual('/test/sd' in topic_plus, False)
        topic1 = Topic.objects.create(name='/+/two')
        self.assertEqual('/test/two' in topic1, True)
        self.assertEqual('/1/two' in topic1, True)
        self.assertEqual('/test' in topic1, False)
        self.assertEqual('/test/twos' in topic1, False)
        self.assertEqual('/test/two/3' in topic1, False)
        self.assertEqual('$test/two' in topic1, False)
        self.assertEqual('/test/two' in topic1, True)
        self.assertEqual('+' < topic1, False)
        self.assertEqual('#' > topic1, True)
        self.assertEqual('+/+' > topic1, False)
        self.assertEqual('/+/+' > topic1, True)
        topic2 = Topic.objects.create(name='+/two')
        self.assertEqual('test/two' in topic2, True)
        self.assertEqual('1/two' in topic2, True)
        self.assertEqual('test' in topic2, False)
        self.assertEqual('test/twos' in topic2, False)
        self.assertEqual('test/two/3' in topic2, False)
        self.assertEqual('$test/two' in topic2, False)
        self.assertEqual('/test/two' in topic2, False)
        self.assertEqual(topic1 == topic2, False)
        self.assertEqual(topic1 in topic2, False)
        self.assertEqual(topic1 < topic2, False)
        self.assertEqual(topic1 > topic2, False)
        self.assertEqual(topic1 in topic2, False)
        self.assertEqual(topic2 in topic1, False)
        self.assertEqual('+' < topic2, False)
        self.assertEqual('#' > topic2, True)
        self.assertEqual('+/+' > topic2, True)
        self.assertEqual('/+/+' > topic2, False)
        self.assertEqual('test' < topic2, False)
        self.assertEqual('test' > topic2, False)

    def test_wrong_topic_simple_wildcard(self):
        for topic in self.WRONG_TOPIC_SIMPLE_WILDCARD:
            self.assertRaises(ValidationError, Topic.objects.create, name=topic)

    def test_topic_multi_wildcard(self):
        multi = Topic.objects.create(name='#')
        self.assertEqual('test/a/two' in multi, True)
        self.assertEqual('test/b/two' in multi, True)
        self.assertEqual('test' in multi, True)
        self.assertEqual('test/a/twos' in multi, True)
        self.assertEqual('test/b/two/3' in multi, True)
        self.assertEqual('/test/a/two' in multi, True)
        self.assertEqual('/test/b/two' in multi, True)
        self.assertEqual('/test' in multi, True)
        self.assertEqual('/test/a/twos' in multi, True)
        self.assertEqual('/test/b/two/3' in multi, True)
        topic = Topic.objects.create(name='/#')
        self.assertEqual(topic == multi, False)
        self.assertEqual(topic in multi, True)
        self.assertEqual(topic < multi, True)
        self.assertEqual(multi in topic, False)
        self.assertEqual(multi > topic, True)
        self.assertEqual(multi < 0, False)
        self.assertEqual(topic > 0, False)
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
        topic = Topic.objects.create(name='$SYS/+')
        multi = Topic.objects.create(name='$SYS/#')
        self.assertEqual(topic == multi, False)
        self.assertEqual(topic in multi, True)
        self.assertEqual(topic < multi, True)
        self.assertEqual(multi in topic, False)
        self.assertEqual(multi > topic, True)
        self.assertEqual('$SYSTEM/test/one' in multi, False)
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
        self.assertEqual(str(Topic.objects.create(name='test')), 'test')
        self.assertEqual(Topic.objects.create(name='/test'), '/test')
        topic = Topic.objects.create(name='/test/one')
        self.assertEqual('/test/one' in topic, True)
        self.assertEqual('/test' in topic, False)
        self.assertEqual(topic < '/+/+', True)
        self.assertEqual(topic > '/+', False)

        self.assertRaises(ValidationError, Topic.objects.create, name='//')
        self.assertRaises(ValidationError, Topic.objects.create, name='/')
        self.assertRaises(ValidationError, Topic.objects.create, name='')

    def assertListEqual(self, list1, list2, msg=None):
        self.assertEqual(len(list1), len(list2))
        for item in list1:
            self.assertIn(item, list2)

    def test_iterator(self):
        topics = {
            '/+/test': ['/me/test', '/ok/test'],
            '/test/+': ['/test/test', '/test/me'],
            '/+': ['/test', '/alone', '/asdf'],
            '#': ['$SYS', '/test/not/match', 'match']
        }
        for wild in topics:
            Topic.objects.create(name=wild)
            for topic in topics[wild]:
                Topic.objects.create(name=topic)

        topics = list(Topic.objects.get(name='/test'))
        self.assertListEqual(topics, ['/test'])
        topics = list(Topic.objects.get(name='/+/test'))
        self.assertListEqual(topics, ['/me/test', '/ok/test', '/test/test'])
        topics = list(Topic.objects.get(name='/test/+'))
        self.assertListEqual(topics, ['/test/test', '/test/me'])
        topics = list(Topic.objects.get(name='/+'))
        self.assertListEqual(topics, ['/test', '/alone', '/asdf'])
        topics = list(Topic.objects.get(name='#'))
        self.assertListEqual(topics, [
            '/me/test', '/ok/test',
            '/test/test', '/test/me',
            '/test', '/alone', '/asdf',
            '/test/not/match', 'match'
        ])
        topics = list(Topic.objects.create(name='/#'))
        self.assertListEqual(topics, [
            '/me/test', '/ok/test',
            '/test/test', '/test/me',
            '/test', '/alone', '/asdf',
            '/test/not/match'
        ])
        topics = list(Topic.objects.create(name='+'))
        self.assertListEqual(topics, ['match'])

        topics = list(Topic.objects.create(name='/+/not/#'))
        self.assertListEqual(topics, ['/test/not/match'])
        Topic.objects.create(name='/test/1/not/2')
        Topic.objects.create(name='/test/1/not/2/3')
        Topic.objects.create(name='/test/1/not/2/3/4')
        topics = list(Topic.objects.create(name='/test/+/not/#'))
        self.assertListEqual(topics, [
            '/test/1/not/2', '/test/1/not/2/3', '/test/1/not/2/3/4',
        ])
        topics = list(Topic.objects.create(name='/test/+/not/+/#'))
        self.assertListEqual(topics, [
            '/test/1/not/2/3', '/test/1/not/2/3/4',
        ])

    def test_delete(self):
        topic = Topic.objects.create(name='topic')
        self.assertEqual(1, Topic.objects.count())
        topic.delete()
        self.assertEqual(0, Topic.objects.count())

    def test_delete_memory(self):
        topic = Topic(name='topic')
        self.assertEqual(0, Topic.objects.count())
        self.assertRaisesMessage(
            AssertionError,
            "Topic object can't be deleted because its id attribute is set to None.",
            topic.delete
        )


class ClientIdModelsTestCase(TestCase):
    WRONG_CLIENT_ID_WILDCARD = ['012345678901234567890123456789', '/', '+', '#']

    def test_client_id(self):
        if hasattr(settings, 'MQTT_ALLOW_EMPTY_CLIENT_ID') and settings.MQTT_ALLOW_EMPTY_CLIENT_ID:  # pragma: no cover
            ClientId.objects.create(name='')
        self.assertEqual(str(ClientId.objects.create(name='1234')), '1234')
        ClientId.objects.create(name=gen_client_id())

    def test_wrong_client_id(self):
        if not hasattr(settings, 'MQTT_ALLOW_EMPTY_CLIENT_ID') or \
                not settings.MQTT_ALLOW_EMPTY_CLIENT_ID:
            self.assertRaises(ValidationError, ClientId.objects.create, name='')
        for client_id in self.WRONG_CLIENT_ID_WILDCARD:
            self.assertRaises(ValidationError, ClientId.objects.create, name=client_id)

    def test_client_id_is_public(self):
        cli = ClientId.objects.create(name='test')
        self.assertEqual(cli.is_public(), True)
        user = User.objects.create_user('test')
        cli.users.add(user)
        self.assertEqual(cli.is_public(), False)
        cli.users.remove(user)
        self.assertEqual(cli.is_public(), True)
        group = Group.objects.create(name='test')
        cli.groups.add(group)
        self.assertEqual(cli.is_public(), False)

    def test_client_id_has_permission(self):
        cli = ClientId.objects.create(name='test')
        self.assertEqual(cli.has_permission(None), True)
        user = User.objects.create_user('test')
        cli.users.add(user)
        self.assertEqual(cli.has_permission(None), False)
        self.assertEqual(cli.has_permission(user), True)
        cli.users.remove(user)
        self.assertEqual(cli.has_permission(None), True)
        group = Group.objects.create(name='test')
        cli.groups.add(group)
        self.assertEqual(cli.has_permission(None), False)
        self.assertEqual(cli.has_permission(user), False)
        user.groups.add(group)
        self.assertEqual(cli.has_permission(user), True)


class ACLModelsTestCase(TestCase):
    def setUp(self):
        self.user_login = User.objects.create_user('test', 'test@test.com', 'test')
        self.user_group = User.objects.create_user('test_group', 'test_group@test.com', 'test_group')
        self.group = Group.objects.create(name='MQTT')
        self.user_group.groups.add(self.group)
        self.admin = User.objects.create_superuser('admin', 'admin@test.com', 'admin')

    def test_string(self):
        topic = Topic.objects.create(name='/test')
        acl = ACL.objects.create(topic=topic, acc=PROTO_MQTT_ACC_SUS, allow=True)
        self.assertEqual(str(acl), "ACL Suscriptor for /test")

    def test_get_acl_no_candidate(self):
        Topic.objects.create(name='/test')
        self.assertIsNone(ACL.get_acl('/test', PROTO_MQTT_ACC_SUS))
        self.assertIsNone(ACL.get_acl('/test', PROTO_MQTT_ACC_PUB))

    def test_get_acl(self):
        topic = Topic.objects.create(name=WILDCARD_MULTI_LEVEL)
        acl = ACL.objects.create(topic=topic, acc=PROTO_MQTT_ACC_SUS, allow=True)
        topic = Topic.objects.create(name='/+')
        acl_plus = ACL.objects.create(topic=topic, acc=PROTO_MQTT_ACC_SUS, allow=True)
        self.assertEqual(ACL.get_acl('/test', PROTO_MQTT_ACC_SUS), acl_plus)
        self.assertEqual(ACL.get_acl('/test/test', PROTO_MQTT_ACC_SUS), acl)
        self.assertRaises(ValueError, ACL.get_acl, object)
        self.assertEqual(acl > acl_plus, True)
        self.assertEqual(acl_plus < acl, True)

    def test_acl_get_default(self):
        for us, ano in [(False, False), (True, False), (True, True)]:
            settings.MQTT_ACL_ALLOW = us
            settings.MQTT_ACL_ALLOW_ANONIMOUS = ano
            allow = ACL.get_default(PROTO_MQTT_ACC_SUS)
            self.assertEqual(allow, ano)
            allow = ACL.get_default(PROTO_MQTT_ACC_SUS, self.user_login)
            self.assertEqual(allow, us)
        settings.MQTT_ACL_ALLOW = False
        settings.MQTT_ACL_ALLOW_ANONIMOUS = False
        topic = Topic.objects.create(name=WILDCARD_MULTI_LEVEL)
        allow = ACL.get_default(PROTO_MQTT_ACC_SUS)
        self.assertEqual(allow, False)

        acl = ACL.objects.create(topic=topic, acc=PROTO_MQTT_ACC_SUS, allow=True)
        allow = ACL.get_default(PROTO_MQTT_ACC_SUS)
        self.assertEqual(allow, False)
        allow = ACL.get_default(PROTO_MQTT_ACC_SUS, self.user_login)
        self.assertEqual(allow, True)
        acl.users.add(self.user_login)
        allow = ACL.get_default(PROTO_MQTT_ACC_SUS)
        self.assertEqual(allow, False)
        allow = ACL.get_default(PROTO_MQTT_ACC_SUS, self.user_login)
        self.assertEqual(allow, True)
        acl.set_password('1234')
        acl.save()
        allow = ACL.get_default(PROTO_MQTT_ACC_SUS)
        self.assertEqual(allow, False)
        allow = ACL.get_default(PROTO_MQTT_ACC_SUS, self.user_login)
        self.assertEqual(allow, True)
        allow = ACL.get_default(PROTO_MQTT_ACC_SUS, password='1234')
        self.assertEqual(allow, True)

    def test_acl_set_unusable_password(self):
        topic = Topic.objects.create(name='/test')
        acl = ACL.objects.create(topic=topic, acc=PROTO_MQTT_ACC_SUS, allow=True, password='1234')
        acl.set_unusable_password()
        self.assertFalse(acl.has_usable_password())

    def test_acl_unusable_password_set(self):
        topic = Topic.objects.create(name='/test')
        acl = ACL.objects.create(topic=topic, acc=PROTO_MQTT_ACC_SUS, allow=True)
        acl.set_password('1234')
        self.assertTrue(acl.has_usable_password())

    def test_acl_set_password_encrypt(self):
        topic = Topic.objects.create(name='/test')
        acl = ACL.objects.create(topic=topic, acc=PROTO_MQTT_ACC_SUS, allow=True)
        acl.set_password('1234')
        self.assertNotEqual(acl.password, '1234')
