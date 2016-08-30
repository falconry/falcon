# -*- coding: utf-8 -*-

from datetime import datetime
import functools
import io
import json
import random
import sys

import six
import testtools

import falcon
from falcon import testing
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

    def test_http_now(self):
        expected = datetime.utcnow()
        actual = falcon.http_date_to_dt(falcon.http_now())

        delta = actual - expected
        delta_sec = abs(delta.days * 86400 + delta.seconds)

        self.assertLessEqual(delta_sec, 1)

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

        self.assertRaises(
            ValueError,
            falcon.http_date_to_dt, 'Thu, 04-Apr-2013 10:28:54 GMT')

        self.assertEqual(
            falcon.http_date_to_dt('Thu, 04-Apr-2013 10:28:54 GMT',
                                   obs_date=True),
            datetime(2013, 4, 4, 10, 28, 54))

        self.assertRaises(
            ValueError,
            falcon.http_date_to_dt, 'Sun Nov  6 08:49:37 1994')

        self.assertRaises(
            ValueError,
            falcon.http_date_to_dt, 'Nov  6 08:49:37 1994', obs_date=True)

        self.assertEqual(
            falcon.http_date_to_dt('Sun Nov  6 08:49:37 1994', obs_date=True),
            datetime(1994, 11, 6, 8, 49, 37))

        self.assertEqual(
            falcon.http_date_to_dt('Sunday, 06-Nov-94 08:49:37 GMT',
                                   obs_date=True),
            datetime(1994, 11, 6, 8, 49, 37))

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

        expected = ('?things=a&things=b&things=&things=None'
                    '&things=true&things=false&things=0')

        actual = falcon.to_query_str(
            {'things': ['a', 'b', '', None, True, False, 0]},
            comma_delimited_lists=False
        )

        self.assertEqual(actual, expected)

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

    def test_uri_encode_double(self):
        url = 'http://example.com/v1/fiz bit/messages'
        expected = 'http://example.com/v1/fiz%20bit/messages'
        self.assertEqual(uri.encode(uri.encode(url)), expected)

        url = u'http://example.com/v1/fizbit/messages?limit=3&e\u00e7ho=true'
        expected = ('http://example.com/v1/fizbit/messages'
                    '?limit=3&e%C3%A7ho=true')
        self.assertEqual(uri.encode(uri.encode(url)), expected)

        url = 'http://example.com/v1/fiz%bit/mess%ages/%'
        expected = 'http://example.com/v1/fiz%25bit/mess%25ages/%25'
        self.assertEqual(uri.encode(uri.encode(url)), expected)

        url = 'http://example.com/%%'
        expected = 'http://example.com/%25%25'
        self.assertEqual(uri.encode(uri.encode(url)), expected)

        # NOTE(kgriffs): Specific example cited in GH issue
        url = 'http://something?redirect_uri=http%3A%2F%2Fsite'
        self.assertEqual(uri.encode(url), url)

        hex_digits = 'abcdefABCDEF0123456789'
        for c1 in hex_digits:
            for c2 in hex_digits:
                url = 'http://example.com/%' + c1 + c2
                encoded = uri.encode(uri.encode(url))
                self.assertEqual(encoded, url)

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
            six.moves.urllib.parse.quote, safe='~'
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

    def test_parse_query_string(self):
        query_strinq = (
            'a=http%3A%2F%2Ffalconframework.org%3Ftest%3D1'
            '&b=%7B%22test1%22%3A%20%22data1%22%'
            '2C%20%22test2%22%3A%20%22data2%22%7D'
            '&c=1,2,3'
            '&d=test'
            '&e=a,,%26%3D%2C'
            '&f=a&f=a%3Db'
            '&%C3%A9=a%3Db'
        )
        decoded_url = 'http://falconframework.org?test=1'
        decoded_json = '{"test1": "data1", "test2": "data2"}'

        result = uri.parse_query_string(query_strinq)
        self.assertEqual(result['a'], decoded_url)
        self.assertEqual(result['b'], decoded_json)
        self.assertEqual(result['c'], ['1', '2', '3'])
        self.assertEqual(result['d'], 'test')
        self.assertEqual(result['e'], ['a', '&=,'])
        self.assertEqual(result['f'], ['a', 'a=b'])
        self.assertEqual(result[u'é'], 'a=b')

        result = uri.parse_query_string(query_strinq, True)
        self.assertEqual(result['a'], decoded_url)
        self.assertEqual(result['b'], decoded_json)
        self.assertEqual(result['c'], ['1', '2', '3'])
        self.assertEqual(result['d'], 'test')
        self.assertEqual(result['e'], ['a', '', '&=,'])
        self.assertEqual(result['f'], ['a', 'a=b'])
        self.assertEqual(result[u'é'], 'a=b')

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

    def test_get_http_status(self):
        self.assertEqual(falcon.get_http_status(404), falcon.HTTP_404)
        self.assertEqual(falcon.get_http_status(404.3), falcon.HTTP_404)
        self.assertEqual(falcon.get_http_status('404.3'), falcon.HTTP_404)
        self.assertEqual(falcon.get_http_status(404.9), falcon.HTTP_404)
        self.assertEqual(falcon.get_http_status('404'), falcon.HTTP_404)
        self.assertEqual(falcon.get_http_status(123), '123 Unknown')
        self.assertRaises(ValueError, falcon.get_http_status, 'not_a_number')
        self.assertRaises(ValueError, falcon.get_http_status, 0)
        self.assertRaises(ValueError, falcon.get_http_status, 99)
        self.assertRaises(ValueError, falcon.get_http_status, -404.3)
        self.assertRaises(ValueError, falcon.get_http_status, '-404')
        self.assertRaises(ValueError, falcon.get_http_status, '-404.3')
        self.assertEqual(falcon.get_http_status(123, 'Go Away'), '123 Go Away')


