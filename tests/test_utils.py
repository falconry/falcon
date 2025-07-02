from datetime import datetime
from datetime import timedelta
from datetime import timezone
import functools
import http
import inspect
import itertools
import json
import random
from urllib.parse import quote
from urllib.parse import unquote_plus

import pytest

import falcon
from falcon import media
from falcon import testing
from falcon.constants import MEDIA_JSON
from falcon.constants import MEDIA_MSGPACK
from falcon.constants import MEDIA_URLENCODED
from falcon.constants import MEDIA_YAML
import falcon.util
from falcon.util import deprecation
from falcon.util import misc
from falcon.util import structures
from falcon.util import uri
from falcon.util.time import TimezoneGMT

try:
    import msgpack
except ImportError:
    msgpack = None


@pytest.fixture
def app(asgi, util):
    return util.create_app(asgi)


def _arbitrary_uris(count, length):
    return (
        ''.join([random.choice(uri._ALL_ALLOWED) for _ in range(length)])
        for __ in range(count)
    )


@pytest.fixture(params=['bytearray', 'join_list'])
def decode_approach(request, monkeypatch):
    method = uri._join_tokens_list
    if request.param == 'bytearray':
        method = uri._join_tokens_bytearray
    monkeypatch.setattr(uri, '_join_tokens', method)
    return method


class TrackingJSONHandler(media.JSONHandler):
    def __init__(self):
        super().__init__()
        self.deserialize_count = 0

    def deserialize(self, *args, **kwargs):
        result = super().deserialize(*args, **kwargs)
        self.deserialize_count += 1
        return result

    async def deserialize_async(self, *args, **kwargs):
        result = await super().deserialize_async(*args, **kwargs)
        self.deserialize_count += 1
        return result


class TrackingMessagePackHandler(media.MessagePackHandler):
    def __init__(self):
        super().__init__()
        self.deserialize_count = 0

    def deserialize(self, *args, **kwargs):
        result = super().deserialize(*args, **kwargs)
        self.deserialize_count += 1
        return result

    async def deserialize_async(self, *args, **kwargs):
        result = await super().deserialize_async(*args, **kwargs)
        self.deserialize_count += 1
        return result


class TrackingFormHandler(media.URLEncodedFormHandler):
    def __init__(self):
        super().__init__()
        self.deserialize_count = 0

    def deserialize(self, *args, **kwargs):
        result = super().deserialize(*args, **kwargs)
        self.deserialize_count += 1
        return result

    async def deserialize_async(self, *args, **kwargs):
        result = await super().deserialize_async(*args, **kwargs)
        self.deserialize_count += 1
        return result


