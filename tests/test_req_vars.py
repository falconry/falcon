import datetime

import ddt
import six
import testtools

import falcon
from falcon.request import Request
import falcon.testing as testing
import falcon.uri


@ddt.ddt
class TestReqVars(testing.TestBase):

    def before(self):
        self.qs = 'marker=deadbeef&limit=10'

        self.headers = {
            'Content-Type': 'text/plain',
            'Content-Length': '4829',
            'Authorization': ''
        }

        self.app = '/test'
        self.path = '/hello'
        self.relative_uri = self.path + '?' + self.qs

        self.req = Request(testing.create_environ(
            app=self.app,
            port=8080,
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

    def test_host(self):
        self.assertEqual(self.req.host, testing.DEFAULT_HOST)

    def test_subdomain(self):
        req = Request(testing.create_environ(
            host='com',
            path='/hello',
            headers=self.headers))
        self.assertIs(req.subdomain, None)

        req = Request(testing.create_environ(
            host='example.com',
            path='/hello',
            headers=self.headers))
        self.assertEqual(req.subdomain, 'example')

        req = Request(testing.create_environ(
            host='highwire.example.com',
            path='/hello',
            headers=self.headers))
        self.assertEqual(req.subdomain, 'highwire')

        req = Request(testing.create_environ(
            host='lb01.dfw01.example.com',
            port=8080,
            path='/hello',
            headers=self.headers))
        self.assertEqual(req.subdomain, 'lb01')

        # NOTE(kgriffs): Behavior for IP addresses is undefined,
        # so just make sure it doesn't blow up.
        req = Request(testing.create_environ(
            host='127.0.0.1',
            path='/hello',
            headers=self.headers))
        self.assertEqual(type(req.subdomain), str)

        # NOTE(kgriffs): Test fallback to SERVER_NAME by using
        # HTTP 1.0, which will cause .create_environ to not set
        # HTTP_HOST.
        req = Request(testing.create_environ(
            protocol='HTTP/1.0',
            host='example.com',
            path='/hello',
            headers=self.headers))
        self.assertEqual(req.subdomain, 'example')

    def test_reconstruct_url(self):
        req = self.req

        scheme = req.protocol
        host = req.get_header('host')
        app = req.app
        path = req.path
        query_string = req.query_string

        expected_uri = ''.join([scheme, '://', host, app, path,
                                '?', query_string])

        self.assertEqual(expected_uri, req.uri)

    @ddt.data(
        u'/hello_\u043f\u0440\u0438\u0432\u0435\u0442',
        u'/test/%E5%BB%B6%E5%AE%89',
        u'/test/%C3%A4%C3%B6%C3%BC%C3%9F%E2%82%AC',
    )
    @testtools.skipUnless(six.PY3, 'Test only applies to Python 3')
    def test_nonlatin_path(self, test_path):
        # NOTE(kgriffs): When a request comes in, web servers decode
        # the path.  The decoded path may contain UTF-8 characters,
        # but according to the WSGI spec, no strings can contain chars
        # outside ISO-8859-1. Therefore, to reconcile the URI
        # encoding standard that allows UTF-8 with the WSGI spec
        # that does not, WSGI servers tunnel the string via
        # ISO-8859-1. falcon.testing.create_environ() mimics this
        # behavior, e.g.:
        #
        #   tunnelled_path = path.encode('utf-8').decode('iso-8859-1')
        #
        # falcon.Request does the following to reverse the process:
        #
        #   path = tunnelled_path.encode('iso-8859-1').decode('utf-8', 'replace')
        #

        req = Request(testing.create_environ(
            host='com',
            path=test_path,
            headers=self.headers))

        self.assertEqual(req.path, falcon.uri.decode(test_path))

    def test_uri(self):
        uri = ('http://' + testing.DEFAULT_HOST + ':8080' +
               self.app + self.relative_uri)

        self.assertEqual(self.req.url, uri)

        # NOTE(kgriffs): Call twice to check caching works
        self.assertEqual(self.req.uri, uri)
        self.assertEqual(self.req.uri, uri)

        uri_noqs = ('http://' + testing.DEFAULT_HOST + self.app + self.path)
        self.assertEqual(self.req_noqs.uri, uri_noqs)

    def test_uri_https(self):
        # =======================================================
        # Default port, implicit
        # =======================================================
        req = Request(testing.create_environ(
            path='/hello', scheme='https'))
        uri = ('https://' + testing.DEFAULT_HOST + '/hello')

        self.assertEqual(req.uri, uri)

        # =======================================================
        # Default port, explicit
        # =======================================================
        req = Request(testing.create_environ(
            path='/hello', scheme='https', port=443))
        uri = ('https://' + testing.DEFAULT_HOST + '/hello')

        self.assertEqual(req.uri, uri)

        # =======================================================
        # Non-default port
        # =======================================================
        req = Request(testing.create_environ(
            path='/hello', scheme='https', port=22))
        uri = ('https://' + testing.DEFAULT_HOST + ':22/hello')

        self.assertEqual(req.uri, uri)

    def test_uri_http_1_0(self):
        # =======================================================
        # HTTP, 80
        # =======================================================
        req = Request(testing.create_environ(
            protocol='HTTP/1.0',
            app=self.app,
            port=80,
            path='/hello',
            query_string=self.qs,
            headers=self.headers))

        uri = ('http://' + testing.DEFAULT_HOST +
               self.app + self.relative_uri)

        self.assertEqual(req.uri, uri)

        # =======================================================
        # HTTP, 80
        # =======================================================
        req = Request(testing.create_environ(
            protocol='HTTP/1.0',
            app=self.app,
            port=8080,
            path='/hello',
            query_string=self.qs,
            headers=self.headers))

        uri = ('http://' + testing.DEFAULT_HOST + ':8080' +
               self.app + self.relative_uri)

        self.assertEqual(req.uri, uri)

        # =======================================================
        # HTTP, 80
        # =======================================================
        req = Request(testing.create_environ(
            protocol='HTTP/1.0',
            scheme='https',
            app=self.app,
            port=443,
            path='/hello',
            query_string=self.qs,
            headers=self.headers))

        uri = ('https://' + testing.DEFAULT_HOST +
               self.app + self.relative_uri)

        self.assertEqual(req.uri, uri)

        # =======================================================
        # HTTP, 80
        # =======================================================
        req = Request(testing.create_environ(
            protocol='HTTP/1.0',
            scheme='https',
            app=self.app,
            port=22,
            path='/hello',
            query_string=self.qs,
            headers=self.headers))

        uri = ('https://' + testing.DEFAULT_HOST + ':22' +
               self.app + self.relative_uri)

        self.assertEqual(req.uri, uri)

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
        self.assertTrue(req.client_accepts('application/json'))
        self.assertTrue(req.client_accepts('application/x-msgpack'))

        headers = {'Accept': 'application/x-msgpack'}
        req = Request(testing.create_environ(headers=headers))
        self.assertFalse(req.client_accepts('application/xml'))
        self.assertFalse(req.client_accepts('application/json'))
        self.assertTrue(req.client_accepts('application/x-msgpack'))

        headers = {}  # NOTE(kgriffs): Equivalent to '*/*' per RFC
        req = Request(testing.create_environ(headers=headers))
        self.assertTrue(req.client_accepts('application/xml'))

        headers = {'Accept': 'application/json'}
        req = Request(testing.create_environ(headers=headers))
        self.assertFalse(req.client_accepts('application/xml'))

        headers = {'Accept': 'application/x-msgpack'}
        req = Request(testing.create_environ(headers=headers))
        self.assertTrue(req.client_accepts('application/x-msgpack'))

        headers = {'Accept': 'application/xm'}
        req = Request(testing.create_environ(headers=headers))
        self.assertFalse(req.client_accepts('application/xml'))

        headers = {'Accept': 'application/*'}
        req = Request(testing.create_environ(headers=headers))
        self.assertTrue(req.client_accepts('application/json'))
        self.assertTrue(req.client_accepts('application/xml'))
        self.assertTrue(req.client_accepts('application/x-msgpack'))

        headers = {'Accept': 'text/*'}
        req = Request(testing.create_environ(headers=headers))
        self.assertTrue(req.client_accepts('text/plain'))
        self.assertTrue(req.client_accepts('text/csv'))
        self.assertFalse(req.client_accepts('application/xhtml+xml'))

        headers = {'Accept': 'text/*, application/xhtml+xml; q=0.0'}
        req = Request(testing.create_environ(headers=headers))
        self.assertTrue(req.client_accepts('text/plain'))
        self.assertTrue(req.client_accepts('text/csv'))
        self.assertFalse(req.client_accepts('application/xhtml+xml'))

        headers = {'Accept': 'text/*; q=0.1, application/xhtml+xml; q=0.5'}
        req = Request(testing.create_environ(headers=headers))
        self.assertTrue(req.client_accepts('text/plain'))
        self.assertTrue(req.client_accepts('application/xhtml+xml'))

        headers = {'Accept': 'text/*,         application/*'}
        req = Request(testing.create_environ(headers=headers))
        self.assertTrue(req.client_accepts('text/plain'))
        self.assertTrue(req.client_accepts('application/xml'))
        self.assertTrue(req.client_accepts('application/json'))
        self.assertTrue(req.client_accepts('application/x-msgpack'))

        headers = {'Accept': 'text/*,application/*'}
        req = Request(testing.create_environ(headers=headers))
        self.assertTrue(req.client_accepts('text/plain'))
        self.assertTrue(req.client_accepts('application/xml'))
        self.assertTrue(req.client_accepts('application/json'))
        self.assertTrue(req.client_accepts('application/x-msgpack'))

    def test_client_accepts_bogus(self):
        headers = {'Accept': '~'}
        req = Request(testing.create_environ(headers=headers))
        self.assertFalse(req.client_accepts('text/plain'))
        self.assertFalse(req.client_accepts('application/json'))

    def test_client_accepts_props(self):
        headers = {'Accept': 'application/xml'}
        req = Request(testing.create_environ(headers=headers))
        self.assertTrue(req.client_accepts_xml)
        self.assertFalse(req.client_accepts_json)
        self.assertFalse(req.client_accepts_msgpack)

        headers = {'Accept': 'application/*'}
        req = Request(testing.create_environ(headers=headers))
        self.assertTrue(req.client_accepts_xml)
        self.assertTrue(req.client_accepts_json)
        self.assertTrue(req.client_accepts_msgpack)

        headers = {'Accept': 'application/json'}
        req = Request(testing.create_environ(headers=headers))
        self.assertFalse(req.client_accepts_xml)
        self.assertTrue(req.client_accepts_json)
        self.assertFalse(req.client_accepts_msgpack)

        headers = {'Accept': 'application/x-msgpack'}
        req = Request(testing.create_environ(headers=headers))
        self.assertFalse(req.client_accepts_xml)
        self.assertFalse(req.client_accepts_json)
        self.assertTrue(req.client_accepts_msgpack)

        headers = {'Accept': 'application/msgpack'}
        req = Request(testing.create_environ(headers=headers))
        self.assertFalse(req.client_accepts_xml)
        self.assertFalse(req.client_accepts_json)
        self.assertTrue(req.client_accepts_msgpack)

        headers = {
            'Accept': 'application/json,application/xml,application/x-msgpack'
        }
        req = Request(testing.create_environ(headers=headers))
        self.assertTrue(req.client_accepts_xml)
        self.assertTrue(req.client_accepts_json)
        self.assertTrue(req.client_accepts_msgpack)

    def test_client_prefers(self):
        headers = {'Accept': 'application/xml'}
        req = Request(testing.create_environ(headers=headers))
        preferred_type = req.client_prefers(['application/xml'])
        self.assertEqual(preferred_type, 'application/xml')

        headers = {'Accept': '*/*'}
        preferred_type = req.client_prefers(('application/xml',
                                             'application/json'))

        # NOTE(kgriffs): If client doesn't care, "prefer" the first one
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
        headers = {'Range': 'bytes=10-'}
        req = Request(testing.create_environ(headers=headers))
        self.assertEqual(req.range, (10, -1))

        headers = {'Range': 'bytes=10-20'}
        req = Request(testing.create_environ(headers=headers))
        self.assertEqual(req.range, (10, 20))

        headers = {'Range': 'bytes=-10240'}
        req = Request(testing.create_environ(headers=headers))
        self.assertEqual(req.range, (-10240, -1))

        headers = {'Range': 'bytes=0-2'}
        req = Request(testing.create_environ(headers=headers))
        self.assertEqual(req.range, (0, 2))

        headers = {'Range': ''}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPInvalidHeader, lambda: req.range)

        req = Request(testing.create_environ())
        self.assertIs(req.range, None)

    def test_range_unit(self):
        headers = {'Range': 'bytes=10-'}
        req = Request(testing.create_environ(headers=headers))
        self.assertEqual(req.range, (10, -1))
        self.assertEqual(req.range_unit, 'bytes')

        headers = {'Range': 'items=10-'}
        req = Request(testing.create_environ(headers=headers))
        self.assertEqual(req.range, (10, -1))
        self.assertEqual(req.range_unit, 'items')

        headers = {'Range': ''}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPInvalidHeader, lambda: req.range_unit)

        req = Request(testing.create_environ())
        self.assertIs(req.range_unit, None)

    def test_range_invalid(self):
        headers = {'Range': 'bytes=10240'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.range)

        headers = {'Range': 'bytes=-'}
        expected_desc = ('The value provided for the Range header is '
                         'invalid. The range offsets are missing.')
        self._test_error_details(headers, 'range',
                                 falcon.HTTPInvalidHeader,
                                 'Invalid header value', expected_desc)

        headers = {'Range': 'bytes=--'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.range)

        headers = {'Range': 'bytes=-3-'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.range)

        headers = {'Range': 'bytes=-3-4'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.range)

        headers = {'Range': 'bytes=3-3-4'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.range)

        headers = {'Range': 'bytes=3-3-'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.range)

        headers = {'Range': 'bytes=3-3- '}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.range)

        headers = {'Range': 'bytes=fizbit'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.range)

        headers = {'Range': 'bytes=a-'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.range)

        headers = {'Range': 'bytes=a-3'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.range)

        headers = {'Range': 'bytes=-b'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.range)

        headers = {'Range': 'bytes=3-b'}
        req = Request(testing.create_environ(headers=headers))
        self.assertRaises(falcon.HTTPBadRequest, lambda: req.range)

        headers = {'Range': 'bytes=x-y'}
        expected_desc = ('The value provided for the Range header is '
                         'invalid. It must be a range formatted '
                         'according to RFC 7233.')
        self._test_error_details(headers, 'range',
                                 falcon.HTTPInvalidHeader,
                                 'Invalid header value', expected_desc)

        headers = {'Range': 'bytes=0-0,-1'}
        expected_desc = ('The value provided for the Range '
                         'header is invalid. The value must be a '
                         'continuous range.')
        self._test_error_details(headers, 'range',
                                 falcon.HTTPInvalidHeader,
                                 'Invalid header value', expected_desc)

        headers = {'Range': '10-'}
        expected_desc = ('The value provided for the Range '
                         'header is invalid. The value must be '
                         "prefixed with a range unit, e.g. 'bytes='")
        self._test_error_details(headers, 'range',
                                 falcon.HTTPInvalidHeader,
                                 'Invalid header value', expected_desc)

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
        expected_desc = ('The value provided for the '
                         'Content-Length header is invalid. The value '
                         'of the header must be a number.')
        self._test_error_details(headers, 'content_length',
                                 falcon.HTTPInvalidHeader,
                                 'Invalid header value', expected_desc)

    def test_bogus_content_length_neg(self):
        headers = {'content-length': '-1'}
        expected_desc = ('The value provided for the Content-Length '
                         'header is invalid. The value of the header '
                         'must be a positive number.')
        self._test_error_details(headers, 'content_length',
                                 falcon.HTTPInvalidHeader,
                                 'Invalid header value', expected_desc)

    @ddt.data(('Date', 'date'),
              ('If-Modified-since', 'if_modified_since'),
              ('If-Unmodified-since', 'if_unmodified_since'),
              )
    @ddt.unpack
    def test_date(self, header, attr):
        date = datetime.datetime(2013, 4, 4, 5, 19, 18)
        date_str = 'Thu, 04 Apr 2013 05:19:18 GMT'

        self._test_header_expected_value(header, date_str, attr, date)

    @ddt.data(('Date', 'date'),
              ('If-Modified-Since', 'if_modified_since'),
              ('If-Unmodified-Since', 'if_unmodified_since'),
              )
    @ddt.unpack
    def test_date_invalid(self, header, attr):

        # Date formats don't conform to RFC 1123
        headers = {header: 'Thu, 04 Apr 2013'}
        expected_desc = ('The value provided for the {0} '
                         'header is invalid. It must be formatted '
                         'according to RFC 7231, Section 7.1.1.1')

        self._test_error_details(headers, attr,
                                 falcon.HTTPInvalidHeader,
                                 'Invalid header value',
                                 expected_desc.format(header))

        headers = {header: ''}
        self._test_error_details(headers, attr,
                                 falcon.HTTPInvalidHeader,
                                 'Invalid header value',
                                 expected_desc.format(header))

    @ddt.data('date', 'if_modified_since', 'if_unmodified_since')
    def test_date_missing(self, attr):
        req = Request(testing.create_environ())
        self.assertIs(getattr(req, attr), None)

    def test_attribute_headers(self):
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
        self._test_attribute_header('If-None-Match', hash, 'if_none_match')
        self._test_attribute_header('If-Range', hash, 'if_range')

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

    def _test_header_expected_value(self, name, value, attr, expected_value):
        headers = {name: value}
        req = Request(testing.create_environ(headers=headers))
        self.assertEqual(getattr(req, attr), expected_value)

    def _test_error_details(self, headers, attr_name,
                            error_type, title, description):
        req = Request(testing.create_environ(headers=headers))

        try:
            getattr(req, attr_name)
            self.fail('{0} not raised'.format(error_type.__name__))
        except error_type as ex:
            self.assertEqual(ex.title, title)
            self.assertEqual(ex.description, description)