class TestFalconTesting(testing.TestBase):
    """Catch some uncommon branches not covered elsewhere."""

    def test_path_escape_chars_in_create_environ(self):
        env = testing.create_environ('/hello%20world%21')
        self.assertEqual(env['PATH_INFO'], '/hello world!')

    def test_no_prefix_allowed_for_query_strings_in_create_environ(self):
        self.assertRaises(ValueError, testing.create_environ,
                          query_string='?foo=bar')

    def test_unicode_path_in_create_environ(self):
        if six.PY3:
            self.skip('Test does not apply to Py3K')

        env = testing.create_environ(u'/fancy/unícode')
        self.assertEqual(env['PATH_INFO'], '/fancy/un\xc3\xadcode')

        env = testing.create_environ(u'/simple')
        self.assertEqual(env['PATH_INFO'], '/simple')

    def test_none_header_value_in_create_environ(self):
        env = testing.create_environ('/', headers={'X-Foo': None})
        self.assertEqual(env['HTTP_X_FOO'], '')

    def test_decode_empty_result(self):
        body = self.simulate_request('/', decode='utf-8')
        self.assertEqual(body, '')

    def test_httpnow_alias_for_backwards_compat(self):
        self.assertIs(testing.httpnow, util.http_now)


class TestFalconTestCase(testing.TestCase):
    """Verify some branches not covered elsewhere."""

    def test_status(self):
        resource = testing.SimpleTestResource(status=falcon.HTTP_702)
        self.api.add_route('/', resource)

        result = self.simulate_get()
        self.assertEqual(result.status, falcon.HTTP_702)

    def test_wsgi_iterable_not_closeable(self):
        result = testing.Result([], falcon.HTTP_200, [])
        self.assertFalse(result.content)

    def test_path_must_start_with_slash(self):
        self.assertRaises(ValueError, self.simulate_get, 'foo')

    def test_cached_text_in_result(self):
        self.api.add_route('/', testing.SimpleTestResource(body='test'))

        result = self.simulate_get()
        self.assertEqual(result.text, result.text)

    def test_simple_resource_body_json_xor(self):
        self.assertRaises(
            ValueError,
            testing.SimpleTestResource,
            body='',
            json={},
        )

    def test_query_string(self):
        class SomeResource(object):
            def on_get(self, req, resp):
                doc = {}

                doc['oid'] = req.get_param_as_int('oid')
                doc['detailed'] = req.get_param_as_bool('detailed')
                doc['things'] = req.get_param_as_list('things', int)
                doc['query_string'] = req.query_string

                resp.body = json.dumps(doc)

        self.api.add_route('/', SomeResource())

        result = self.simulate_get(query_string='oid=42&detailed=no&things=1')
        self.assertEqual(result.json['oid'], 42)
        self.assertFalse(result.json['detailed'])
        self.assertEqual(result.json['things'], [1])

        params = {'oid': 42, 'detailed': False}
        result = self.simulate_get(params=params)
        self.assertEqual(result.json['oid'], params['oid'])
        self.assertFalse(result.json['detailed'])
        self.assertEqual(result.json['things'], None)

        params = {'oid': 1978, 'detailed': 'yes', 'things': [1, 2, 3]}
        result = self.simulate_get(params=params)
        self.assertEqual(result.json['oid'], params['oid'])
        self.assertTrue(result.json['detailed'])
        self.assertEqual(result.json['things'], params['things'])

        expected_qs = 'things=1,2,3'
        result = self.simulate_get(params={'things': [1, 2, 3]})
        self.assertEqual(result.json['query_string'], expected_qs)

        expected_qs = 'things=1&things=2&things=3'
        result = self.simulate_get(params={'things': [1, 2, 3]},
                                   params_csv=False)
        self.assertEqual(result.json['query_string'], expected_qs)

    def test_query_string_no_question(self):
        self.assertRaises(ValueError, self.simulate_get, query_string='?x=1')

    def test_query_string_in_path(self):
        self.assertRaises(ValueError, self.simulate_get, path='/thing?x=1')


class FancyAPI(falcon.API):
    pass


class FancyTestCase(testing.TestCase):
    api_class = FancyAPI

    def test_something(self):
        self.assertTrue(isinstance(self.api, FancyAPI))
