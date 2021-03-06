import struct

from django.core.exceptions import ValidationError
from django.test import TestCase

from django_mqtt.protocol import (
    gen_string,
    get_remaining,
    get_string,
    int2remaining,
    remaining2list
)
from django_mqtt.validators import (
    ClientIdValidator,
    TopicValidator,
)


class ValidatorTestCase(TestCase):

    def test_client_id(self):
        validator = ClientIdValidator(valid_empty=None)
        self.assertRaises(ValidationError, validator, '')
        validator = ClientIdValidator(valid_empty=True)
        self.assertEqual(validator(''), None)
        validator = ClientIdValidator(valid_empty=False)
        self.assertRaises(ValidationError, validator, '')

    def test_topic(self):
        validator = TopicValidator(only_wildcards=None, not_wildcards=None)
        self.assertRaises(ValidationError, validator, '')
        validator = TopicValidator(only_wildcards=True, not_wildcards=True)
        self.assertRaises(ValidationError, validator, '/valid/topic')
        self.assertRaises(ValidationError, validator, '/valid/topic')
        validator = TopicValidator(only_wildcards=True, not_wildcards=False)
        self.assertRaises(ValidationError, validator, '/valid/topic')
        validator = TopicValidator(only_wildcards=False, not_wildcards=True)
        self.assertRaises(ValidationError, validator, '/+/topic')


