from datetime import datetime, timedelta, tzinfo
import re

import pytest
from six.moves.http_cookies import Morsel

import falcon
import falcon.testing as testing
from falcon.util import http_date_to_dt, TimezoneGMT


UNICODE_TEST_STRING = u'Unicode_\xc3\xa6\xc3\xb8'


class TimezoneGMTPlus1(tzinfo):

    def utcoffset(self, dt):
        return timedelta(hours=1)

    def tzname(self, dt):
        return 'GMT+1'

    def dst(self, dt):
        return timedelta(hours=1)

GMT_PLUS_ONE = TimezoneGMTPlus1()


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
        e = datetime(year=2050, month=1, day=1, tzinfo=GMT_PLUS_ONE)  # aware
        resp.set_cookie('foo', 'bar', http_only=False, secure=False, expires=e)
        resp.unset_cookie('bad')


class CookieResourceMaxAgeFloatString:

    def on_get(self, req, resp):
        resp.set_cookie(
            'foofloat', 'bar', max_age=15.3, secure=False, http_only=False)
        resp.set_cookie(
            'foostring', 'bar', max_age='15', secure=False, http_only=False)


@pytest.fixture(scope='module')
def client():
    app = falcon.API()
    app.add_route('/', CookieResource())
    app.add_route('/test-convert', CookieResourceMaxAgeFloatString())

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

    cookie = result.cookies['bar']
    assert cookie.value == 'baz'
    assert cookie.domain is None
    assert cookie.expires is None
    assert not cookie.http_only
    assert cookie.max_age is None
    assert cookie.path is None
    assert cookie.secure

    cookie = result.cookies['bad']
    assert cookie.value == ''  # An unset cookie has an empty value
    assert cookie.domain is None

    assert cookie.expires < datetime.utcnow()

    # NOTE(kgriffs): I know accessing a private attr like this is
    # naughty of me, but we just need to sanity-check that the
    # string is GMT.
    assert cookie._expires.endswith('GMT')

    assert cookie.http_only
    assert cookie.max_age is None
    assert cookie.path is None
    assert cookie.secure


def test_cookie_expires_naive(client):
    result = client.simulate_post('/')

    cookie = result.cookies['foo']
    assert cookie.value == 'bar'
    assert cookie.domain is None
    assert cookie.expires == datetime(year=2050, month=1, day=1)
    assert not cookie.http_only
    assert cookie.max_age is None
    assert cookie.path is None
    assert not cookie.secure


def test_cookie_expires_aware(client):
    result = client.simulate_put('/')

    cookie = result.cookies['foo']
    assert cookie.value == 'bar'
    assert cookie.domain is None
    assert cookie.expires == datetime(year=2049, month=12, day=31, hour=23)
    assert not cookie.http_only
    assert cookie.max_age is None
    assert cookie.path is None
    assert not cookie.secure


def test_cookies_setable(client):
    resp = falcon.Response()

    assert resp._cookies is None

    resp.set_cookie('foo', 'wrong-cookie', max_age=301)
    resp.set_cookie('foo', 'bar', max_age=300)
    morsel = resp._cookies['foo']

    assert isinstance(morsel, Morsel)
    assert morsel.key == 'foo'
    assert morsel.value == 'bar'
    assert morsel['max-age'] == 300


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


def test_response_unset_cookie(client):
    resp = falcon.Response()
    resp.unset_cookie('bad')
    resp.set_cookie('bad', 'cookie', max_age=300)
    resp.unset_cookie('bad')

    morsels = list(resp._cookies.values())
    len(morsels) == 1

    bad_cookie = morsels[0]
    bad_cookie['expires'] == -1

    output = bad_cookie.OutputString()
    assert 'bad=;' in output or 'bad="";' in output

    match = re.search('expires=([^;]+)', output)
    assert match

    expiration = http_date_to_dt(match.group(1), obs_date=True)
    assert expiration < datetime.utcnow()


def test_cookie_timezone(client):
    tz = TimezoneGMT()
    assert tz.tzname(timedelta(0)) == 'GMT'


# =====================================================================
# Request
# =====================================================================


def test_request_cookie_parsing():
    # testing with a github-ish set of cookies
    headers = [
        (
            'Cookie',
            '''
            logged_in=no;_gh_sess=eyJzZXXzaW9uX2lkIjoiN2;
            tz=Europe/Berlin; _ga=GA1.2.332347814.1422308165;
            _gat=1;
            _octo=GH1.1.201722077.1422308165
            '''
        ),
    ]

    environ = testing.create_environ(headers=headers)
    req = falcon.Request(environ)

    assert req.cookies['logged_in'] == 'no'
    assert req.cookies['tz'] == 'Europe/Berlin'
    assert req.cookies['_octo'] == 'GH1.1.201722077.1422308165'

    assert 'logged_in' in req.cookies
    assert '_gh_sess' in req.cookies
    assert 'tz' in req.cookies
    assert '_ga' in req.cookies
    assert '_gat' in req.cookies
    assert '_octo' in req.cookies


def test_unicode_inside_ascii_range():
    resp = falcon.Response()

    # should be ok
    resp.set_cookie('non_unicode_ascii_name_1', 'ascii_value')
    resp.set_cookie(u'unicode_ascii_name_1', 'ascii_value')
    resp.set_cookie('non_unicode_ascii_name_2', u'unicode_ascii_value')
    resp.set_cookie(u'unicode_ascii_name_2', u'unicode_ascii_value')


@pytest.mark.parametrize(
    'name',
    (
        UNICODE_TEST_STRING,
        UNICODE_TEST_STRING.encode('utf-8'),
        42
    )
)
def test_non_ascii_name(name):
    resp = falcon.Response()
    with pytest.raises(KeyError):
        resp.set_cookie(name, 'ok_value')


@pytest.mark.parametrize(
    'value',
    (
        UNICODE_TEST_STRING,
        UNICODE_TEST_STRING.encode('utf-8'),
        42
    )
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
