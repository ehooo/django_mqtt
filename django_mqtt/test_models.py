
from django.test import TestCase

from django_mqtt.models import *
from django.core.exceptions import ValidationError


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
        self.assertEqual(unicode(Topic.objects.create(name='test/one')), u'test/one')
        self.assertEqual(Topic.objects.create(name='/test'), '/test')
        topic = Topic.objects.create(name='/test/one')
        self.assertEqual('/test/one' in topic, True)
        self.assertEqual('/test' in topic, False)
        self.assertEqual(topic < '/+/+', True)
        self.assertEqual(topic > '/+', False)

        self.assertRaises(ValidationError, Topic.objects.create, name='//')
        self.assertRaises(ValidationError, Topic.objects.create, name='/')
        self.assertRaises(ValidationError, Topic.objects.create, name='')

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
        topic = Topic.objects.get(name='/+/test')
        size = 0
        for t in topic:
            size += 1
        self.assertEqual(size, 3)
        topic = Topic.objects.get(name='/test/+')
        size = 0
        for t in topic:
            size += 1
        self.assertEqual(size, 2)
        topic = Topic.objects.get(name='/+')
        size = 0
        for t in topic:
            size += 1
        self.assertEqual(size, 3)
        topic = Topic.objects.get(name='#')
        size = 0
        for t in topic:
            size += 1
        self.assertEqual(size, 9)
        topic = Topic.objects.create(name='/#')
        size = 0
        for t in topic:
            size += 1
        self.assertEqual(size, 8)
        topic = Topic.objects.create(name='+')
        size = 0
        for t in topic:
            size += 1
        self.assertEqual(size, 1)
        topic = Topic.objects.create(name='/+/not/#')
        size = 0
        for t in topic:
            size += 1
        self.assertEqual(size, 1)
        Topic.objects.create(name='/test/1/not/2')
        Topic.objects.create(name='/test/1/not/2/3')
        Topic.objects.create(name='/test/1/not/2/3/4')
        topic = Topic.objects.create(name='/test/+/not/#')
        size = 0
        for t in topic:
            size += 1
        self.assertEqual(size, 3)
        topic = Topic.objects.create(name='/test/+/not/+/#')
        size = 0
        for t in topic:
            size += 1
        self.assertEqual(size, 2)


class ClientIdModelsTestCase(TestCase):
    WRONG_CLIENT_ID_WILDCARD = ['012345678901234567890123456789', '/', '+', '#']

    def test_client_id(self):
        if hasattr(settings, 'MQTT_ALLOW_EMPTY_CLIENT_ID') and settings.MQTT_ALLOW_EMPTY_CLIENT_ID:  # pragma: no cover
            ClientId.objects.create(name='')
        self.assertEqual(str(ClientId.objects.create(name='1234')), '1234')
        self.assertEqual(unicode(ClientId.objects.create(name='test')), u'test')
        ClientId.objects.create(name=gen_client_id())

    def test_wrong_client_id(self):
        if not hasattr(settings, 'MQTT_ALLOW_EMPTY_CLIENT_ID') or\
           not settings.MQTT_ALLOW_EMPTY_CLIENT_ID:  # pragma: no cover
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
        str(acl)
        unicode(acl)
        acl.groups.add(self.group)
        acl.users.add(self.user_login)
        ACL.objects.create(
            allow=True, topic=self.topic_public_subs,
            acc=PROTO_MQTT_ACC_SUS)
        ACL.objects.create(
            allow=False, topic=self.topic_forbidden_subs,
            acc=PROTO_MQTT_ACC_SUS)
        acl = ACL.objects.create(
            allow=True, topic=self.topic_private_subs,
            acc=PROTO_MQTT_ACC_SUS)
        acl.groups.add(self.group)
        acl.users.add(self.user_login)

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
        self.assertEqual(allow, True)
        allow = ACL.get_default(PROTO_MQTT_ACC_SUS, self.user_login)
        self.assertEqual(allow, True)
        acl.users.add(self.user_login)
        allow = ACL.get_default(PROTO_MQTT_ACC_SUS)
        self.assertEqual(allow, False)
        allow = ACL.get_default(PROTO_MQTT_ACC_SUS, self.user_login)
        self.assertEqual(allow, True)
        acl.password = '1234'
        acl.save()
        allow = ACL.get_default(PROTO_MQTT_ACC_SUS)
        self.assertEqual(allow, False)
        allow = ACL.get_default(PROTO_MQTT_ACC_SUS, self.user_login)
        self.assertEqual(allow, True)
        allow = ACL.get_default(PROTO_MQTT_ACC_SUS, password='1234')
        self.assertEqual(allow, True)




