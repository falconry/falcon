# -*- coding: utf-8 -*-

from datetime import datetime
import functools
import random

import pytest

import falcon
from falcon import testing
from falcon import util
from falcon.util import compat, json, misc, structures, uri


def _arbitrary_uris(count, length):
    return (
        u''.join(
            [random.choice(uri._ALL_ALLOWED)
             for _ in range(length)]
        ) for __ in range(count)
    )


class TestFalconUtils(object):

    def setup_method(self, method):
        # NOTE(cabrera): for DRYness - used in uri.[de|en]code tests
        # below.
        self.uris = _arbitrary_uris(count=100, length=32)

    def test_deprecated_decorator(self):
        msg = 'Please stop using this thing. It is going away.'

        @util.deprecated(msg)
        def old_thing():
            pass

        with pytest.warns(UserWarning) as rec:
            old_thing()

        warn = rec.pop()
        assert msg in str(warn.message)

    def test_http_now(self):
        expected = datetime.utcnow()
        actual = falcon.http_date_to_dt(falcon.http_now())

        delta = actual - expected
        delta_sec = abs(delta.days * 86400 + delta.seconds)

        assert delta_sec <= 1

    def test_dt_to_http(self):
        assert falcon.dt_to_http(datetime(2013, 4, 4)) == 'Thu, 04 Apr 2013 00:00:00 GMT'

        assert falcon.dt_to_http(
            datetime(2013, 4, 4, 10, 28, 54)
        ) == 'Thu, 04 Apr 2013 10:28:54 GMT'

    def test_http_date_to_dt(self):
        assert falcon.http_date_to_dt('Thu, 04 Apr 2013 00:00:00 GMT') == datetime(2013, 4, 4)

        assert falcon.http_date_to_dt(
            'Thu, 04 Apr 2013 10:28:54 GMT'
        ) == datetime(2013, 4, 4, 10, 28, 54)

        with pytest.raises(ValueError):
            falcon.http_date_to_dt('Thu, 04-Apr-2013 10:28:54 GMT')

        assert falcon.http_date_to_dt(
            'Thu, 04-Apr-2013 10:28:54 GMT', obs_date=True
        ) == datetime(2013, 4, 4, 10, 28, 54)

        with pytest.raises(ValueError):
            falcon.http_date_to_dt('Sun Nov  6 08:49:37 1994')

        with pytest.raises(ValueError):
            falcon.http_date_to_dt('Nov  6 08:49:37 1994', obs_date=True)

        assert falcon.http_date_to_dt(
            'Sun Nov  6 08:49:37 1994', obs_date=True
        ) == datetime(1994, 11, 6, 8, 49, 37)

        assert falcon.http_date_to_dt(
            'Sunday, 06-Nov-94 08:49:37 GMT', obs_date=True
        ) == datetime(1994, 11, 6, 8, 49, 37)

    def test_pack_query_params_none(self):
        assert falcon.to_query_str({}) == ''

    def test_pack_query_params_one(self):
        assert falcon.to_query_str({'limit': 10}) == '?limit=10'

        assert falcon.to_query_str(
            {'things': [1, 2, 3]}) == '?things=1,2,3'

        assert falcon.to_query_str({'things': ['a']}) == '?things=a'

        assert falcon.to_query_str(
            {'things': ['a', 'b']}) == '?things=a,b'

        expected = ('?things=a&things=b&things=&things=None'
                    '&things=true&things=false&things=0')

        actual = falcon.to_query_str(
            {'things': ['a', 'b', '', None, True, False, 0]},
            comma_delimited_lists=False
        )

        assert actual == expected

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

        assert expected == garbage_out

    def test_uri_encode(self):
        url = 'http://example.com/v1/fizbit/messages?limit=3&echo=true'
        assert uri.encode(url) == url

        url = 'http://example.com/v1/fiz bit/messages'
        expected = 'http://example.com/v1/fiz%20bit/messages'
        assert uri.encode(url) == expected

        url = u'http://example.com/v1/fizbit/messages?limit=3&e\u00e7ho=true'
        expected = ('http://example.com/v1/fizbit/messages'
                    '?limit=3&e%C3%A7ho=true')
        assert uri.encode(url) == expected

    def test_uri_encode_double(self):
        url = 'http://example.com/v1/fiz bit/messages'
        expected = 'http://example.com/v1/fiz%20bit/messages'
        assert uri.encode(uri.encode(url)) == expected

        url = u'http://example.com/v1/fizbit/messages?limit=3&e\u00e7ho=true'
        expected = ('http://example.com/v1/fizbit/messages'
                    '?limit=3&e%C3%A7ho=true')
        assert uri.encode(uri.encode(url)) == expected

        url = 'http://example.com/v1/fiz%bit/mess%ages/%'
        expected = 'http://example.com/v1/fiz%25bit/mess%25ages/%25'
        assert uri.encode(uri.encode(url)) == expected

        url = 'http://example.com/%%'
        expected = 'http://example.com/%25%25'
        assert uri.encode(uri.encode(url)) == expected

        # NOTE(kgriffs): Specific example cited in GH issue
        url = 'http://something?redirect_uri=http%3A%2F%2Fsite'
        assert uri.encode(url) == url

        hex_digits = 'abcdefABCDEF0123456789'
        for c1 in hex_digits:
            for c2 in hex_digits:
                url = 'http://example.com/%' + c1 + c2
                encoded = uri.encode(uri.encode(url))
                assert encoded == url

    def test_uri_encode_value(self):
        assert uri.encode_value('abcd') == 'abcd'
        assert uri.encode_value(u'abcd') == u'abcd'
        assert uri.encode_value(u'ab cd') == u'ab%20cd'
        assert uri.encode_value(u'\u00e7') == '%C3%A7'
        assert uri.encode_value(u'\u00e7\u20ac') == '%C3%A7%E2%82%AC'
        assert uri.encode_value('ab/cd') == 'ab%2Fcd'
        assert uri.encode_value('ab+cd=42,9') == 'ab%2Bcd%3D42%2C9'

    def test_uri_decode(self):
        assert uri.decode('abcd') == 'abcd'
        assert uri.decode(u'abcd') == u'abcd'
        assert uri.decode(u'ab%20cd') == u'ab cd'

        assert uri.decode('This thing is %C3%A7') == u'This thing is \u00e7'

        assert uri.decode('This thing is %C3%A7%E2%82%AC') == u'This thing is \u00e7\u20ac'

        assert uri.decode('ab%2Fcd') == 'ab/cd'

        assert uri.decode(
            'http://example.com?x=ab%2Bcd%3D42%2C9'
        ) == 'http://example.com?x=ab+cd=42,9'

    def test_uri_decode_unquote_plus(self):
        assert uri.decode('/disk/lost+found/fd0') == '/disk/lost found/fd0'
        assert uri.decode('/disk/lost+found/fd0', unquote_plus=True) == (
            '/disk/lost found/fd0')
        assert uri.decode('/disk/lost+found/fd0', unquote_plus=False) == (
            '/disk/lost+found/fd0')

        assert uri.decode('http://example.com?x=ab%2Bcd%3D42%2C9') == (
            'http://example.com?x=ab+cd=42,9')
        assert uri.decode('http://example.com?x=ab%2Bcd%3D42%2C9', unquote_plus=True) == (
            'http://example.com?x=ab+cd=42,9')
        assert uri.decode('http://example.com?x=ab%2Bcd%3D42%2C9', unquote_plus=False) == (
            'http://example.com?x=ab+cd=42,9')

    def test_prop_uri_encode_models_stdlib_quote(self):
        equiv_quote = functools.partial(
            compat.quote, safe=uri._ALL_ALLOWED
        )
        for case in self.uris:
            expect = equiv_quote(case)
            actual = uri.encode(case)
            assert expect == actual

    def test_prop_uri_encode_value_models_stdlib_quote_safe_tilde(self):
        equiv_quote = functools.partial(
            compat.quote, safe='~'
        )
        for case in self.uris:
            expect = equiv_quote(case)
            actual = uri.encode_value(case)
            assert expect == actual

    def test_prop_uri_decode_models_stdlib_unquote_plus(self):
        stdlib_unquote = compat.unquote_plus
        for case in self.uris:
            case = uri.encode_value(case)

            expect = stdlib_unquote(case)
            actual = uri.decode(case)
            assert expect == actual

    def test_unquote_string(self):
        assert uri.unquote_string('v') == 'v'
        assert uri.unquote_string('not-quoted') == 'not-quoted'
        assert uri.unquote_string('partial-quoted"') == 'partial-quoted"'
        assert uri.unquote_string('"partial-quoted') == '"partial-quoted'
        assert uri.unquote_string('"partial-quoted"') == 'partial-quoted'

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
        assert result['a'] == decoded_url
        assert result['b'] == decoded_json
        assert result['c'] == ['1', '2', '3']
        assert result['d'] == 'test'
        assert result['e'] == ['a', '&=,']
        assert result['f'] == ['a', 'a=b']
        assert result[u'é'] == 'a=b'

        result = uri.parse_query_string(query_strinq, True)
        assert result['a'] == decoded_url
        assert result['b'] == decoded_json
        assert result['c'] == ['1', '2', '3']
        assert result['d'] == 'test'
        assert result['e'] == ['a', '', '&=,']
        assert result['f'] == ['a', 'a=b']
        assert result[u'é'] == 'a=b'

    def test_parse_host(self):
        assert uri.parse_host('::1') == ('::1', None)
        assert uri.parse_host('2001:ODB8:AC10:FE01::') == ('2001:ODB8:AC10:FE01::', None)
        assert uri.parse_host(
            '2001:ODB8:AC10:FE01::', default_port=80
        ) == ('2001:ODB8:AC10:FE01::', 80)

        ipv6_addr = '2001:4801:1221:101:1c10::f5:116'

        assert uri.parse_host(ipv6_addr) == (ipv6_addr, None)
        assert uri.parse_host('[' + ipv6_addr + ']') == (ipv6_addr, None)
        assert uri.parse_host('[' + ipv6_addr + ']:28080') == (ipv6_addr, 28080)
        assert uri.parse_host('[' + ipv6_addr + ']:8080') == (ipv6_addr, 8080)
        assert uri.parse_host('[' + ipv6_addr + ']:123') == (ipv6_addr, 123)
        assert uri.parse_host('[' + ipv6_addr + ']:42') == (ipv6_addr, 42)

        assert uri.parse_host('173.203.44.122') == ('173.203.44.122', None)
        assert uri.parse_host('173.203.44.122', default_port=80) == ('173.203.44.122', 80)
        assert uri.parse_host('173.203.44.122:27070') == ('173.203.44.122', 27070)
        assert uri.parse_host('173.203.44.122:123') == ('173.203.44.122', 123)
        assert uri.parse_host('173.203.44.122:42') == ('173.203.44.122', 42)

        assert uri.parse_host('example.com') == ('example.com', None)
        assert uri.parse_host('example.com', default_port=443) == ('example.com', 443)
        assert uri.parse_host('falcon.example.com') == ('falcon.example.com', None)
        assert uri.parse_host('falcon.example.com:9876') == ('falcon.example.com', 9876)
        assert uri.parse_host('falcon.example.com:42') == ('falcon.example.com', 42)

    def test_get_http_status(self):
        assert falcon.get_http_status(404) == falcon.HTTP_404
        assert falcon.get_http_status(404.3) == falcon.HTTP_404
        assert falcon.get_http_status('404.3') == falcon.HTTP_404
        assert falcon.get_http_status(404.9) == falcon.HTTP_404
        assert falcon.get_http_status('404') == falcon.HTTP_404
        assert falcon.get_http_status(123) == '123 Unknown'
        with pytest.raises(ValueError):
            falcon.get_http_status('not_a_number')
        with pytest.raises(ValueError):
            falcon.get_http_status(0)
        with pytest.raises(ValueError):
            falcon.get_http_status(0)
        with pytest.raises(ValueError):
            falcon.get_http_status(99)
        with pytest.raises(ValueError):
            falcon.get_http_status(-404.3)
        with pytest.raises(ValueError):
            falcon.get_http_status('-404')
        with pytest.raises(ValueError):
            falcon.get_http_status('-404.3')
        assert falcon.get_http_status(123, 'Go Away') == '123 Go Away'

    def test_etag_dumps_to_header_format(self):
        etag = structures.ETag('67ab43')

        assert etag.dumps() == '"67ab43"'

        etag.is_weak = True
        assert etag.dumps() == 'W/"67ab43"'

        assert structures.ETag('67a b43').dumps() == '"67a b43"'

    def test_etag_strong_vs_weak_comparison(self):
        strong_67ab43_one = structures.ETag.loads('"67ab43"')
        strong_67ab43_too = structures.ETag.loads('"67ab43"')
        strong_67aB43 = structures.ETag.loads('"67aB43"')
        weak_67ab43_one = structures.ETag.loads('W/"67ab43"')
        weak_67ab43_two = structures.ETag.loads('W/"67ab43"')
        weak_67aB43 = structures.ETag.loads('W/"67aB43"')

        assert strong_67aB43 == strong_67aB43
        assert weak_67aB43 == weak_67aB43
        assert strong_67aB43 == weak_67aB43
        assert weak_67aB43 == strong_67aB43
        assert strong_67ab43_one == strong_67ab43_too
        assert weak_67ab43_one == weak_67ab43_two

        assert strong_67aB43 != strong_67ab43_one
        assert strong_67ab43_one != strong_67aB43

        assert strong_67aB43.strong_compare(strong_67aB43)
        assert strong_67ab43_one.strong_compare(strong_67ab43_too)
        assert not strong_67aB43.strong_compare(strong_67ab43_one)
        assert not strong_67ab43_one.strong_compare(strong_67aB43)

        assert not strong_67ab43_one.strong_compare(weak_67ab43_one)
        assert not weak_67ab43_one.strong_compare(strong_67ab43_one)

        assert not weak_67aB43.strong_compare(weak_67aB43)
        assert not weak_67ab43_one.strong_compare(weak_67ab43_two)

        assert not weak_67ab43_one.strong_compare(weak_67aB43)
        assert not weak_67aB43.strong_compare(weak_67ab43_one)


