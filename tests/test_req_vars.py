import datetime

import falcon
from falcon.request import Request
import falcon.testing as testing


class TestReqVars(testing.TestBase):

    def before(self):
        self.qs = 'marker=deadbeef&limit=10'

        self.headers = {
            'Host': 'falcon.example.com',
            'Content-Type': 'text/plain',
            'Content-Length': '4829',
            'Authorization': ''
        }

        self.app = '/test'
        self.path = '/hello'
        self.relative_uri = self.path + '?' + self.qs
        self.uri = 'http://falcon.example.com' + self.app + self.relative_uri
        self.uri_noqs = 'http://falcon.example.com' + self.app + self.path

        self.req = Request(testing.create_environ(
            app=self.app,
            path='/hello',
            query_string=self.qs,
            headers=self.headers))

        self.req_noqs = Request(testing.create_environ(
            app=self.app,
            path='/hello',
            headers=self.headers))

    def test_missing_qs(self):
        env = testing.create_environ()
        if 'QUERY_STRING' in env:
            del env['QUERY_STRING']

        # Should not cause an exception when Request is instantiated
        Request(env)

    def test_empty(self):
        self.assertIs(self.req.auth, None)

    def test_reconstruct_url(self):
        req = self.req

        scheme = req.protocol
        host = req.get_header('host')
        app = req.app
        path = req.path
        query_string = req.query_string

        actual_url = ''.join([scheme, '://', host, app, path,
                              '?', query_string])
        self.assertEqual(actual_url, self.uri)

    def test_uri(self):
        self.assertEqual(self.req.url, self.uri)

        # NOTE(kgriffs): Call twice to check caching works
        self.assertEqual(self.req.uri, self.uri)
        self.assertEqual(self.req.uri, self.uri)

        self.assertEqual(self.req_noqs.uri, self.uri_noqs)

    def test_relative_uri(self):
        self.assertEqual(self.req.relative_uri, self.app + self.relative_uri)
        self.assertEqual(
            self.req_noqs.relative_uri, self.app + self.path)

        req_noapp = Request(testing.create_environ(
            path='/hello',
            query_string=self.qs,
            headers=self.headers))

        self.assertEqual(req_noapp.relative_uri, self.relative_uri)

        req_noapp = Request(testing.create_environ(
            path='/hello/',
            query_string=self.qs,
            headers=self.headers))

        # NOTE(kgriffs): Call twice to check caching works
        self.assertEqual(req_noapp.relative_uri, self.relative_uri)
        self.assertEqual(req_noapp.relative_uri, self.relative_uri)

    def test_client_accepts(self):
        headers = {'Accept': 'application/xml'}
        req = Request(testing.create_environ(headers=headers))
        self.assertTrue(req.client_accepts('application/xml'))

        headers = {'Accept': '*/*'}
        req = Request(testing.create_environ(headers=headers))
        self.assertTrue(req.client_accepts('application/xml'))

        headers = {}  # NOTE(kgriffs): Equivalent to '*/*' per RFC
        req = Request(testing.create_environ(headers=headers))
        self.assertTrue(req.client_accepts('application/xml'))

        headers = {'Accept': 'application/json'}
        req = Request(testing.create_environ(headers=headers))
        self.assertFalse(req.client_accepts('application/xml'))

        headers = {'Accept': 'application/xm'}
        req = Request(testing.create_environ(headers=headers))
        self.assertFalse(req.client_accepts('application/xml'))

        headers = {'Accept': 'application/*'}
        req = Request(testing.create_environ(headers=headers))
        self.assertTrue(req.client_accepts('application/json'))
        self.assertTrue(req.client_accepts('application/xml'))

        headers = {'Accept': 'text/*'}
        req = Request(testing.create_environ(headers=headers))
        self.assertTrue(req.client_accepts('text/plain'))
        self.assertTrue(req.client_accepts('text/csv'))
        self.assertFalse(req.client_accepts('application/xhtml+xml'))

        headers = {'Accept': 'text/*, application/xhtml+xml; q=0.0'}
        req = Request(testing.create_environ(headers=headers))
        self.assertTrue(req.client_accepts('text/plain'))
        self.assertTrue(req.client_accepts('text/csv'))
        self.assertTrue(req.client_accepts('application/xhtml+xml'))

        headers = {'Accept': 'text/*; q=0.1, application/xhtml+xml; q=0.5'}
        req = Request(testing.create_environ(headers=headers))
        self.assertTrue(req.client_accepts('text/plain'))

        headers = {'Accept': 'text/*,         application/*'}
        req = Request(testing.create_environ(headers=headers))
        self.assertTrue(req.client_accepts('text/plain'))
        self.assertTrue(req.client_accepts('application/json'))

        headers = {'Accept': 'text/*,application/*'}
        req = Request(testing.create_environ(headers=headers))
        self.assertTrue(req.client_accepts('text/plain'))
        self.assertTrue(req.client_accepts('application/json'))

    def test_client_accepts_props(self):
        headers = {'Accept': 'application/xml'}
        req = Request(testing.create_environ(headers=headers))
        self.assertTrue(req.client_accepts_xml)
        self.assertFalse(req.client_accepts_json)

        headers = {'Accept': 'application/*'}
        req = Request(testing.create_environ(headers=headers))
        self.assertTrue(req.client_accepts_xml)

        headers = {'Accept': 'application/json'}
        req = Request(testing.create_environ(headers=headers))
        self.assertFalse(req.client_accepts_xml)
        self.assertTrue(req.client_accepts_json)

        headers = {'Accept': 'application/json, application/xml'}
        req = Request(testing.create_environ(headers=headers))
        self.assertTrue(req.client_accepts_xml)
        self.assertTrue(req.client_accepts_json)

    def test_client_prefers(self):
        headers = {'Accept': 'application/xml'}
        req = Request(testing.create_environ(headers=headers))
        preferred_type = req.client_prefers(['application/xml'])
        self.assertEqual(preferred_type, 'application/xml')

        headers = {'Accept': '*/*'}
        preferred_type = req.client_prefers(('application/xml',
                                             'application/json'))

        # NOTE(kgriffs): If client doesn't care, "preferr" the first one
        self.assertEqual(preferred_type, 'application/xml')

        headers = {'Accept': 'text/*; q=0.1, application/xhtml+xml; q=0.5'}
        req = Request(testing.create_environ(headers=headers))
        preferred_type = req.client_prefers(['application/xhtml+xml'])
        self.assertEqual(preferred_type, 'application/xhtml+xml')

        headers = {'Accept': '3p12845j;;;asfd;'}
        req = Request(testing.create_environ(headers=headers))
        preferred_type = req.client_prefers(['application/xhtml+xml'])
        self.assertEqual(preferred_type, None)

    def test_range(self):
        headers = {'Range': '10-'}
        req = Request(testing.create_environ(headers=headers))
        self.assertEqual(req.range, (10, -1))

        headers = {'Range': '10-20'}
        req = Request(testing.create_environ(headers=headers))
        self.assertEqual(req.range, (10, 20))

        headers = {'Range': '-10240'}
        req = Request(testing.create_environ(headers=headers))
        self.assertEqual(req.range, (-10240, -1))

        headers = {'Range': ''}
        req = Request(testing.create_environ(headers=headers))
        self.assertIs(req.range, None)

        req = Request(testing.create_environ())
        self.assertIs(req.range, None)

    def test_range_invalid(self):
        headers = {'Range': '10240'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.range)

        headers = {'Range': '-'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.range)

        headers = {'Range': '--'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.range)

        headers = {'Range': '-3-'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.range)

        headers = {'Range': '-3-4'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.range)

        headers = {'Range': '3-3-4'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.range)

        headers = {'Range': '3-3-'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.range)

        headers = {'Range': '3-3- '}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.range)

        headers = {'Range': 'fizbit'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.range)

        headers = {'Range': 'a-'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.range)

        headers = {'Range': 'a-3'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.range)

        headers = {'Range': '-b'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.range)

        headers = {'Range': '3-b'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.range)

        headers = {'Range': 'x-y'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.range)

        headers = {'Range': 'bytes=0-0,-1'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.range)

    def test_missing_attribute_header(self):
        req = Request(testing.create_environ())
        self.assertEqual(req.range, None)

        req = Request(testing.create_environ())
        self.assertEqual(req.content_length, None)

    def test_content_length(self):
        headers = {'content-length': '5656'}
        req = Request(testing.create_environ(headers=headers))
        self.assertEqual(req.content_length, 5656)

        headers = {'content-length': ''}
        req = Request(testing.create_environ(headers=headers))
        self.assertEqual(req.content_length, None)

    def test_bogus_content_length_nan(self):
        headers = {'content-length': 'fuzzy-bunnies'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.content_length)

    def test_bogus_content_length_neg(self):
        headers = {'content-length': '-1'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.content_length)

    def test_date(self):
        date = datetime.datetime(2013, 4, 4, 5, 19, 18)
        headers = {'date': 'Thu, 04 Apr 2013 05:19:18 GMT'}
        req = Request(testing.create_environ(headers=headers))
        self.assertEqual(req.date, date)

    def test_date_invalid(self):
        headers = {'date': 'Thu, 04 Apr 2013'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.date)

    def test_attribute_headers(self):
        date = testing.httpnow()
        hash = 'fa0d1a60ef6616bb28038515c8ea4cb2'
        auth = 'HMAC_SHA1 c590afa9bb59191ffab30f223791e82d3fd3e3af'
        agent = 'testing/1.0.1'
        default_agent = 'curl/7.24.0 (x86_64-apple-darwin12.0)'

        self._test_attribute_header('Accept', 'x-falcon', 'accept',
                                    default='*/*')

        self._test_attribute_header('Authorization', auth, 'auth')

        self._test_attribute_header('Content-Type', 'text/plain',
                                    'content_type')
        self._test_attribute_header('Expect', '100-continue', 'expect')

        self._test_attribute_header('If-Match', hash, 'if_match')
        self._test_attribute_header('If-Modified-Since', date,
                                    'if_modified_since')
        self._test_attribute_header('If-None-Match', hash, 'if_none_match')
        self._test_attribute_header('If-Range', hash, 'if_range')
        self._test_attribute_header('If-Unmodified-Since', date,
                                    'if_unmodified_since')

        self._test_attribute_header('User-Agent', agent, 'user_agent',
                                    default=default_agent)

    def test_method(self):
        self.assertEqual(self.req.method, 'GET')

        self.req = Request(testing.create_environ(path='', method='HEAD'))
        self.assertEqual(self.req.method, 'HEAD')

    def test_empty_path(self):
        self.req = Request(testing.create_environ(path=''))
        self.assertEqual(self.req.path, '/')

    def test_content_type_method(self):
        self.assertEqual(self.req.get_header('content-type'), 'text/plain')

    def test_content_length_method(self):
        self.assertEqual(self.req.get_header('content-length'), '4829')

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _test_attribute_header(self, name, value, attr, default=None):
        headers = {name: value}
        req = Request(testing.create_environ(headers=headers))
        self.assertEqual(getattr(req, attr), value)

        req = Request(testing.create_environ())
        self.assertEqual(getattr(req, attr), default)