class ProtocolTestCase(TestCase):

    def test_wrong_remaining2list(self):
        self.assertEqual(len(remaining2list(None)), 0)
        self.assertEqual(len(remaining2list(-1)), 0)
        self.assertRaises(TypeError, remaining2list, object)
        self.assertRaises(TypeError, remaining2list, None, exception=True)
        self.assertRaises(TypeError, remaining2list, object, exception=True)
        self.assertRaises(ValueError, remaining2list, -1, exception=True)

    def test_remaining2list_size(self):
        self.assertEqual(len(remaining2list(-1)), 0)
        self.assertEqual(len(remaining2list(0)), 1)
        self.assertEqual(len(remaining2list(127)), 1)
        self.assertEqual(len(remaining2list(128)), 2)
        self.assertEqual(len(remaining2list(16383)), 2)
        self.assertEqual(len(remaining2list(16384)), 3)
        self.assertEqual(len(remaining2list(2097151)), 3)
        self.assertEqual(len(remaining2list(2097152)), 4)
        self.assertEqual(len(remaining2list(268435455)), 4)

    def test_wrong_int2remaining(self):
        self.assertEqual(int2remaining(None), b'')
        self.assertEqual(int2remaining(-1), b'')
        self.assertRaises(TypeError, int2remaining, object)
        self.assertRaises(TypeError, int2remaining, None, exception=True)
        self.assertRaises(TypeError, int2remaining, object, exception=True)
        self.assertRaises(ValueError, int2remaining, -1, exception=True)

    def test_int2remaining(self):
        self.assertEqual(int2remaining(-1), b'')
        self.assertEqual(int2remaining(0), b'\x00')
        self.assertEqual(int2remaining(127), b'\x7f')
        self.assertEqual(int2remaining(128), b'\x80\x01')
        self.assertEqual(int2remaining(16383), b'\xff\x7f')
        self.assertEqual(int2remaining(16384), b'\x80\x80\x01')
        self.assertEqual(int2remaining(2097151), b'\xff\xff\x7f')
        self.assertEqual(int2remaining(2097152), b'\x80\x80\x80\x01')
        self.assertEqual(int2remaining(268435455), b'\xff\xff\xff\x7f')

    def test_wrong_get_remaining(self):
        self.assertEqual(get_remaining(None), None)
        self.assertRaises(TypeError, get_remaining, object)
        self.assertEqual(get_remaining(b'\x80\x80'), -1)
        self.assertEqual(get_remaining(b'\x00\x80'), -1)
        self.assertEqual(get_remaining(b'\x80\x01\x00\x00'), -1)
        self.assertRaises(TypeError, get_remaining, None, exception=True)
        self.assertRaises(TypeError, get_remaining, object, exception=True)
        self.assertRaises(struct.error, get_remaining, b'\x80\x80', exception=True)
        self.assertRaises(struct.error, get_remaining, b'\x00\x80', exception=True)
        self.assertRaises(struct.error, get_remaining, b'\x00\x01\x00\x00', exception=True)
        self.assertRaises(struct.error, get_remaining, b'\x80\x01\x00', exception=True)

    def test_get_remaining(self):
        self.assertEqual(get_remaining(b'\x00', exception=False), 0)
        self.assertEqual(get_remaining(b'\x7f', exception=False), 127)
        self.assertEqual(get_remaining(b'\x80\x01', exception=False), 128)
        self.assertEqual(get_remaining(b'\xff\x7f', exception=False), 16383)
        self.assertEqual(get_remaining(b'\x80\x80\x01', exception=False), 16384)
        self.assertEqual(get_remaining(b'\xff\xff\x7f', exception=False), 2097151)
        self.assertEqual(get_remaining(b'\x80\x80\x80\x01', exception=False), 2097152)
        self.assertEqual(get_remaining(b'\xff\xff\xff\x7f', exception=False), 268435455)

    def test_wrong_gen_string(self):
        self.assertEqual(gen_string(None), b'')
        self.assertEqual(gen_string(object), b'')
        self.assertEqual(gen_string('\x00\x02\x00\x00'), b'\x00\x02\x00\x02')
        self.assertRaises(TypeError, gen_string, None, exception=True)
        self.assertRaises(TypeError, gen_string, object, exception=True)
        self.assertRaises(ValueError, gen_string, '\x00\x02\x00\x00', exception=True)

    def test_empty_strings(self):
        self.assertEqual(gen_string(''), b'\x00\x00')
        self.assertEqual(gen_string(u''), b'\x00\x00')

    def test_gen_rfc3629_strings(self):
        self.assertEqual(gen_string('MQTT'), b'\x00\x04MQTT')
        self.assertEqual(gen_string(u'MQTT'), b'\x00\x04MQTT')

    def test_gen_rfc3629_alfa_strings(self):
        self.assertEqual(gen_string(u'\u0041\u2262\u0391\u002E'), b'\x00\x07\x41\xE2\x89\xA2\xCE\x91\x2E')

    def test_gen_rfc3629_korean_strings(self):
        self.assertEqual(gen_string(u'\uD55C\uAD6D\uC5B4'), b'\x00\x09\xED\x95\x9C\xEA\xB5\xAD\xEC\x96\xB4')

    def test_gen_rfc3629_japanese_strings(self):
        self.assertEqual(gen_string(u'\u65E5\u672C\u8A9E'), b'\x00\x09\xE6\x97\xA5\xE6\x9C\xAC\xE8\xAA\x9E')

    def test_get_rfc3629(self):
        self.assertEqual(get_string(b'\x00\x04MQTT'), u'MQTT')
        self.assertEqual(get_string(b'\x00\x07\x41\xE2\x89\xA2\xCE\x91\x2E'), u'\u0041\u2262\u0391\u002E')
        self.assertEqual(get_string(b'\x00\x09\xED\x95\x9C\xEA\xB5\xAD\xEC\x96\xB4'), u'\uD55C\uAD6D\uC5B4')
        self.assertEqual(get_string(b'\x00\x09\xE6\x97\xA5\xE6\x9C\xAC\xE8\xAA\x9E'), u'\u65E5\u672C\u8A9E')

    def test_wrong_get_string(self):
        self.assertEqual(get_string(None), '')
        self.assertEqual(get_string(b'\xff'), '')
        self.assertEqual(get_string(b'\xff\xff'), '')

        self.assertEqual(get_string(b'\xff\xff\x00'), '')
        self.assertEqual(get_string(b'\x00\x02\x00\x00'), '')
        self.assertEqual(get_string(b'\x00\x01\xC0'), '')
        self.assertEqual(get_string(b'\x00\x01\xC1'), '')
        self.assertEqual(get_string(b'\x00\x01\xF5'), '')
        self.assertEqual(get_string(b'\x00\x01\xFF'), '')
        self.assertEqual(get_string(b'\x00\x01\x00'), '\x00')

        self.assertRaises(TypeError, get_string, object)
        self.assertRaises(TypeError, get_string, b'\xff', exception=True)
        self.assertRaises(struct.error, get_string, b'\xff\xff', exception=True)
        self.assertRaises(struct.error, get_string, b'\xff\xff\x00', exception=True)
        self.assertRaises(ValueError, get_string, b'\x00\x02\x00\x00', exception=True)
        self.assertRaises(UnicodeDecodeError, get_string, b'\x00\x01\xC0', exception=True)
        self.assertRaises(UnicodeDecodeError, get_string, b'\x00\x01\xC1', exception=True)
        self.assertRaises(UnicodeDecodeError, get_string, b'\x00\x01\xF5', exception=True)
        self.assertRaises(UnicodeDecodeError, get_string, b'\x00\x01\xFF', exception=True)
        self.assertRaises(TypeError, get_string, None, exception=True)
        self.assertRaises(TypeError, get_string, object, exception=True)
