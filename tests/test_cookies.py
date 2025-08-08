from datetime import datetime
from datetime import timedelta
from datetime import timezone
from http import cookies as http_cookies
import re
import warnings

import pytest

import falcon
import falcon.testing as testing
from falcon.util import http_date_to_dt
from falcon.util.deprecation import DeprecatedWarning
from falcon.util.misc import _utcnow

UNICODE_TEST_STRING = 'Unicode_\xc3\xa6\xc3\xb8'


def utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CookieResource:
    def on_get(self, req, resp):
        resp.set_cookie('foo', 'bar', domain='example.com', path='/')

    def on_head(self, req, resp):
        resp.set_cookie('foo', 'bar', max_age=300)
        resp.set_cookie('bar', 'baz', http_only=False)
        resp.set_cookie('bad', 'cookie')
        resp.unset_cookie('bad')

    def on_post(self, req, resp):
        e = datetime(year=2050, month=1, day=1)  # naive
        resp.set_cookie('foo', 'bar', http_only=False, secure=False, expires=e)
        resp.unset_cookie('bad')

    def on_put(self, req, resp):
        e = datetime(
            year=2050, month=1, day=1, tzinfo=timezone(timedelta(hours=1))
        )  # aware
        resp.set_cookie('foo', 'bar', http_only=False, secure=False, expires=e)
        resp.unset_cookie('bad')


class CookieResourceMaxAgeFloatString:
    def on_get(self, req, resp):
        resp.set_cookie('foofloat', 'bar', max_age=15.3, secure=False, http_only=False)
        resp.set_cookie('foostring', 'bar', max_age='15', secure=False, http_only=False)


class CookieResourceSameSite:
    def on_get(self, req, resp):
        resp.set_cookie('foo', 'bar', same_site='Lax')
        resp.set_cookie('barz', 'barz', same_site='')

    def on_post(self, req, resp):
        resp.set_cookie('bar', 'foo', same_site='STRICT')

    def on_put(self, req, resp):
        resp.set_cookie('baz', 'foo', same_site='none')

    def on_delete(self, req, resp):
        resp.set_cookie('baz', 'foo', same_site='')


class CookieResourcePartitioned:
    def on_get(self, req, resp):
        resp.set_cookie('foo', 'bar', secure=True, partitioned=True)
        resp.set_cookie('bar', 'baz', secure=True, partitioned=False)
        resp.set_cookie('baz', 'foo', secure=True)


class CookieUnset:
    def on_get(self, req, resp):
        resp.unset_cookie('foo')
        resp.unset_cookie('bar', path='/bar')
        resp.unset_cookie('baz', domain='www.example.com')
        resp.unset_cookie('foobar', path='/foo', domain='www.example.com')
        resp.unset_cookie(
            'barfoo', same_site='none', path='/foo', domain='www.example.com'
        )


class CookieUnsetSameSite:
    def on_get(self, req, resp):
        # change lax to strict
        resp.unset_cookie('foo', same_site='Strict')
        # change strict to lax
        resp.unset_cookie('bar')
        # change none to ''
        resp.unset_cookie('baz', same_site='')
        # change '' to none
        resp.unset_cookie('barz', same_site='None')


@pytest.fixture
def client(asgi, util):
    app = util.create_app(asgi)
    app.add_route('/', CookieResource())
    app.add_route('/test-convert', CookieResourceMaxAgeFloatString())
    app.add_route('/same-site', CookieResourceSameSite())
    app.add_route('/partitioned', CookieResourcePartitioned())
    app.add_route('/unset-cookie', CookieUnset())
    app.add_route('/unset-cookie-same-site', CookieUnsetSameSite())

    return testing.TestClient(app)


# =====================================================================
# Response
# =====================================================================


def test_response_base_case(client):
    result = client.simulate_get('/')

    cookie = result.cookies['foo']

    assert cookie.name == 'foo'
    assert cookie.value == 'bar'
    assert cookie.domain == 'example.com'
    assert cookie.http_only

    # NOTE(kgriffs): Explicitly test for None to ensure
    # falcon.testing.Cookie is returning exactly what we
    # expect. Apps using falcon.testing.Cookie can be a
    # bit more cavalier if they wish.
    assert cookie.max_age is None
    assert cookie.expires is None

    assert cookie.path == '/'
    assert cookie.secure


def test_response_disable_secure_globally(client):
    client.app.resp_options.secure_cookies_by_default = False
    result = client.simulate_get('/')
    cookie = result.cookies['foo']
    assert not cookie.secure

    client.app.resp_options.secure_cookies_by_default = True
    result = client.simulate_get('/')
    cookie = result.cookies['foo']
    assert cookie.secure