@pytest.mark.parametrize(
    'protocol,method',
    zip(
        ['https'] * len(falcon.HTTP_METHODS) + ['http'] * len(falcon.HTTP_METHODS),
        falcon.HTTP_METHODS * 2
    )
)
def test_simulate_request_protocol(protocol, method):
    sink_called = [False]

    def sink(req, resp):
        sink_called[0] = True
        assert req.protocol == protocol

    app = falcon.API()
    app.add_sink(sink, '/test')

    client = testing.TestClient(app)

    try:
        simulate = client.getattr('simulate_' + method.lower())
        simulate('/test', protocol=protocol)
        assert sink_called[0]
    except AttributeError:
        # NOTE(kgriffs): simulate_* helpers do not exist for all methods
        pass


@pytest.mark.parametrize('simulate', [
    testing.simulate_get,
    testing.simulate_head,
    testing.simulate_post,
    testing.simulate_put,
    testing.simulate_options,
    testing.simulate_patch,
    testing.simulate_delete,
])
def test_simulate_free_functions(simulate):
    sink_called = [False]

    def sink(req, resp):
        sink_called[0] = True

    app = falcon.API()
    app.add_sink(sink, '/test')

    simulate(app, '/test')
    assert sink_called[0]


class TestFalconTestingUtils(object):
    """Verify some branches not covered elsewhere."""

    def test_path_escape_chars_in_create_environ(self):
        env = testing.create_environ('/hello%20world%21')
        assert env['PATH_INFO'] == '/hello world!'

    def test_no_prefix_allowed_for_query_strings_in_create_environ(self):
        with pytest.raises(ValueError):
            testing.create_environ(query_string='?foo=bar')

    @pytest.mark.skipif(compat.PY3, reason='Test does not apply to Py3K')
    def test_unicode_path_in_create_environ(self):
        env = testing.create_environ(u'/fancy/unícode')
        assert env['PATH_INFO'] == '/fancy/un\xc3\xadcode'

        env = testing.create_environ(u'/simple')
        assert env['PATH_INFO'] == '/simple'

    def test_plus_in_path_in_create_environ(self):
        env = testing.create_environ('/mnt/grub2/lost+found/inode001')
        assert env['PATH_INFO'] == '/mnt/grub2/lost+found/inode001'

    def test_none_header_value_in_create_environ(self):
        env = testing.create_environ('/', headers={'X-Foo': None})
        assert env['HTTP_X_FOO'] == ''

    def test_decode_empty_result(self):
        app = falcon.API()
        client = testing.TestClient(app)
        response = client.simulate_request(path='/')
        assert response.text == ''

    def test_httpnow_alias_for_backwards_compat(self):
        assert testing.httpnow is util.http_now

    def test_default_headers(self):
        app = falcon.API()
        resource = testing.SimpleTestResource()
        app.add_route('/', resource)

        headers = {
            'Authorization': 'Bearer 123',
        }

        client = testing.TestClient(app, headers=headers)

        client.simulate_get()
        assert resource.captured_req.auth == headers['Authorization']

        client.simulate_get(headers=None)
        assert resource.captured_req.auth == headers['Authorization']

    def test_default_headers_with_override(self):
        app = falcon.API()
        resource = testing.SimpleTestResource()
        app.add_route('/', resource)

        override_before = 'something-something'
        override_after = 'something-something'[::-1]

        headers = {
            'Authorization': 'Bearer XYZ',
            'Accept': 'application/vnd.siren+json',
            'X-Override-Me': override_before,
        }

        client = testing.TestClient(app, headers=headers)
        client.simulate_get(headers={'X-Override-Me': override_after})

        assert resource.captured_req.auth == headers['Authorization']
        assert resource.captured_req.accept == headers['Accept']
        assert resource.captured_req.get_header('X-Override-Me') == override_after

    def test_status(self):
        app = falcon.API()
        resource = testing.SimpleTestResource(status=falcon.HTTP_702)
        app.add_route('/', resource)
        client = testing.TestClient(app)

        result = client.simulate_get()
        assert result.status == falcon.HTTP_702

    def test_wsgi_iterable_not_closeable(self):
        result = testing.Result([], falcon.HTTP_200, [])
        assert not result.content
        assert result.json is None

    def test_path_must_start_with_slash(self):
        app = falcon.API()
        app.add_route('/', testing.SimpleTestResource())
        client = testing.TestClient(app)
        with pytest.raises(ValueError):
            client.simulate_get('foo')

    def test_cached_text_in_result(self):
        app = falcon.API()
        app.add_route('/', testing.SimpleTestResource(body='test'))
        client = testing.TestClient(app)

        result = client.simulate_get()
        assert result.text == result.text

    def test_simple_resource_body_json_xor(self):
        with pytest.raises(ValueError):
            testing.SimpleTestResource(body='', json={})

    def test_query_string(self):
        class SomeResource(object):
            def on_get(self, req, resp):
                doc = {}

                doc['oid'] = req.get_param_as_int('oid')
                doc['detailed'] = req.get_param_as_bool('detailed')
                doc['things'] = req.get_param_as_list('things', int)
                doc['query_string'] = req.query_string

                resp.body = json.dumps(doc)

        app = falcon.API()
        app.req_options.auto_parse_qs_csv = True
        app.add_route('/', SomeResource())
        client = testing.TestClient(app)

        result = client.simulate_get(query_string='oid=42&detailed=no&things=1')
        assert result.json['oid'] == 42
        assert not result.json['detailed']
        assert result.json['things'] == [1]

        params = {'oid': 42, 'detailed': False}
        result = client.simulate_get(params=params)
        assert result.json['oid'] == params['oid']
        assert not result.json['detailed']
        assert result.json['things'] is None

        params = {'oid': 1978, 'detailed': 'yes', 'things': [1, 2, 3]}
        result = client.simulate_get(params=params)
        assert result.json['oid'] == params['oid']
        assert result.json['detailed']
        assert result.json['things'] == params['things']

        expected_qs = 'things=1,2,3'
        result = client.simulate_get(params={'things': [1, 2, 3]})
        assert result.json['query_string'] == expected_qs

        expected_qs = 'things=1&things=2&things=3'
        result = client.simulate_get(params={'things': [1, 2, 3]},
                                     params_csv=False)
        assert result.json['query_string'] == expected_qs

    def test_query_string_no_question(self):
        app = falcon.API()
        app.add_route('/', testing.SimpleTestResource())
        client = testing.TestClient(app)
        with pytest.raises(ValueError):
            client.simulate_get(query_string='?x=1')

    def test_query_string_in_path(self):
        app = falcon.API()
        resource = testing.SimpleTestResource()
        app.add_route('/thing', resource)
        client = testing.TestClient(app)

        with pytest.raises(ValueError):
            client.simulate_get(path='/thing?x=1', query_string='things=1,2,3')
        with pytest.raises(ValueError):
            client.simulate_get(path='/thing?x=1', params={'oid': 1978})
        with pytest.raises(ValueError):
            client.simulate_get(path='/thing?x=1', query_string='things=1,2,3',
                                params={'oid': 1978})

        client.simulate_get(path='/thing?detailed=no&oid=1337')
        assert resource.captured_req.path == '/thing'
        assert resource.captured_req.query_string == 'detailed=no&oid=1337'

    @pytest.mark.parametrize('document', [
        # NOTE(vytas): using an exact binary fraction here to avoid special
        # code branch for approximate equality as it is not the focus here
        16.0625,
        123456789,
        True,
        '',
        u'I am a \u1d0a\ua731\u1d0f\u0274 string.',
        [1, 3, 3, 7],
        {u'message': u'\xa1Hello Unicode! \U0001F638'},
        {
            'count': 4,
            'items': [
                {'number': 'one'},
                {'number': 'two'},
                {'number': 'three'},
                {'number': 'four'},
            ],
            'next': None,
        },
    ])
    def test_simulate_json_body(self, document):
        app = falcon.API()
        resource = testing.SimpleTestResource()
        app.add_route('/', resource)

        json_types = ('application/json', 'application/json; charset=UTF-8')
        client = testing.TestClient(app)
        client.simulate_post('/', json=document)
        captured_body = resource.captured_req.bounded_stream.read().decode('utf-8')
        assert json.loads(captured_body) == document
        assert resource.captured_req.content_type in json_types

        headers = {
            'Content-Type': 'x-falcon/peregrine',
            'X-Falcon-Type': 'peregrine',
        }
        body = 'If provided, `json` parameter overrides `body`.'
        client.simulate_post('/', headers=headers, body=body, json=document)
        assert resource.captured_req.media == document
        assert resource.captured_req.content_type in json_types
        assert resource.captured_req.get_header('X-Falcon-Type') == 'peregrine'

    @pytest.mark.parametrize('remote_addr', [
        None,
        '127.0.0.1',
        '8.8.8.8',
        '104.24.101.85',
        '2606:4700:30::6818:6455',
    ])
    def test_simulate_remote_addr(self, remote_addr):
        class ShowMyIPResource(object):
            def on_get(self, req, resp):
                resp.body = req.remote_addr
                resp.content_type = falcon.MEDIA_TEXT

        app = falcon.API()
        app.add_route('/', ShowMyIPResource())

        client = testing.TestClient(app)
        resp = client.simulate_get('/', remote_addr=remote_addr)
        assert resp.status_code == 200

        if remote_addr is None:
            assert resp.text == '127.0.0.1'
        else:
            assert resp.text == remote_addr

    def test_simulate_hostname(self):
        app = falcon.API()
        resource = testing.SimpleTestResource()
        app.add_route('/', resource)

        client = testing.TestClient(app)
        client.simulate_get('/', protocol='https',
                            host='falcon.readthedocs.io')
        assert resource.captured_req.uri == 'https://falcon.readthedocs.io/'

    @pytest.mark.parametrize('extras,expected_headers', [
        (
            {},
            (('user-agent', 'curl/7.24.0 (x86_64-apple-darwin12.0)'),),
        ),
        (
            {'HTTP_USER_AGENT': 'URL/Emacs', 'HTTP_X_FALCON': 'peregrine'},
            (('user-agent', 'URL/Emacs'), ('x-falcon', 'peregrine')),
        ),
    ])
    def test_simulate_with_environ_extras(self, extras, expected_headers):
        app = falcon.API()
        resource = testing.SimpleTestResource()
        app.add_route('/', resource)

        client = testing.TestClient(app)
        client.simulate_get('/', extras=extras)

        for header, value in expected_headers:
            assert resource.captured_req.get_header(header) == value

    def test_override_method_with_extras(self):
        app = falcon.API()
        app.add_route('/', testing.SimpleTestResource(body='test'))
        client = testing.TestClient(app)

        with pytest.raises(ValueError):
            client.simulate_get('/', extras={'REQUEST_METHOD': 'PATCH'})

        resp = client.simulate_get('/', extras={'REQUEST_METHOD': 'GET'})
        assert resp.status_code == 200
        assert resp.text == 'test'