class TestFalconUtils:
    def setup_method(self, method):
        # NOTE(cabrera): for DRYness - used in uri.[de|en]code tests
        # below.
        self.uris = _arbitrary_uris(count=100, length=32)

    def test_deprecated_decorator(self):
        msg = 'Please stop using this thing. It is going away.'

        @falcon.util.deprecated(msg)
        def old_thing():
            pass

        with pytest.warns(UserWarning) as rec:
            old_thing()

        warn = rec.pop()
        assert msg in str(warn.message)

    def test_http_now(self):
        expected = datetime.now(timezone.utc)
        actual = falcon.http_date_to_dt(falcon.http_now())

        delta = actual.replace(tzinfo=timezone.utc) - expected

        assert delta.total_seconds() <= 1

    def test_dt_to_http(self):
        assert (
            falcon.dt_to_http(datetime(2013, 4, 4, tzinfo=timezone.utc))
            == 'Thu, 04 Apr 2013 00:00:00 GMT'
        )

        assert (
            falcon.dt_to_http(datetime(2013, 4, 4, 10, 28, 54, tzinfo=timezone.utc))
            == 'Thu, 04 Apr 2013 10:28:54 GMT'
        )

    def test_http_date_to_dt(self):
        assert falcon.http_date_to_dt('Thu, 04 Apr 2013 00:00:00 GMT') == datetime(
            2013, 4, 4, tzinfo=timezone.utc
        )

        assert falcon.http_date_to_dt('Thu, 04 Apr 2013 10:28:54 GMT') == datetime(
            2013, 4, 4, 10, 28, 54, tzinfo=timezone.utc
        )

        with pytest.raises(ValueError):
            falcon.http_date_to_dt('Thu, 04-Apr-2013 10:28:54 GMT')

        assert falcon.http_date_to_dt(
            'Thu, 04-Apr-2013 10:28:54 GMT', obs_date=True
        ) == datetime(2013, 4, 4, 10, 28, 54, tzinfo=timezone.utc)

        with pytest.raises(ValueError):
            falcon.http_date_to_dt('Sun Nov  6 08:49:37 1994')

        with pytest.raises(ValueError):
            falcon.http_date_to_dt('Nov  6 08:49:37 1994', obs_date=True)

        assert falcon.http_date_to_dt(
            'Sun Nov  6 08:49:37 1994', obs_date=True
        ) == datetime(1994, 11, 6, 8, 49, 37, tzinfo=timezone.utc)

        assert falcon.http_date_to_dt(
            'Sunday, 06-Nov-94 08:49:37 GMT', obs_date=True
        ) == datetime(1994, 11, 6, 8, 49, 37, tzinfo=timezone.utc)

        with pytest.raises(ValueError):
            falcon.http_date_to_dt('Thu, 04 Apr 2013 10:28:54 EST')

    def test_pack_query_params_none(self):
        assert falcon.to_query_str({}) == ''

    def test_pack_query_params_one(self):
        assert falcon.to_query_str({'limit': 10}) == '?limit=10'

        assert falcon.to_query_str({'things': [1, 2, 3]}) == '?things=1,2,3'

        assert falcon.to_query_str({'things': ['a']}) == '?things=a'

        assert falcon.to_query_str({'things': ['a', 'b']}) == '?things=a,b'

        expected = (
            '?things=a&things=b&things=&things=None&things=true&things=false&things=0'
        )

        actual = falcon.to_query_str(
            {'things': ['a', 'b', '', None, True, False, 0]},
            comma_delimited_lists=False,
        )

        assert actual == expected

    def test_pack_query_params_several(self):
        garbage_in = {'limit': 17, 'echo': True, 'doit': False, 'x': 'val', 'y': 0.2}

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
            'doit': 'false',
        }

        assert expected == garbage_out

    @pytest.mark.parametrize('csv', [True, False])
    @pytest.mark.parametrize(
        'params',
        [
            {'a & b': 'a and b', 'b and c': 'b & c'},
            {'apples and oranges': '🍏 & 🍊'},
            {'garbage': ['&', '&+&', 'a=1&b=2', 'c=4&'], 'one': '1'},
            {'&': '&amp;', '™': '&trade;', '&&&': ['&amp;', '&amp;', '&amp;']},
            {'&': '%26', '&&': '%26', '&&&': ['%26', '%2', '%']},
        ],
    )
    def test_to_query_str_encoding(self, params, csv):
        query_str = falcon.to_query_str(params, comma_delimited_lists=csv, prefix=False)

        assert uri.parse_query_string(query_str, csv=csv) == params

    def test_uri_encode(self):
        url = 'http://example.com/v1/fizbit/messages?limit=3&echo=true'
        assert uri.encode(url) == url

        url = 'http://example.com/v1/fiz bit/messages'
        expected = 'http://example.com/v1/fiz%20bit/messages'
        assert uri.encode(url) == expected

        url = 'http://example.com/v1/fizbit/messages?limit=3&e\u00e7ho=true'
        expected = 'http://example.com/v1/fizbit/messages?limit=3&e%C3%A7ho=true'
        assert uri.encode(url) == expected

        # NOTE(minesja): Addresses #1872
        assert uri.encode('%26') == '%2526'
        assert uri.decode(uri.encode('%26')) == '%26'

    def test_uri_encode_double(self):
        url = 'http://example.com/v1/fiz bit/messages'
        expected = 'http://example.com/v1/fiz%20bit/messages'
        assert uri.encode_check_escaped(uri.encode_check_escaped(url)) == expected

        url = 'http://example.com/v1/fizbit/messages?limit=3&e\u00e7ho=true'
        expected = 'http://example.com/v1/fizbit/messages?limit=3&e%C3%A7ho=true'
        assert uri.encode_check_escaped(uri.encode_check_escaped(url)) == expected

        url = 'http://example.com/v1/fiz%bit/mess%ages/%'
        expected = 'http://example.com/v1/fiz%25bit/mess%25ages/%25'
        assert uri.encode_check_escaped(uri.encode_check_escaped(url)) == expected

        url = 'http://example.com/%%'
        expected = 'http://example.com/%25%25'
        assert uri.encode_check_escaped(uri.encode_check_escaped(url)) == expected

        # NOTE(kgriffs): Specific example cited in GH issue
        url = 'http://something?redirect_uri=http%3A%2F%2Fsite'
        assert uri.encode_check_escaped(url) == url

        hex_digits = 'abcdefABCDEF0123456789'
        for c1 in hex_digits:
            for c2 in hex_digits:
                url = 'http://example.com/%' + c1 + c2
                encoded = uri.encode_check_escaped(uri.encode_check_escaped(url))
                assert encoded == url

    def test_uri_encode_value(self):
        assert uri.encode_value('abcd') == 'abcd'
        assert uri.encode_value('abcd') == 'abcd'
        assert uri.encode_value('ab cd') == 'ab%20cd'
        assert uri.encode_value('\u00e7') == '%C3%A7'
        assert uri.encode_value('\u00e7\u20ac') == '%C3%A7%E2%82%AC'
        assert uri.encode_value('ab/cd') == 'ab%2Fcd'
        assert uri.encode_value('ab+cd=42,9') == 'ab%2Bcd%3D42%2C9'

        # NOTE(minesja): Addresses #1872
        assert uri.encode_value('%26') == '%2526'
        assert uri.decode(uri.encode_value('%26')) == '%26'

    def test_uri_decode(self, decode_approach):
        assert uri.decode('abcd') == 'abcd'
        assert uri.decode('ab%20cd') == 'ab cd'

        assert uri.decode('This thing is %C3%A7') == 'This thing is \u00e7'

        assert (
            uri.decode('This thing is %C3%A7%E2%82%AC') == 'This thing is \u00e7\u20ac'
        )

        assert uri.decode('ab%2Fcd') == 'ab/cd'

        assert (
            uri.decode('http://example.com?x=ab%2Bcd%3D42%2C9')
            == 'http://example.com?x=ab+cd=42,9'
        )

    @pytest.mark.parametrize(
        'encoded,expected',
        [
            ('ab%2Gcd', 'ab%2Gcd'),
            ('ab%2Fcd: 100% coverage', 'ab/cd: 100% coverage'),
            ('%s' * 100, '%s' * 100),
        ],
    )
    def test_uri_decode_bad_coding(self, encoded, expected, decode_approach):
        assert uri.decode(encoded) == expected

    @pytest.mark.parametrize(
        'encoded,expected',
        [
            ('+%80', ' �'),
            ('+++%FF+++', '   �   '),  # impossible byte
            ('%fc%83%bf%bf%bf%bf', '������'),  # overlong sequence
            ('%ed%ae%80%ed%b0%80', '������'),  # paired UTF-16 surrogates
        ],
    )
    def test_uri_decode_bad_unicode(self, encoded, expected, decode_approach):
        assert uri.decode(encoded) == expected

    def test_uri_decode_unquote_plus(self, decode_approach):
        assert uri.decode('/disk/lost+found/fd0') == '/disk/lost found/fd0'
        assert uri.decode('/disk/lost+found/fd0', unquote_plus=True) == (
            '/disk/lost found/fd0'
        )
        assert uri.decode('/disk/lost+found/fd0', unquote_plus=False) == (
            '/disk/lost+found/fd0'
        )

        assert uri.decode('http://example.com?x=ab%2Bcd%3D42%2C9') == (
            'http://example.com?x=ab+cd=42,9'
        )
        assert uri.decode(
            'http://example.com?x=ab%2Bcd%3D42%2C9', unquote_plus=True
        ) == ('http://example.com?x=ab+cd=42,9')
        assert uri.decode(
            'http://example.com?x=ab%2Bcd%3D42%2C9', unquote_plus=False
        ) == ('http://example.com?x=ab+cd=42,9')

    def test_prop_uri_encode_models_stdlib_quote(self):
        equiv_quote = functools.partial(quote, safe=uri._ALL_ALLOWED)
        for case in self.uris:
            expect = equiv_quote(case)
            actual = uri.encode(case)
            assert expect == actual

    def test_prop_uri_encode_value_models_stdlib_quote_safe_tilde(self):
        equiv_quote = functools.partial(quote, safe='~')
        for case in self.uris:
            expect = equiv_quote(case)
            actual = uri.encode_value(case)
            assert expect == actual

    def test_prop_uri_decode_models_stdlib_unquote_plus(self):
        stdlib_unquote = unquote_plus
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
        query_string = (
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

        result = uri.parse_query_string(query_string)
        assert result['a'] == decoded_url
        assert result['b'] == decoded_json
        assert result['c'] == '1,2,3'
        assert result['d'] == 'test'
        assert result['e'] == 'a,,&=,'
        assert result['f'] == ['a', 'a=b']
        assert result['é'] == 'a=b'

        result = uri.parse_query_string(query_string, True, True)
        assert result['a'] == decoded_url
        assert result['b'] == decoded_json
        assert result['c'] == ['1', '2', '3']
        assert result['d'] == 'test'
        assert result['e'] == ['a', '', '&=,']
        assert result['f'] == ['a', 'a=b']
        assert result['é'] == 'a=b'

        result = uri.parse_query_string(query_string, csv=True)
        assert result['a'] == decoded_url
        assert result['b'] == decoded_json
        assert result['c'] == ['1', '2', '3']
        assert result['d'] == 'test'
        assert result['e'] == ['a', '&=,']
        assert result['f'] == ['a', 'a=b']
        assert result['é'] == 'a=b'

    @pytest.mark.parametrize(
        'query_string,keep_blank,expected',
        [
            ('', True, {}),
            ('', False, {}),
            ('flag1&&&&&flag2&&&', True, {'flag1': '', 'flag2': ''}),
            ('flag1&&&&&flag2&&&', False, {}),
            ('malformed=%FG%1%Hi%%%a', False, {'malformed': '%FG%1%Hi%%%a'}),
            ('=', False, {}),
            ('==', False, {'': '='}),
            (
                '%==+==&&&&&&&&&%%==+=&&&&&&%0g%=%=',
                False,
                {'%': '= ==', '%%': '= =', '%0g%': '%='},
            ),
            ('%=&%%=&&%%%=', False, {}),
            ('%=&%%=&&%%%=', True, {'%': '', '%%': '', '%%%': ''}),
            ('+=&%+=&&%++=', True, {' ': '', '% ': '', '%  ': ''}),
            ('=x=&=x=+1=x=&%=x', False, {'': ['x=', 'x= 1=x='], '%': 'x'}),
            (
                ''.join(
                    itertools.chain.from_iterable(itertools.permutations('%=+&', 4))
                ),
                False,
                {
                    '': ['%', ' %', '%', ' ', ' =%', '%', '% ', ' %'],
                    ' ': ['=% ', ' %', '%'],
                    '%': [' ', ' ', ' '],
                },
            ),
            # NOTE(vytas): Sanity check that we do not accidentally use C-strings
            #   anywhere in the cythonized variant.
            ('%%%\x00%\x00==\x00\x00==', True, {'%%%\x00%\x00': '=\x00\x00=='}),
            ('spade=♠&spade=♠', False, {'spade': ['♠', '♠']}),  # Unicode query
        ],
    )
    def test_parse_query_string_edge_cases(self, query_string, keep_blank, expected):
        assert uri.parse_query_string(query_string, keep_blank=keep_blank) == (expected)

    def test_parse_host(self):
        assert uri.parse_host('::1') == ('::1', None)
        assert uri.parse_host('2001:ODB8:AC10:FE01::') == (
            '2001:ODB8:AC10:FE01::',
            None,
        )
        assert uri.parse_host('2001:ODB8:AC10:FE01::', default_port=80) == (
            '2001:ODB8:AC10:FE01::',
            80,
        )

        ipv6_addr = '2001:4801:1221:101:1c10::f5:116'

        assert uri.parse_host(ipv6_addr) == (ipv6_addr, None)
        assert uri.parse_host('[' + ipv6_addr + ']') == (ipv6_addr, None)
        assert uri.parse_host('[' + ipv6_addr + ']:28080') == (ipv6_addr, 28080)
        assert uri.parse_host('[' + ipv6_addr + ']:8080') == (ipv6_addr, 8080)
        assert uri.parse_host('[' + ipv6_addr + ']:123') == (ipv6_addr, 123)
        assert uri.parse_host('[' + ipv6_addr + ']:42') == (ipv6_addr, 42)

        assert uri.parse_host('173.203.44.122') == ('173.203.44.122', None)
        assert uri.parse_host('173.203.44.122', default_port=80) == (
            '173.203.44.122',
            80,
        )
        assert uri.parse_host('173.203.44.122:27070') == ('173.203.44.122', 27070)
        assert uri.parse_host('173.203.44.122:123') == ('173.203.44.122', 123)
        assert uri.parse_host('173.203.44.122:42') == ('173.203.44.122', 42)

        assert uri.parse_host('example.com') == ('example.com', None)
        assert uri.parse_host('example.com', default_port=443) == ('example.com', 443)
        assert uri.parse_host('falcon.example.com') == ('falcon.example.com', None)
        assert uri.parse_host('falcon.example.com:9876') == ('falcon.example.com', 9876)
        assert uri.parse_host('falcon.example.com:42') == ('falcon.example.com', 42)

    @pytest.mark.parametrize(
        'v_in,v_out',
        [
            (703, falcon.HTTP_703),
            (404, falcon.HTTP_404),
            (404.9, falcon.HTTP_404),
            (falcon.HTTP_200, falcon.HTTP_200),
            (falcon.HTTP_307, falcon.HTTP_307),
            (falcon.HTTP_404, falcon.HTTP_404),
            (123, '123 Unknown'),
            ('123 Wow Such Status', '123 Wow Such Status'),
            (b'123 Wow Such Status', '123 Wow Such Status'),
            (b'200 OK', falcon.HTTP_OK),
            (http.HTTPStatus(200), falcon.HTTP_200),
            (http.HTTPStatus(307), falcon.HTTP_307),
            (http.HTTPStatus(401), falcon.HTTP_401),
            (http.HTTPStatus(410), falcon.HTTP_410),
            (http.HTTPStatus(429), falcon.HTTP_429),
            (http.HTTPStatus(500), falcon.HTTP_500),
        ],
    )
    def test_code_to_http_status(self, v_in, v_out):
        assert falcon.code_to_http_status(v_in) == v_out

    @pytest.mark.parametrize(
        'v',
        [
            0,
            13,
            99,
            1000,
            1337.01,
            -99,
            -404.3,
            -404,
            -404.3,
            'Successful',
            'Failed',
            None,
        ],
    )
    def test_code_to_http_status_value_error(self, v):
        with pytest.raises(ValueError):
            falcon.code_to_http_status(v)

    @pytest.mark.parametrize(
        'v_in,v_out',
        [
            # NOTE(kgriffs): Include some codes not used elsewhere so that
            #   we get past the LRU.
            (http.HTTPStatus(505), 505),
            (712, 712),
            ('712', 712),
            (b'404 Not Found', 404),
            (b'712 NoSQL', 712),
            ('404 Not Found', 404),
            ('123 Wow Such Status', 123),
            # NOTE(kgriffs): Test LRU
            (http.HTTPStatus(505), 505),
            ('123 Wow Such Status', 123),
        ],
    )
    def test_http_status_to_code(self, v_in, v_out):
        assert falcon.http_status_to_code(v_in) == v_out

    @pytest.mark.parametrize('v', ['', ' ', '1', '12', '99', 'catsup', b'', 5.2])
    def test_http_status_to_code_neg(self, v):
        with pytest.raises(ValueError):
            falcon.http_status_to_code(v)

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
        'filename,max_length,expected',
        [
            ('.', None, '_'),
            ('..', None, '_.'),
            ('hello.txt', None, 'hello.txt'),
            ('Ąžuolai žaliuos.jpeg', None, 'A_z_uolai_z_aliuos.jpeg'),
            ('/etc/shadow', None, '_etc_shadow'),
            ('. ⬅ a dot', None, '____a_dot'),
            ('C:\\Windows\\kernel32.dll', None, 'C__Windows_kernel32.dll'),
            ('hello.txt', 8, 'hell.txt'),
            ('hello.txt', 5, 'h.txt'),
            ('hello.txt', 4, 'hell'),
            ('Ąžuolai žaliuos.jpeg', 0, 'A_z_uolai_z_aliuos.jpeg'),
            ('Ąžuolai žaliuos.jpeg', 10, 'A_z_u.jpeg'),
            ('Ąžuolai žaliuos.jpeg', 6, 'A.jpeg'),
            ('Ąžuolai žaliuos.jpeg', 5, 'A_z_u'),
            ('Ąžuolai žaliuos.jpeg', 3, 'A_z'),
            ('Ąžuolai žaliuos.jpeg', 1, 'A'),
            ('.emacs.d/init.el', 11, '_emacs.d.el'),
            ('~/.emacs.d/init.el', 11, '__.emacs.el'),
            ('. ⬅ a dot', 10, '____a_dot'),
        ],
    )
    def test_secure_filename(self, filename, max_length, expected):
        assert misc.secure_filename(filename, max_length) == expected

    def test_secure_filename_empty_value(self):
        with pytest.raises(ValueError):
            misc.secure_filename('')

    def test_secure_filename_invalid_max_length(self):
        with pytest.raises(ValueError):
            misc.secure_filename('Document.pdf', -11)

    def test_misc_isascii(self):
        with pytest.warns(deprecation.DeprecatedWarning):
            assert misc.isascii('foobar')