def test_response_complex_case(client):
    result = client.simulate_head('/')

    assert len(result.cookies) == 3

    cookie = result.cookies['foo']
    assert cookie.value == 'bar'
    assert cookie.domain is None
    assert cookie.expires is None
    assert cookie.http_only
    assert cookie.max_age == 300
    assert cookie.path is None
    assert cookie.secure
    assert not cookie.partitioned

    cookie = result.cookies['bar']
    assert cookie.value == 'baz'
    assert cookie.domain is None
    assert cookie.expires is None
    assert not cookie.http_only
    assert cookie.max_age is None
    assert cookie.path is None
    assert cookie.secure
    assert not cookie.partitioned

    cookie = result.cookies['bad']
    assert cookie.value == ''  # An unset cookie has an empty value
    assert cookie.domain is None
    assert cookie.same_site == 'Lax'

    assert cookie.expires < _utcnow()

    # NOTE(kgriffs): I know accessing a private attr like this is
    # naughty of me, but we just need to sanity-check that the
    # string is GMT.
    assert cookie._expires.endswith('GMT')

    assert cookie.http_only
    assert cookie.max_age is None
    assert cookie.path is None
    assert cookie.secure


def test_unset_cookies(client):
    result = client.simulate_get('/unset-cookie')
    assert len(result.cookies) == 5

    def test(cookie, path, domain, same_site='Lax'):
        assert cookie.value == ''  # An unset cookie has an empty value
        assert cookie.domain == domain
        assert cookie.path == path
        assert cookie.same_site == same_site
        assert cookie.expires < _utcnow()

    test(result.cookies['foo'], path=None, domain=None)
    test(result.cookies['bar'], path='/bar', domain=None)
    test(result.cookies['baz'], path=None, domain='www.example.com')
    test(result.cookies['foobar'], path='/foo', domain='www.example.com')
    test(
        result.cookies['barfoo'],
        path='/foo',
        domain='www.example.com',
        same_site='none',
    )


def test_unset_cookies_samesite(client):
    # Test possible different samesite values in set_cookies
    # foo, bar, lax
    result_set_lax_empty = client.simulate_get('/same-site')
    # bar, foo, strict
    result_set_strict = client.simulate_post('/same-site')
    # baz, foo, none
    result_set_none = client.simulate_put('/same-site')

    def test_set(cookie, value, samesite=None):
        assert cookie.value == value
        assert cookie.same_site == samesite

    test_set(result_set_lax_empty.cookies['foo'], 'bar', samesite='Lax')
    test_set(result_set_strict.cookies['bar'], 'foo', samesite='Strict')
    test_set(result_set_none.cookies['baz'], 'foo', samesite='None')
    # barz gets set with '', that is None value
    test_set(result_set_lax_empty.cookies['barz'], 'barz')
    test_set(result_set_lax_empty.cookies['barz'], 'barz', samesite=None)

    # Unset the cookies with different samesite values
    result_unset = client.simulate_get('/unset-cookie-same-site')
    assert len(result_unset.cookies) == 4

    def test_unset(cookie, same_site='Lax'):
        assert cookie.value == ''  # An unset cookie has an empty value
        assert cookie.same_site == same_site
        assert cookie.expires < _utcnow()

    test_unset(result_unset.cookies['foo'], same_site='Strict')
    # default: bar is unset with no same_site param, so should go to Lax
    test_unset(result_unset.cookies['bar'], same_site='Lax')
    test_unset(result_unset.cookies['bar'])  # default in test_unset

    test_unset(
        result_unset.cookies['baz'], same_site=None
    )  # baz gets unset to same_site = ''
    test_unset(result_unset.cookies['barz'], same_site='None')
    # test for false
    assert result_unset.cookies['baz'].same_site != 'Strict'
    assert result_unset.cookies['foo'].same_site != 'Lax'
    assert not result_unset.cookies['baz'].same_site


def test_cookie_expires_naive(client):
    result = client.simulate_post('/')

    cookie = result.cookies['foo']
    assert cookie.value == 'bar'
    assert cookie.domain is None
    assert cookie.expires == datetime(year=2050, month=1, day=1, tzinfo=timezone.utc)
    assert not cookie.http_only
    assert cookie.max_age is None
    assert cookie.path is None
    assert not cookie.secure


def test_cookie_expires_aware(client):
    result = client.simulate_put('/')

    cookie = result.cookies['foo']
    assert cookie.value == 'bar'
    assert cookie.domain is None
    assert cookie.expires == datetime(
        year=2049, month=12, day=31, hour=23, tzinfo=timezone.utc
    )
    assert not cookie.http_only
    assert cookie.max_age is None
    assert cookie.path is None
    assert not cookie.secure