class TestNoApiClass(testing.TestCase):
    def test_something(self):
        self.assertTrue(isinstance(self.app, falcon.API))


class TestSetupApi(testing.TestCase):
    def setUp(self):
        super(TestSetupApi, self).setUp()
        self.api = falcon.API()

    def test_something(self):
        self.assertTrue(isinstance(self.api, falcon.API))


def test_get_argnames():
    def foo(a, b, c):
        pass

    class Bar(object):
        def __call__(self, a, b):
            pass

    assert misc.get_argnames(foo) == ['a', 'b', 'c']
    assert misc.get_argnames(Bar()) == ['a', 'b']

    # NOTE(kgriffs): This difference will go away once we drop Python 2.7
    # support, so we just use this regression test to ensure the status quo.
    expected = ['b', 'c'] if compat.PY3 else ['a', 'b', 'c']
    assert misc.get_argnames(functools.partial(foo, 42)) == expected


class TestContextType(object):

    class CustomContextType(structures.Context):
        def __init__(self):
            pass

    @pytest.mark.parametrize('context_type', [
        CustomContextType,
        structures.Context,
    ])
    def test_attributes(self, context_type):
        ctx = context_type()

        ctx.foo = 'bar'
        ctx.details = None
        ctx._cache = {}

        assert ctx.foo == 'bar'
        assert ctx.details is None
        assert ctx._cache == {}

        with pytest.raises(AttributeError):
            ctx.cache_strategy

    @pytest.mark.parametrize('context_type', [
        CustomContextType,
        structures.Context,
    ])
    def test_items_from_attributes(self, context_type):
        ctx = context_type()

        ctx.foo = 'bar'
        ctx.details = None
        ctx._cache = {}

        assert ctx['foo'] == 'bar'
        assert ctx['details'] is None
        assert ctx['_cache'] == {}

        with pytest.raises(KeyError):
            ctx['cache_strategy']

        assert 'foo' in ctx
        assert '_cache' in ctx
        assert 'cache_strategy' not in ctx

    @pytest.mark.parametrize('context_type', [
        CustomContextType,
        structures.Context,
    ])
    def test_attributes_from_items(self, context_type):
        ctx = context_type()

        ctx['foo'] = 'bar'
        ctx['details'] = None
        ctx['_cache'] = {}
        ctx['cache_strategy'] = 'lru'

        assert ctx['cache_strategy'] == 'lru'
        del ctx['cache_strategy']

        assert ctx['foo'] == 'bar'
        assert ctx['details'] is None
        assert ctx['_cache'] == {}

        with pytest.raises(KeyError):
            ctx['cache_strategy']

    @pytest.mark.parametrize('context_type,type_name', [
        (CustomContextType, 'CustomContextType'),
        (structures.Context, 'Context'),
    ])
    def test_dict_interface(self, context_type, type_name):
        ctx = context_type()

        ctx['foo'] = 'bar'
        ctx['details'] = None
        ctx[1] = 'one'
        ctx[2] = 'two'

        assert ctx == {'foo': 'bar', 'details': None, 1: 'one', 2: 'two'}
        assert ctx != {'bar': 'foo', 'details': None, 1: 'one', 2: 'two'}
        assert ctx != {}

        copy = ctx.copy()
        assert isinstance(copy, context_type)
        assert copy == ctx
        assert copy == {'foo': 'bar', 'details': None, 1: 'one', 2: 'two'}
        copy.pop('foo')
        assert copy != ctx

        assert set(key for key in ctx) == {'foo', 'details', 1, 2}

        assert ctx.get('foo') == 'bar'
        assert ctx.get('bar') is None
        assert ctx.get('bar', frozenset('hello')) == frozenset('hello')
        false = ctx.get('bar', False)
        assert isinstance(false, bool)
        assert not false

        assert len(ctx) == 4
        assert ctx.pop(3) is None
        assert ctx.pop(3, 'not found') == 'not found'
        assert ctx.pop('foo') == 'bar'
        assert ctx.pop(1) == 'one'
        assert ctx.pop(2) == 'two'
        assert len(ctx) == 1

        assert repr(ctx) == type_name + "({'details': None})"
        assert str(ctx) == type_name + "({'details': None})"
        assert '{}'.format(ctx) == type_name + "({'details': None})"

        with pytest.raises(TypeError):
            {ctx: ctx}

        ctx.clear()
        assert ctx == {}
        assert len(ctx) == 0

        ctx['key'] = 'value'
        assert ctx.popitem() == ('key', 'value')

        ctx.setdefault('numbers', []).append(1)
        ctx.setdefault('numbers', []).append(2)
        ctx.setdefault('numbers', []).append(3)
        assert ctx['numbers'] == [1, 2, 3]

    @pytest.mark.parametrize('context_type', [
        CustomContextType,
        structures.Context,
    ])
    def test_keys_and_values(self, context_type):
        ctx = context_type()
        ctx.update((number, number ** 2) for number in range(1, 5))

        assert set(ctx.keys()) == {1, 2, 3, 4}
        assert set(ctx.values()) == {1, 4, 9, 16}
        assert set(ctx.items()) == {(1, 1), (2, 4), (3, 9), (4, 16)}

    @pytest.mark.skipif(compat.PY3, reason='python2-specific dict methods')
    def test_python2_dict_methods(self):
        ctx = structures.Context()
        ctx.update((number, number ** 2) for number in range(1, 5))

        assert set(ctx.keys()) == set(ctx.iterkeys()) == set(ctx.viewkeys())
        assert set(ctx.values()) == set(ctx.itervalues()) == set(ctx.viewvalues())
        assert set(ctx.items()) == set(ctx.iteritems()) == set(ctx.viewitems())

        assert ctx.has_key(2)  # noqa