@pytest.mark.parametrize(
    'protocol,method',
    zip(
        ['https'] * len(falcon.HTTP_METHODS) + ['http'] * len(falcon.HTTP_METHODS),
        falcon.HTTP_METHODS * 2,
    ),
)
def test_simulate_request_protocol(asgi, protocol, method, util):
    sink_called = [False]

    def sink(req, resp):
        sink_called[0] = True
        assert req.protocol == protocol

    if asgi:
        sink = util.to_coroutine(sink)

    app = util.create_app(asgi)
    app.add_sink(sink, '/test')

    client = testing.TestClient(app)

    try:
        simulate = client.getattr('simulate_' + method.lower())
        simulate('/test', protocol=protocol)
        assert sink_called[0]
    except AttributeError:
        # NOTE(kgriffs): simulate_* helpers do not exist for all methods
        pass


@pytest.mark.parametrize(
    'simulate',
    [
        testing.simulate_get,
        testing.simulate_head,
        testing.simulate_post,
        testing.simulate_put,
        testing.simulate_options,
        testing.simulate_patch,
        testing.simulate_delete,
    ],
)
def test_simulate_free_functions(asgi, simulate, util):
    sink_called = [False]

    def sink(req, resp):
        sink_called[0] = True

    if asgi:
        sink = util.to_coroutine(sink)

    app = util.create_app(asgi)
    app.add_sink(sink, '/test')

    simulate(app, '/test')
    assert sink_called[0]