def test_cookies_setable():
    resp = falcon.Response()

    assert resp._cookies is None

    resp.set_cookie('foo', 'wrong-cookie', max_age=301)
    resp.set_cookie('foo', 'bar', max_age=300)
    resp.set_cookie('bar', 'baz', same_site='None', partitioned=True)

    morsel1 = resp._cookies['foo']
    morsel2 = resp._cookies['bar']

    assert isinstance(morsel1, http_cookies.Morsel)
    assert morsel1.key == 'foo'
    assert morsel1.value == 'bar'
    assert morsel1['max-age'] == 300

    assert isinstance(morsel2, http_cookies.Morsel)
    assert morsel2.key == 'bar'
    assert morsel2.value == 'baz'
    assert morsel2['partitioned'] is True
    assert morsel2.output() == (
        'Set-Cookie: bar=baz; HttpOnly; Partitioned; SameSite=None; Secure'
    )


@pytest.mark.parametrize('cookie_name', ('foofloat', 'foostring'))
def test_cookie_max_age_float_and_string(client, cookie_name):
    # NOTE(tbug): Falcon implicitly converts max-age values to integers,
    # to ensure RFC 6265-compliance of the attribute value.

    result = client.simulate_get('/test-convert')

    cookie = result.cookies[cookie_name]
    assert cookie.value == 'bar'
    assert cookie.domain is None
    assert cookie.expires is None
    assert not cookie.http_only
    assert cookie.max_age == 15
    assert cookie.path is None
    assert not cookie.secure


def test_response_unset_cookie():
    resp = falcon.Response()
    resp.unset_cookie('bad')
    resp.set_cookie('bad', 'cookie', max_age=300)
    resp.unset_cookie('bad')

    morsels = list(resp._cookies.values())
    assert len(morsels) == 1

    bad_cookie = morsels[0]
    assert bad_cookie['expires'] == -1

    output = bad_cookie.OutputString()
    assert 'bad=;' in output or 'bad="";' in output

    match = re.search('expires=([^;]+)', output)
    assert match

    expiration = http_date_to_dt(match.group(1), obs_date=True)
    assert expiration < _utcnow()


# =====================================================================
# Request
# =====================================================================


def test_request_cookie_parsing():
    # testing with a github-ish set of cookies
    headers = [
        (
            'Cookie',
            """
            logged_in=no;_gh_sess=eyJzZXXzaW9uX2lkIjoiN2;
            tz=Europe/Berlin; _ga =GA1.2.332347814.1422308165;
            tz2=Europe/Paris ; _ga2="line1\\012line2";
            tz3=Europe/Madrid ;_ga3= GA3.2.332347814.1422308165;
            _gat=1;
            _octo=GH1.1.201722077.1422308165
            """,
        ),
    ]

    environ = testing.create_environ(headers=headers)
    req = falcon.Request(environ)

    # NOTE(kgriffs): Test case-sensitivity
    assert req.get_cookie_values('TZ') is None
    assert 'TZ' not in req.cookies
    with pytest.raises(KeyError):
        req.cookies['TZ']

    for name, value in [
        ('logged_in', 'no'),
        ('_gh_sess', 'eyJzZXXzaW9uX2lkIjoiN2'),
        ('tz', 'Europe/Berlin'),
        ('tz2', 'Europe/Paris'),
        ('tz3', 'Europe/Madrid'),
        ('_ga', 'GA1.2.332347814.1422308165'),
        ('_ga2', 'line1\nline2'),
        ('_ga3', 'GA3.2.332347814.1422308165'),
        ('_gat', '1'),
        ('_octo', 'GH1.1.201722077.1422308165'),
    ]:
        assert name in req.cookies
        assert req.cookies[name] == value
        assert req.get_cookie_values(name) == [value]


def test_invalid_cookies_are_ignored():
    vals = [chr(i) for i in range(0x1F)]
    vals += [chr(i) for i in range(0x7F, 0xFF)]
    vals += '()<>@,;:\\"/[]?={} \x09'.split()

    for c in vals:
        headers = [
            ('Cookie', 'good_cookie=foo;bad' + c + 'cookie=bar'),
        ]

        environ = testing.create_environ(headers=headers)
        req = falcon.Request(environ)

        assert req.cookies['good_cookie'] == 'foo'
        assert 'bad' + c + 'cookie' not in req.cookies


def test_duplicate_cookie():
    headers = [
        ('Cookie', 'x=1;bad{cookie=bar; x=2;x=3 ; x=4;'),
    ]

    environ = testing.create_environ(headers=headers)
    req = falcon.Request(environ)

    assert req.cookies['x'] == '1'
    assert req.get_cookie_values('x') == ['1', '2', '3', '4']


