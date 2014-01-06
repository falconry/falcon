from datetime import datetime
import testtools

import falcon
from falcon.util import uri


class TestFalconUtils(testtools.TestCase):

    def test_dt_to_http(self):
        self.assertEqual(
            falcon.dt_to_http(datetime(2013, 4, 4)),
            'Thu, 04 Apr 2013 00:00:00 GMT')

        self.assertEqual(
            falcon.dt_to_http(datetime(2013, 4, 4, 10, 28, 54)),
            'Thu, 04 Apr 2013 10:28:54 GMT')

    def test_http_date_to_dt(self):
        self.assertEqual(
            falcon.http_date_to_dt('Thu, 04 Apr 2013 00:00:00 GMT'),
            datetime(2013, 4, 4))

        self.assertEqual(
            falcon.http_date_to_dt('Thu, 04 Apr 2013 10:28:54 GMT'),
            datetime(2013, 4, 4, 10, 28, 54))

    def test_pack_query_params_none(self):
        self.assertEqual(
            falcon.to_query_str({}),
            '')

    def test_pack_query_params_one(self):
        self.assertEqual(
            falcon.to_query_str({'limit': 10}),
            '?limit=10')

        self.assertEqual(
            falcon.to_query_str({'things': [1, 2, 3]}),
            '?things=1,2,3')

        self.assertEqual(
            falcon.to_query_str({'things': ['a']}),
            '?things=a')

        self.assertEqual(
            falcon.to_query_str({'things': ['a', 'b']}),
            '?things=a,b')

    def test_pack_query_params_several(self):
        garbage_in = {
            'limit': 17,
            'echo': True,
            'doit': False,
            'x': 'val',
            'y': 0.2
        }

        query_str = falcon.to_query_str(garbage_in)
        fields = query_str[1:].split('&')

        garbage_out = {}
        for field in fields:
            k, v = field.split('=')
            garbage_out[k] = v

        expected = {
            'echo': 'true',
            'limit': '17',
            'x': 'val',
            'y': '0.2',
            'doit': 'false'}

        self.assertEqual(expected, garbage_out)

    def test_uri_encode(self):
        url = 'http://example.com/v1/fizbit/messages?limit=3&echo=true'
        self.assertEqual(uri.encode(url), url)

        url = 'http://example.com/v1/fiz bit/messages'
        expected = 'http://example.com/v1/fiz%20bit/messages'
        self.assertEqual(uri.encode(url), expected)

        url = u'http://example.com/v1/fizbit/messages?limit=3&e\u00e7ho=true'
        expected = ('http://example.com/v1/fizbit/messages'
                    '?limit=3&e%C3%A7ho=true')
        self.assertEqual(uri.encode(url), expected)

    def test_uri_encode_value(self):
        self.assertEqual(uri.encode_value('abcd'), 'abcd')
        self.assertEqual(uri.encode_value(u'abcd'), u'abcd')
        self.assertEqual(uri.encode_value(u'ab cd'), u'ab%20cd')
        self.assertEqual(uri.encode_value(u'\u00e7'), '%C3%A7')
        self.assertEqual(uri.encode_value('ab/cd'), 'ab%2Fcd')
        self.assertEqual(uri.encode_value('ab+cd=42,9'),
                         'ab%2Bcd%3D42%2C9')

    def test_uri_decode(self):
        self.assertEqual(uri.decode('abcd'), 'abcd')
        self.assertEqual(uri.decode(u'abcd'), u'abcd')
        self.assertEqual(uri.decode(u'ab%20cd'), u'ab cd')
        self.assertEqual(uri.decode('%C3%A7'), u'\u00e7')
        self.assertEqual(uri.decode('ab%2Fcd'), 'ab/cd')

        self.assertEqual(uri.decode('http://example.com?x=ab%2Bcd%3D42%2C9'),
                         'http://example.com?x=ab+cd=42,9')