class TestFalconTestingUtils:
    """Verify some branches not covered elsewhere."""

    def test_path_escape_chars_in_create_environ(self):
        env = testing.create_environ('/hello%20world%21')
        assert env['PATH_INFO'] == '/hello world!'

    def test_no_prefix_allowed_for_query_strings_in_create_environ(self):
        with pytest.raises(ValueError):
            testing.create_environ(query_string='?foo=bar')

    def test_plus_in_path_in_create_environ(self):
        env = testing.create_environ('/mnt/grub2/lost+found/inode001')
        assert env['PATH_INFO'] == '/mnt/grub2/lost+found/inode001'

    def test_none_header_value_in_create_environ(self):
        env = testing.create_environ('/', headers={'X-Foo': None})
        assert env['HTTP_X_FOO'] == ''

    def test_decode_empty_result(self, app):
        client = testing.TestClient(app)
        response = client.simulate_request(path='/')
        assert response.json == falcon.HTTPNotFound().to_dict()

    def test_httpnow_alias_for_backwards_compat(self):
        # Ensure that both the alias and decorated alias work
        assert (
            testing.httpnow is falcon.util.http_now
            or inspect.unwrap(testing.httpnow) is falcon.util.http_now
        )

    def test_default_headers(self, app):
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

    def test_default_headers_with_override(self, app):
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

    def test_status(self, app):
        resource = testing.SimpleTestResource(status=falcon.HTTP_702)
        app.add_route('/', resource)
        client = testing.TestClient(app)

        result = client.simulate_get()
        assert result.status == falcon.HTTP_702

    @pytest.mark.parametrize(
        'simulate',
        [
            testing.simulate_get,
            testing.simulate_post,
        ],
    )
    @pytest.mark.parametrize(
        'value',
        (
            'd\xff\xff\x00',
            'quick fox jumps over the lazy dog',
            '{"hello": "WORLD!"}',
            'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Praese',
            '{"hello": "WORLD!", "greetings": "fellow traveller"}',
            '\xe9\xe8',
        ),
    )
    def test_repr_result_when_body_varies(self, asgi, util, value, simulate):
        if isinstance(value, str):
            value = bytes(value, 'UTF-8')

        if asgi:
            resource = testing.SimpleTestResourceAsync(body=value)
        else:
            resource = testing.SimpleTestResource(body=value)

        app = util.create_app(asgi)
        app.add_route('/hello', resource)

        result = simulate(app, '/hello')
        captured_resp = resource.captured_resp
        content = captured_resp.text

        if len(value) > 40:
            content = value[:20] + b'...' + value[-20:]
        else:
            content = value

        args = [
            captured_resp.status,
            captured_resp.headers['content-type'],
            str(content),
        ]

        expected_content = ' '.join(filter(None, args))

        expected_result = 'Result<{}>'.format(expected_content)

        assert str(result) == expected_result

    def test_repr_without_content_type_header(self, asgi):
        value = b'huh'
        header = [('Not-content-type', 'no!')]
        result = falcon.testing.Result([value], falcon.HTTP_200, header)

        expected_result = 'Result<200 OK {}>'.format(value)
        assert str(result) == expected_result

    @pytest.mark.parametrize(
        'simulate',
        [
            testing.simulate_get,
            testing.simulate_post,
        ],
    )
    @pytest.mark.parametrize(
        'value',
        (
            'd\xff\xff\x00',
            'quick fox jumps over the lazy dog',
            '{"hello": "WORLD!"}',
            'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Praese',
            '{"hello": "WORLD!", "greetings": "fellow traveller"}',
            '\xe9\xe8',
        ),
    )
    def test_rich_repr_result_when_body_varies(self, asgi, util, value, simulate):
        if isinstance(value, str):
            value = bytes(value, 'UTF-8')

        if asgi:
            resource = testing.SimpleTestResourceAsync(body=value)
        else:
            resource = testing.SimpleTestResource(body=value)

        app = util.create_app(asgi)
        app.add_route('/hello', resource)

        result: falcon.testing.Result = simulate(app, '/hello')
        captured_resp = resource.captured_resp
        content = captured_resp.text

        if len(value) > 40:
            content = value[:20] + b'...' + value[-20:]
        else:
            content = value

        args = [
            captured_resp.status,
            captured_resp.headers['content-type'],
            str(content),
        ]

        status_color: str

        for prefix, color in (
            ('1', 'blue'),
            ('2', 'green'),
            ('3', 'magenta'),
            ('4', 'red'),
            ('5', 'red'),
        ):
            if captured_resp.status.startswith(prefix):
                status_color = color

        result_template = (
            '[bold]Result[/]<[bold {}]{}[/] [italic yellow]{}[/] [grey50]{}[/]>'
        )
        expected_result = result_template.format(status_color, *args)

        assert result.__rich__() == expected_result

    @pytest.mark.parametrize(
        'value',
        (
            'd\xff\xff\x00',
            'quick fox jumps over the lazy dog',
            '{"hello": "WORLD!"}',
            'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Praese',
            '{"hello": "WORLD!", "greetings": "fellow traveller"}',
            '\xe9\xe8',
        ),
    )
    @pytest.mark.parametrize(
        'status_color_pair',
        (
            (falcon.HTTP_101, 'blue'),
            (falcon.HTTP_200, 'green'),
            (falcon.HTTP_301, 'magenta'),
            (falcon.HTTP_404, 'red'),
            (falcon.HTTP_500, 'red'),
        ),
    )
    def test_rich_repr_with_different_statuses(self, asgi, status_color_pair, value):
        expected_status, expected_color = status_color_pair

        if isinstance(value, str):
            value = bytes(value, 'UTF-8')

        result = falcon.testing.Result(
            [value], expected_status, [('content-type', 'dummy')]
        )

        if len(value) > 40:
            content = value[:20] + b'...' + value[-20:]
        else:
            content = value

        expected_result_template = (
            '[bold]Result[/]<[bold {}]{}[/] [italic yellow]{}[/] [grey50]{}[/]>'
        )

        expected_result = expected_result_template.format(
            expected_color, expected_status, 'dummy', content
        )

        assert result.__rich__() == expected_result

    def test_wsgi_iterable_not_closeable(self):
        result = testing.Result([], falcon.HTTP_200, [])
        assert not result.content
        assert result.json is None

    def test_path_must_start_with_slash(self, app):
        app.add_route('/', testing.SimpleTestResource())
        client = testing.TestClient(app)
        with pytest.raises(ValueError):
            client.simulate_get('foo')

    def test_cached_text_in_result(self, app):
        app.add_route('/', testing.SimpleTestResource(body='test'))
        client = testing.TestClient(app)

        result = client.simulate_get()
        assert result.text == result.text

    @pytest.mark.parametrize(
        'resource_type',
        [
            testing.SimpleTestResource,
            testing.SimpleTestResourceAsync,
        ],
    )
    def test_simple_resource_body_json_xor(self, resource_type):
        with pytest.raises(ValueError):
            resource_type(body='', json={})

    def test_query_string(self, app):
        class SomeResource:
            def on_get(self, req, resp):
                doc = {}

                doc['oid'] = req.get_param_as_int('oid')
                doc['detailed'] = req.get_param_as_bool('detailed')
                doc['things'] = req.get_param_as_list('things', int)
                doc['query_string'] = req.query_string

                resp.text = json.dumps(doc)

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

        expected_qs = 'things=1&things=2&things=3'
        result = client.simulate_get(params={'things': [1, 2, 3]})
        assert result.json['query_string'] == expected_qs

        expected_qs = 'things=1,2,3'
        result = client.simulate_get(params={'things': [1, 2, 3]}, params_csv=True)
        assert result.json['query_string'] == expected_qs

    def test_query_string_no_question(self, app):
        app.add_route('/', testing.SimpleTestResource())
        client = testing.TestClient(app)
        with pytest.raises(ValueError):
            client.simulate_get(query_string='?x=1')

    def test_query_string_in_path(self, app):
        resource = testing.SimpleTestResource()
        app.add_route('/thing', resource)
        client = testing.TestClient(app)

        with pytest.raises(ValueError):
            client.simulate_get(path='/thing?x=1', query_string='things=1,2,3')
        with pytest.raises(ValueError):
            client.simulate_get(path='/thing?x=1', params={'oid': 1978})
        with pytest.raises(ValueError):
            client.simulate_get(
                path='/thing?x=1', query_string='things=1,2,3', params={'oid': 1978}
            )

        client.simulate_get(path='/thing?detailed=no&oid=1337')
        assert resource.captured_req.path == '/thing'
        assert resource.captured_req.query_string == 'detailed=no&oid=1337'

    @pytest.mark.parametrize(
        'document',
        [
            # NOTE(vytas): using an exact binary fraction here to avoid special
            # code branch for approximate equality as it is not the focus here
            16.0625,
            123456789,
            True,
            '',
            'I am a \u1d0a\ua731\u1d0f\u0274 string.',
            [1, 3, 3, 7],
            {'message': '\xa1Hello Unicode! \U0001f638'},
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
        ],
    )
    def test_simulate_json_body(self, asgi, util, document):
        resource = (
            testing.SimpleTestResourceAsync() if asgi else testing.SimpleTestResource()
        )
        app = util.create_app(asgi)
        app.add_route('/', resource)

        json_types = ('application/json', 'application/json; charset=UTF-8')
        client = testing.TestClient(app)
        client.simulate_post(
            '/', json=document, headers={'capture-req-body-bytes': '-1'}
        )
        assert json.loads(resource.captured_req_body.decode()) == document
        assert resource.captured_req.content_type in json_types

        headers = {
            'Content-Type': 'x-falcon/peregrine',
            'X-Falcon-Type': 'peregrine',
            'capture-req-media': 'y',
        }
        body = 'If provided, `json` parameter overrides `body`.'
        client.simulate_post('/', headers=headers, body=body, json=document)
        assert resource.captured_req_media == document
        assert resource.captured_req.content_type in json_types
        assert resource.captured_req.get_header('X-Falcon-Type') == 'peregrine'

    @pytest.mark.parametrize(
        'remote_addr',
        [
            None,
            '127.0.0.1',
            '8.8.8.8',
            '104.24.101.85',
            '2606:4700:30::6818:6455',
        ],
    )
    def test_simulate_remote_addr(self, app, remote_addr):
        class ShowMyIPResource:
            def on_get(self, req, resp):
                resp.text = req.remote_addr
                resp.content_type = falcon.MEDIA_TEXT

        app.add_route('/', ShowMyIPResource())

        client = testing.TestClient(app)
        resp = client.simulate_get('/', remote_addr=remote_addr)
        assert resp.status_code == 200

        if remote_addr is None:
            assert resp.text == '127.0.0.1'
        else:
            assert resp.text == remote_addr

    def test_simulate_hostname(self, app):
        resource = testing.SimpleTestResource()
        app.add_route('/', resource)

        client = testing.TestClient(app)
        client.simulate_get('/', protocol='https', host='falcon.readthedocs.io')
        assert resource.captured_req.uri == 'https://falcon.readthedocs.io/'

    @pytest.mark.parametrize(
        'extras,expected_headers',
        [
            (
                {},
                (('user-agent', 'falcon-client/' + falcon.__version__),),
            ),
            (
                {'HTTP_USER_AGENT': 'URL/Emacs', 'HTTP_X_FALCON': 'peregrine'},
                (('user-agent', 'URL/Emacs'), ('x-falcon', 'peregrine')),
            ),
        ],
    )
    def test_simulate_with_environ_extras(self, extras, expected_headers):
        app = falcon.App()
        resource = testing.SimpleTestResource()
        app.add_route('/', resource)

        client = testing.TestClient(app)
        client.simulate_get('/', extras=extras)

        for header, value in expected_headers:
            assert resource.captured_req.get_header(header) == value

    def test_override_method_with_extras(self, asgi, util):
        app = util.create_app(asgi)
        app.add_route('/', testing.SimpleTestResource(body='test'))
        client = testing.TestClient(app)

        with pytest.raises(ValueError):
            if asgi:
                client.simulate_get('/', extras={'method': 'PATCH'})
            else:
                client.simulate_get('/', extras={'REQUEST_METHOD': 'PATCH'})

        result = client.simulate_get('/', extras={'REQUEST_METHOD': 'GET'})
        assert result.status_code == 200
        assert result.text == 'test'

    @pytest.mark.parametrize(
        'content_type',
        [
            'application/json',
            'application/json; charset=UTF-8',
            'application/yaml',
        ],
    )
    def test_simulate_content_type(self, util, content_type):
        class MediaMirror:
            def on_post(self, req, resp):
                resp.media = req.media

        app = util.create_app(asgi=False)
        app.add_route('/', MediaMirror())

        client = testing.TestClient(app)
        headers = {'Content-Type': content_type}
        payload = b'{"hello": "world"}'

        resp = client.simulate_post('/', headers=headers, body=payload)

        if MEDIA_JSON in content_type:
            assert resp.status_code == 200
            assert resp.json == {'hello': 'world'}
        else:
            # JSON handler should not have been called for YAML
            assert resp.status_code == 415

    @pytest.mark.parametrize(
        'content_type',
        [
            MEDIA_JSON,
            MEDIA_JSON + '; charset=UTF-8',
            MEDIA_YAML,
            MEDIA_MSGPACK,
            MEDIA_URLENCODED,
        ],
    )
    @pytest.mark.skipif(msgpack is None, reason='msgpack is required for this test')
    def test_simulate_content_type_extra_handler(self, asgi, util, content_type):
        class TestResourceAsync(testing.SimpleTestResourceAsync):
            def __init__(self):
                super().__init__()

            async def on_post(self, req, resp):
                await super().on_post(req, resp)

                resp.media = {'hello': 'back'}
                resp.content_type = content_type

        class TestResource(testing.SimpleTestResource):
            def __init__(self):
                super().__init__()

            def on_post(self, req, resp):
                super().on_post(req, resp)

                resp.media = {'hello': 'back'}
                resp.content_type = content_type

        resource = TestResourceAsync() if asgi else TestResource()
        app = util.create_app(asgi)
        app.add_route('/', resource)

        json_handler = TrackingJSONHandler()
        msgpack_handler = TrackingMessagePackHandler()
        form_handler = TrackingFormHandler()

        # NOTE(kgriffs): Do not use MEDIA_* so that we can sanity-check that
        #   our constants that are used in the pytest parametrization match
        #   up to what we expect them to be.
        extra_handlers = {
            'application/json': json_handler,
            'application/msgpack': msgpack_handler,
            'application/x-www-form-urlencoded': form_handler,
        }
        app.req_options.media_handlers.update(extra_handlers)
        app.resp_options.media_handlers.update(extra_handlers)

        client = testing.TestClient(app)
        headers = {
            'Content-Type': content_type,
            'capture-req-media': 'y',
        }

        if MEDIA_JSON in content_type:
            payload = b'{"hello": "world"}'
        elif content_type == MEDIA_MSGPACK:
            payload = b'\x81\xa5hello\xa5world'
        elif content_type == MEDIA_URLENCODED:
            payload = b'hello=world'
        else:
            payload = None

        resp = client.simulate_post('/', headers=headers, body=payload)

        if MEDIA_JSON in content_type:
            assert resp.status_code == 200
            assert resp.json == {'hello': 'back'}

            # Test that our custom deserializer was called
            assert json_handler.deserialize_count == 1
            assert resource.captured_req_media == {'hello': 'world'}

            # Verify that other handlers were not called
            assert msgpack_handler.deserialize_count == 0
            assert form_handler.deserialize_count == 0

        elif content_type == MEDIA_MSGPACK:
            assert resp.status_code == 200
            assert resp.content == b'\x81\xa5hello\xa4back'

            # Test that our custom deserializer was called
            assert msgpack_handler.deserialize_count == 1
            assert resource.captured_req_media == {'hello': 'world'}

            # Verify that other handlers were not called
            assert json_handler.deserialize_count == 0
            assert form_handler.deserialize_count == 0

        elif content_type == MEDIA_URLENCODED:
            assert resp.status_code == 200
            assert resp.content == b'hello=back'

            # Test that our custom deserializer was called
            assert form_handler.deserialize_count == 1
            assert resource.captured_req_media == {'hello': 'world'}

            # Verify that other handlers were not called
            assert json_handler.deserialize_count == 0
            assert msgpack_handler.deserialize_count == 0

        else:
            # YAML should not get handled
            for handler in (json_handler, msgpack_handler):
                assert handler.deserialize_count == 0

            assert resource.captured_req_media is None
            assert resp.status_code == 415