def test_cookie_header_is_missing():
    environ = testing.create_environ(headers={})

    req = falcon.Request(environ)
    assert req.cookies == {}
    assert req.get_cookie_values('x') is None

    # NOTE(kgriffs): Test again with a new object to cover calling in the
    #   opposite order.
    req = falcon.Request(environ)
    assert req.get_cookie_values('x') is None
    assert req.cookies == {}


def test_unicode_inside_ascii_range():
    resp = falcon.Response()

    # should be ok
    resp.set_cookie('non_unicode_ascii_name_1', 'ascii_value')
    resp.set_cookie('unicode_ascii_name_1', 'ascii_value')
    resp.set_cookie('non_unicode_ascii_name_2', 'unicode_ascii_value')
    resp.set_cookie('unicode_ascii_name_2', 'unicode_ascii_value')


@pytest.mark.parametrize(
    'name', (UNICODE_TEST_STRING, UNICODE_TEST_STRING.encode('utf-8'), 42)
)
def test_non_ascii_name(name):
    resp = falcon.Response()
    with pytest.raises(KeyError):
        resp.set_cookie(name, 'ok_value')


@pytest.mark.parametrize(
    'value', (UNICODE_TEST_STRING, UNICODE_TEST_STRING.encode('utf-8'), 42)
)
def test_non_ascii_value(value):
    resp = falcon.Response()

    # NOTE(tbug): we need to grab the exception to check
    # that it is not instance of UnicodeEncodeError, so
    # we cannot simply use pytest.raises
    try:
        resp.set_cookie('ok_name', value)
    except ValueError as e:
        assert isinstance(e, ValueError)
        assert not isinstance(e, UnicodeEncodeError)
    else:
        pytest.fail('set_bad_cookie_value did not fail as expected')


def test_lax_same_site_value(client):
    result = client.simulate_get('/same-site')
    cookie = result.cookies['foo']

    assert cookie.same_site == 'Lax'


def test_strict_same_site_value(client):
    result = client.simulate_post('/same-site')
    cookie = result.cookies['bar']

    assert cookie.same_site == 'Strict'


def test_none_same_site_value(client):
    result = client.simulate_put('/same-site')
    cookie = result.cookies['baz']

    assert cookie.same_site == 'None'


def test_same_site_empty_string(client):
    result = client.simulate_delete('/same-site')
    cookie = result.cookies['baz']

    assert cookie.same_site is None


@pytest.mark.parametrize(
    'same_site', ['laX', 'lax', 'STRICT', 'strict', 'None', 'none']
)
def test_same_site_value_case_insensitive(same_site):
    resp = falcon.Response()
    resp.set_cookie('foo', 'bar', same_site=same_site)

    # NOTE(kgriffs): Verify directly, unit-test style, since we
    #   already tested end-to-end above.
    morsel = resp._cookies['foo']
    assert morsel['samesite'].lower() == same_site.lower()


@pytest.mark.parametrize('same_site', ['bogus', 'laxx', 'stric'])
def test_invalid_same_site_value(same_site):
    resp = falcon.Response()

    with pytest.raises(ValueError):
        resp.set_cookie('foo', 'bar', same_site=same_site)


def test_partitioned_value(client):
    result = client.simulate_get('/partitioned')

    cookie = result.cookies['foo']
    assert cookie.partitioned

    cookie = result.cookies['bar']
    assert not cookie.partitioned

    cookie = result.cookies['baz']
    assert not cookie.partitioned


def test_unset_cookie_deprecation_warning():
    resp = falcon.Response()

    # Test that using the deprecated 'samesite' parameter raises a warning
    with pytest.warns(
        DeprecatedWarning, match='The "samesite" parameter is deprecated'
    ):
        resp.unset_cookie('test', samesite='Strict')

    # Verify the cookie was still set correctly with the deprecated parameter
    morsel = resp._cookies['test']
    assert morsel['samesite'] == 'Strict'

    # Test that using the new 'same_site' parameter doesn't raise a warning
    with warnings.catch_warnings():
        warnings.simplefilter('error')
        resp.unset_cookie('test2', same_site='Lax')

    # Verify the cookie was set correctly with the new parameter
    morsel2 = resp._cookies['test2']
    assert morsel2['samesite'] == 'Lax'

    # Test that when both parameters are provided, deprecated one is used with warning
    with pytest.warns(
        DeprecatedWarning, match='The "samesite" parameter is deprecated'
    ):
        resp.unset_cookie('test3', samesite='None', same_site='Strict')

    # Verify the deprecated parameter value was used
    morsel3 = resp._cookies['test3']
    assert morsel3['samesite'] == 'None'
