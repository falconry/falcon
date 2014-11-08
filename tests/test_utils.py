# -*- coding: utf-8-*-

from datetime import datetime
import functools
import io
import random
import sys

import testtools
import six

import falcon
import falcon.testing
from falcon import util
from falcon.util import uri


def _arbitrary_uris(count, length):
    return (
        u''.join(
            [random.choice(uri._ALL_ALLOWED)
             for _ in range(length)]
        ) for __ in range(count)
    )


class TestFalconUtils(testtools.TestCase):

    def setUp(self):
        super(TestFalconUtils, self).setUp()
        # NOTE(cabrera): for DRYness - used in uri.[de|en]code tests
        # below.
        self.uris = _arbitrary_uris(count=100, length=32)

    def test_deprecated_decorator(self):
        msg = 'Please stop using this thing. It is going away.'

        @util.deprecated(msg)
        def old_thing():
            pass

        if six.PY3:
            stream = io.StringIO()
        else:
            stream = io.BytesIO()

        old_stderr = sys.stderr
        sys.stderr = stream

        old_thing()

        sys.stderr = old_stderr
        self.assertIn(msg, stream.getvalue())

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
        self.assertEqual(uri.encode_value(u'\u00e7\u20ac'),
                         '%C3%A7%E2%82%AC')
        self.assertEqual(uri.encode_value('ab/cd'), 'ab%2Fcd')
        self.assertEqual(uri.encode_value('ab+cd=42,9'),
                         'ab%2Bcd%3D42%2C9')

    def test_uri_decode(self):
        self.assertEqual(uri.decode('abcd'), 'abcd')
        self.assertEqual(uri.decode(u'abcd'), u'abcd')
        self.assertEqual(uri.decode(u'ab%20cd'), u'ab cd')

        self.assertEqual(uri.decode('This thing is %C3%A7'),
                         u'This thing is \u00e7')

        self.assertEqual(uri.decode('This thing is %C3%A7%E2%82%AC'),
                         u'This thing is \u00e7\u20ac')

        self.assertEqual(uri.decode('ab%2Fcd'), 'ab/cd')

        self.assertEqual(uri.decode('http://example.com?x=ab%2Bcd%3D42%2C9'),
                         'http://example.com?x=ab+cd=42,9')

    def test_prop_uri_encode_models_stdlib_quote(self):
        equiv_quote = functools.partial(
            six.moves.urllib.parse.quote, safe=uri._ALL_ALLOWED
        )
        for case in self.uris:
            expect = equiv_quote(case)
            actual = uri.encode(case)
            self.assertEqual(expect, actual)

    def test_prop_uri_encode_value_models_stdlib_quote_safe_tilde(self):
        equiv_quote = functools.partial(
            six.moves.urllib.parse.quote, safe="~"
        )
        for case in self.uris:
            expect = equiv_quote(case)
            actual = uri.encode_value(case)
            self.assertEqual(expect, actual)

    def test_prop_uri_decode_models_stdlib_unquote_plus(self):
        stdlib_unquote = six.moves.urllib.parse.unquote_plus
        for case in self.uris:
            case = uri.encode_value(case)

            expect = stdlib_unquote(case)
            actual = uri.decode(case)
            self.assertEqual(expect, actual)

    def test_parse_host(self):
        self.assertEqual(uri.parse_host('::1'), ('::1', None))
        self.assertEqual(uri.parse_host('2001:ODB8:AC10:FE01::'),
                         ('2001:ODB8:AC10:FE01::', None))
        self.assertEqual(
            uri.parse_host('2001:ODB8:AC10:FE01::', default_port=80),
            ('2001:ODB8:AC10:FE01::', 80))

        ipv6_addr = '2001:4801:1221:101:1c10::f5:116'

        self.assertEqual(uri.parse_host(ipv6_addr), (ipv6_addr, None))
        self.assertEqual(uri.parse_host('[' + ipv6_addr + ']'),
                         (ipv6_addr, None))
        self.assertEqual(uri.parse_host('[' + ipv6_addr + ']:28080'),
                         (ipv6_addr, 28080))
        self.assertEqual(uri.parse_host('[' + ipv6_addr + ']:8080'),
                         (ipv6_addr, 8080))
        self.assertEqual(uri.parse_host('[' + ipv6_addr + ']:123'),
                         (ipv6_addr, 123))
        self.assertEqual(uri.parse_host('[' + ipv6_addr + ']:42'),
                         (ipv6_addr, 42))

        self.assertEqual(uri.parse_host('173.203.44.122'),
                         ('173.203.44.122', None))
        self.assertEqual(uri.parse_host('173.203.44.122', default_port=80),
                         ('173.203.44.122', 80))
        self.assertEqual(uri.parse_host('173.203.44.122:27070'),
                         ('173.203.44.122', 27070))
        self.assertEqual(uri.parse_host('173.203.44.122:123'),
                         ('173.203.44.122', 123))
        self.assertEqual(uri.parse_host('173.203.44.122:42'),
                         ('173.203.44.122', 42))

        self.assertEqual(uri.parse_host('example.com'),
                         ('example.com', None))
        self.assertEqual(uri.parse_host('example.com', default_port=443),
                         ('example.com', 443))
        self.assertEqual(uri.parse_host('falcon.example.com'),
                         ('falcon.example.com', None))
        self.assertEqual(uri.parse_host('falcon.example.com:9876'),
                         ('falcon.example.com', 9876))
        self.assertEqual(uri.parse_host('falcon.example.com:42'),
                         ('falcon.example.com', 42))


class TestFalconTesting(falcon.testing.TestBase):
    """Catch some uncommon branches not covered elsewhere."""

    def test_path_escape_chars_in_create_environ(self):
        env = falcon.testing.create_environ('/hello%20world%21')
        self.assertEqual(env['PATH_INFO'], '/hello world!')

    def test_unicode_path_in_create_environ(self):
        if six.PY3:
            self.skip('Test does not apply to Py3K')

        env = falcon.testing.create_environ(u'/fancy/unícode')
        self.assertEqual(env['PATH_INFO'], '/fancy/un\xc3\xadcode')

        env = falcon.testing.create_environ(u'/simple')
        self.assertEqual(env['PATH_INFO'], '/simple')

    def test_none_header_value_in_create_environ(self):
        env = falcon.testing.create_environ('/', headers={'X-Foo': None})
        self.assertEqual(env['HTTP_X_FOO'], '')

    def test_decode_empty_result(self):
        body = self.simulate_request('/', decode='utf-8')
        self.assertEqual(body, '')
