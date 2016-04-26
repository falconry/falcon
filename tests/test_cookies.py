import re
import sys
from datetime import datetime, timedelta, tzinfo

import ddt
from six.moves.http_cookies import Morsel
from testtools.matchers import LessThan

import falcon
import falcon.testing as testing
from falcon.util import TimezoneGMT, http_date_to_dt


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


@ddt.ddt
class TestCookies(testing.TestBase):

    #
    # Response
    #

    def test_response_base_case(self):
        self.resource = CookieResource()
        self.api.add_route(self.test_route, self.resource)
        self.simulate_request(self.test_route, method='GET')
        if sys.version_info >= (3, 4, 3):
            value = 'foo=bar; Domain=example.com; HttpOnly; Path=/; Secure'
        else:
            value = 'foo=bar; Domain=example.com; httponly; Path=/; secure'
        self.assertIn(('set-cookie', value), self.srmock.headers)

    def test_response_complex_case(self):
        self.resource = CookieResource()
        self.api.add_route(self.test_route, self.resource)
        self.simulate_request(self.test_route, method='HEAD')
        if sys.version_info >= (3, 4, 3):
            value = 'foo=bar; HttpOnly; Max-Age=300; Secure'
        else:
            value = 'foo=bar; httponly; Max-Age=300; secure'
        self.assertIn(('set-cookie', value), self.srmock.headers)
        if sys.version_info >= (3, 4, 3):
            value = 'bar=baz; Secure'
        else:
            value = 'bar=baz; secure'
        self.assertIn(('set-cookie', value), self.srmock.headers)
        self.assertNotIn(('set-cookie', 'bad=cookie'), self.srmock.headers)

    def test_cookie_expires_naive(self):
        self.resource = CookieResource()
        self.api.add_route(self.test_route, self.resource)
        self.simulate_request(self.test_route, method='POST')
        self.assertIn(
            ('set-cookie', 'foo=bar; expires=Sat, 01 Jan 2050 00:00:00 GMT'),
            self.srmock.headers)

    def test_cookie_expires_aware(self):
        self.resource = CookieResource()
        self.api.add_route(self.test_route, self.resource)
        self.simulate_request(self.test_route, method='PUT')
        self.assertIn(
            ('set-cookie', 'foo=bar; expires=Fri, 31 Dec 2049 23:00:00 GMT'),
            self.srmock.headers)

    def test_cookies_setable(self):
        resp = falcon.Response()

        self.assertIsNone(resp._cookies)

        resp.set_cookie('foo', 'wrong-cookie', max_age=301)
        resp.set_cookie('foo', 'bar', max_age=300)
        morsel = resp._cookies['foo']

        self.assertIsInstance(morsel, Morsel)
        self.assertEqual(morsel.key, 'foo')
        self.assertEqual(morsel.value, 'bar')
        self.assertEqual(morsel['max-age'], 300)

    def test_cookie_max_age_float_and_string(self):
        # Falcon implicitly converts max-age values to integers,
        # for ensuring RFC 6265-compliance of the attribute value.
        self.resource = CookieResourceMaxAgeFloatString()
        self.api.add_route(self.test_route, self.resource)
        self.simulate_request(self.test_route, method='GET')
        self.assertIn(
            ('set-cookie', 'foofloat=bar; Max-Age=15'), self.srmock.headers)
        self.assertIn(
            ('set-cookie', 'foostring=bar; Max-Age=15'), self.srmock.headers)

    def test_response_unset_cookie(self):
        resp = falcon.Response()
        resp.unset_cookie('bad')
        resp.set_cookie('bad', 'cookie', max_age=300)
        resp.unset_cookie('bad')

        morsels = list(resp._cookies.values())
        self.assertEqual(len(morsels), 1)

        bad_cookie = morsels[0]
        self.assertEqual(bad_cookie['expires'], -1)

        output = bad_cookie.OutputString()
        self.assertTrue('bad=;' in output or 'bad="";' in output)

        match = re.search('expires=([^;]+)', output)
        self.assertIsNotNone(match)

        expiration = http_date_to_dt(match.group(1), obs_date=True)
        self.assertThat(expiration, LessThan(datetime.utcnow()))

    def test_cookie_timezone(self):
        tz = TimezoneGMT()
        self.assertEqual('GMT', tz.tzname(timedelta(0)))

    #
    # Request
    #

    def test_request_cookie_parsing(self):
        # testing with a github-ish set of cookies
        headers = [
            ('Cookie', '''
                logged_in=no;_gh_sess=eyJzZXXzaW9uX2lkIjoiN2;
                tz=Europe/Berlin; _ga=GA1.2.332347814.1422308165;
                _gat=1;
                _octo=GH1.1.201722077.1422308165'''),
        ]

        environ = testing.create_environ(headers=headers)
        req = falcon.Request(environ)

        self.assertEqual('no', req.cookies['logged_in'])
        self.assertEqual('Europe/Berlin', req.cookies['tz'])
        self.assertEqual('GH1.1.201722077.1422308165', req.cookies['_octo'])

        self.assertIn('logged_in', req.cookies)
        self.assertIn('_gh_sess', req.cookies)
        self.assertIn('tz', req.cookies)
        self.assertIn('_ga', req.cookies)
        self.assertIn('_gat', req.cookies)
        self.assertIn('_octo', req.cookies)

    def test_unicode_inside_ascii_range(self):
        resp = falcon.Response()

        # should be ok
        resp.set_cookie('non_unicode_ascii_name_1', 'ascii_value')
        resp.set_cookie(u'unicode_ascii_name_1', 'ascii_value')
        resp.set_cookie('non_unicode_ascii_name_2', u'unicode_ascii_value')
        resp.set_cookie(u'unicode_ascii_name_2', u'unicode_ascii_value')

    @ddt.data(
        UNICODE_TEST_STRING,
        UNICODE_TEST_STRING.encode('utf-8'),
        42
    )
    def test_non_ascii_name(self, name):
        resp = falcon.Response()
        self.assertRaises(KeyError, resp.set_cookie,
                          name, 'ok_value')

    @ddt.data(
        UNICODE_TEST_STRING,
        UNICODE_TEST_STRING.encode('utf-8'),
        42
    )
    def test_non_ascii_value(self, value):
        resp = falcon.Response()

        # NOTE(tbug): we need to grab the exception to check
        # that it is not instance of UnicodeEncodeError, so
        # we cannot simply use assertRaises
        try:
            resp.set_cookie('ok_name', value)
        except ValueError as e:
            self.assertIsInstance(e, ValueError)
            self.assertNotIsInstance(e, UnicodeEncodeError)
        else:
            self.fail('set_bad_cookie_value did not fail as expected')