class TestNoApiClass(testing.TestCase):
    def test_something(self):
        self.assertTrue(isinstance(self.app, falcon.App))


class TestSetupApi(testing.TestCase):
    def setUp(self):
        super(TestSetupApi, self).setUp()
        with pytest.warns(UserWarning, match='API class will be removed in Falcon 5.0'):
            self.app = falcon.API()
        self.app.add_route('/', testing.SimpleTestResource(body='test'))

    def test_something(self):
        self.assertTrue(isinstance(self.app, falcon.API))
        self.assertTrue(isinstance(self.app, falcon.App))

        result = self.simulate_get()
        assert result.status_code == 200
        assert result.text == 'test'


def test_get_argnames():
    def foo(a, b, c):
        pass

    class Bar:
        def __call__(self, a, b):
            pass

    assert misc.get_argnames(foo) == ['a', 'b', 'c']
    assert misc.get_argnames(Bar()) == ['a', 'b']
    assert misc.get_argnames(functools.partial(foo, 42)) == ['b', 'c']


class TestContextType:
    class CustomContextType(structures.Context):
        def __init__(self):
            pass

    @pytest.mark.parametrize(
        'context_type',
        [
            CustomContextType,
            structures.Context,
        ],
    )
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

    @pytest.mark.parametrize(
        'context_type',
        [
            CustomContextType,
            structures.Context,
        ],
    )
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

    @pytest.mark.parametrize(
        'context_type',
        [
            CustomContextType,
            structures.Context,
        ],
    )
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

    @pytest.mark.parametrize(
        'context_type,type_name',
        [
            (CustomContextType, 'CustomContextType'),
            (structures.Context, 'Context'),
        ],
    )
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

    @pytest.mark.parametrize(
        'context_type',
        [
            CustomContextType,
            structures.Context,
        ],
    )
    def test_keys_and_values(self, context_type):
        ctx = context_type()
        ctx.update((number, number**2) for number in range(1, 5))

        assert set(ctx.keys()) == {1, 2, 3, 4}
        assert set(ctx.values()) == {1, 4, 9, 16}
        assert set(ctx.items()) == {(1, 1), (2, 4), (3, 9), (4, 16)}


class TestDeprecatedArgs:
    def test_method(self, recwarn):
        class C:
            @deprecation.deprecated_args(allowed_positional=0)
            def a_method(self, a=1, b=2):
                pass

        C().a_method(a=1, b=2)
        assert len(recwarn) == 0
        C().a_method(1, b=2)
        assert len(recwarn) == 1
        assert 'C.a_method(...)' in str(recwarn[0].message)

    def test_function(self, recwarn):
        @deprecation.deprecated_args(allowed_positional=0, is_method=False)
        def a_function(a=1, b=2):
            pass

        a_function(a=1, b=2)
        assert len(recwarn) == 0
        a_function(1, b=2)
        assert len(recwarn) == 1
        assert 'a_function(...)' in str(recwarn[0].message)


def test_TimezoneGMT():
    with pytest.warns(deprecation.DeprecatedWarning):
        tz = TimezoneGMT()

    z = timedelta(0)
    assert tz.tzname(None) == 'GMT'
    assert tz.dst(None) == z
    assert tz.utcoffset(None) == z
