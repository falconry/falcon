import datetime
import itertools

import pytest

import falcon
from falcon.request import Request, RequestOptions
from falcon.request_helpers import _parse_etags
import falcon.testing as testing
import falcon.uri
from falcon.util import compat
from falcon.util.structures import ETag

_PROTOCOLS = ['HTTP/1.0', 'HTTP/1.1']


def _make_etag(value, is_weak=False):
    """Creates and returns an ETag object.

    Args:
        value (str): Unquated entity tag value
        is_weak (bool): The weakness indicator

    Returns:
        A ``str``-like Etag instance with weakness indicator.

    """
    etag = ETag(value)

    etag.is_weak = is_weak
    return etag


class TestRequestAttributes(object):

    def setup_method(self, method):
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
        assert self.req.auth is None

    def test_host(self):
        assert self.req.host == testing.DEFAULT_HOST

    def test_subdomain(self):
        req = Request(testing.create_environ(
            host='com',
            path='/hello',
            headers=self.headers))
        assert req.subdomain is None

        req = Request(testing.create_environ(
            host='example.com',
            path='/hello',
            headers=self.headers))
        assert req.subdomain == 'example'

        req = Request(testing.create_environ(
            host='highwire.example.com',
            path='/hello',
            headers=self.headers))
        assert req.subdomain == 'highwire'

        req = Request(testing.create_environ(
            host='lb01.dfw01.example.com',
            port=8080,
            path='/hello',
            headers=self.headers))
        assert req.subdomain == 'lb01'

        # NOTE(kgriffs): Behavior for IP addresses is undefined,
        # so just make sure it doesn't blow up.
        req = Request(testing.create_environ(
            host='127.0.0.1',
            path='/hello',
            headers=self.headers))
        assert type(req.subdomain) == str

        # NOTE(kgriffs): Test fallback to SERVER_NAME by using
        # HTTP 1.0, which will cause .create_environ to not set
        # HTTP_HOST.
        req = Request(testing.create_environ(
            protocol='HTTP/1.0',
            host='example.com',
            path='/hello',
            headers=self.headers))
        assert req.subdomain == 'example'

    def test_reconstruct_url(self):
        req = self.req

        scheme = req.scheme
        host = req.get_header('host')
        app = req.app
        path = req.path
        query_string = req.query_string

        expected_prefix = ''.join([scheme, '://', host, app])
        expected_uri = ''.join([expected_prefix, path, '?', query_string])

        assert req.uri == expected_uri
        assert req.prefix == expected_prefix
        assert req.prefix == expected_prefix  # Check cached value

    @pytest.mark.skipif(not compat.PY3, reason='Test only applies to Python 3')
    @pytest.mark.parametrize('test_path', [
        u'/hello_\u043f\u0440\u0438\u0432\u0435\u0442',
        u'/test/%E5%BB%B6%E5%AE%89',
        u'/test/%C3%A4%C3%B6%C3%BC%C3%9F%E2%82%AC',
    ])
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

        assert req.path == falcon.uri.decode(test_path)

    def test_uri(self):
        prefix = 'http://' + testing.DEFAULT_HOST + ':8080' + self.app
        uri = prefix + self.relative_uri

        assert self.req.url == uri
        assert self.req.prefix == prefix

        # NOTE(kgriffs): Call twice to check caching works
        assert self.req.uri == uri
        assert self.req.uri == uri

        uri_noqs = ('http://' + testing.DEFAULT_HOST + self.app + self.path)
        assert self.req_noqs.uri == uri_noqs

    def test_uri_https(self):
        # =======================================================
        # Default port, implicit
        # =======================================================
        req = Request(testing.create_environ(
            path='/hello', scheme='https'))
        uri = ('https://' + testing.DEFAULT_HOST + '/hello')

        assert req.uri == uri

        # =======================================================
        # Default port, explicit
        # =======================================================
        req = Request(testing.create_environ(
            path='/hello', scheme='https', port=443))
        uri = ('https://' + testing.DEFAULT_HOST + '/hello')

        assert req.uri == uri

        # =======================================================
        # Non-default port
        # =======================================================
        req = Request(testing.create_environ(
            path='/hello', scheme='https', port=22))
        uri = ('https://' + testing.DEFAULT_HOST + ':22/hello')

        assert req.uri == uri

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

        assert req.uri == uri

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

        assert req.uri == uri

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

        assert req.uri == uri

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

        assert req.uri == uri

    def test_relative_uri(self):
        assert self.req.relative_uri == self.app + self.relative_uri
        assert self.req_noqs.relative_uri == self.app + self.path

        req_noapp = Request(testing.create_environ(
            path='/hello',
            query_string=self.qs,
            headers=self.headers))

        assert req_noapp.relative_uri == self.relative_uri

        req_noapp = Request(testing.create_environ(
            path='/hello/',
            query_string=self.qs,
            headers=self.headers))

        relative_trailing_uri = self.path + '/?' + self.qs
        # NOTE(kgriffs): Call twice to check caching works
        assert req_noapp.relative_uri == relative_trailing_uri
        assert req_noapp.relative_uri == relative_trailing_uri

        options = RequestOptions()
        options.strip_url_path_trailing_slash = False
        req_noapp = Request(testing.create_environ(
            path='/hello/',
            query_string=self.qs,
            headers=self.headers),
            options=options)

        assert req_noapp.relative_uri == '/hello/' + '?' + self.qs

    def test_client_accepts(self):
        headers = {'Accept': 'application/xml'}
        req = Request(testing.create_environ(headers=headers))
        assert req.client_accepts('application/xml')

        headers = {'Accept': '*/*'}
        req = Request(testing.create_environ(headers=headers))
        assert req.client_accepts('application/xml')
        assert req.client_accepts('application/json')
        assert req.client_accepts('application/x-msgpack')

        headers = {'Accept': 'application/x-msgpack'}
        req = Request(testing.create_environ(headers=headers))
        assert not req.client_accepts('application/xml')
        assert not req.client_accepts('application/json')
        assert req.client_accepts('application/x-msgpack')

        headers = {}  # NOTE(kgriffs): Equivalent to '*/*' per RFC
        req = Request(testing.create_environ(headers=headers))
        assert req.client_accepts('application/xml')

        headers = {'Accept': 'application/json'}
        req = Request(testing.create_environ(headers=headers))
        assert not req.client_accepts('application/xml')

        headers = {'Accept': 'application/x-msgpack'}
        req = Request(testing.create_environ(headers=headers))
        assert req.client_accepts('application/x-msgpack')

        headers = {'Accept': 'application/xm'}
        req = Request(testing.create_environ(headers=headers))
        assert not req.client_accepts('application/xml')

        headers = {'Accept': 'application/*'}
        req = Request(testing.create_environ(headers=headers))
        assert req.client_accepts('application/json')
        assert req.client_accepts('application/xml')
        assert req.client_accepts('application/x-msgpack')

        headers = {'Accept': 'text/*'}
        req = Request(testing.create_environ(headers=headers))
        assert req.client_accepts('text/plain')
        assert req.client_accepts('text/csv')
        assert not req.client_accepts('application/xhtml+xml')

        headers = {'Accept': 'text/*, application/xhtml+xml; q=0.0'}
        req = Request(testing.create_environ(headers=headers))
        assert req.client_accepts('text/plain')
        assert req.client_accepts('text/csv')
        assert not req.client_accepts('application/xhtml+xml')

        headers = {'Accept': 'text/*; q=0.1, application/xhtml+xml; q=0.5'}
        req = Request(testing.create_environ(headers=headers))
        assert req.client_accepts('text/plain')
        assert req.client_accepts('application/xhtml+xml')

        headers = {'Accept': 'text/*,         application/*'}
        req = Request(testing.create_environ(headers=headers))
        assert req.client_accepts('text/plain')
        assert req.client_accepts('application/xml')
        assert req.client_accepts('application/json')
        assert req.client_accepts('application/x-msgpack')

        headers = {'Accept': 'text/*,application/*'}
        req = Request(testing.create_environ(headers=headers))
        assert req.client_accepts('text/plain')
        assert req.client_accepts('application/xml')
        assert req.client_accepts('application/json')
        assert req.client_accepts('application/x-msgpack')

    def test_client_accepts_bogus(self):
        headers = {'Accept': '~'}
        req = Request(testing.create_environ(headers=headers))
        assert not req.client_accepts('text/plain')
        assert not req.client_accepts('application/json')

    def test_client_accepts_props(self):
        headers = {'Accept': 'application/xml'}
        req = Request(testing.create_environ(headers=headers))
        assert req.client_accepts_xml
        assert not req.client_accepts_json
        assert not req.client_accepts_msgpack

        headers = {'Accept': 'application/*'}
        req = Request(testing.create_environ(headers=headers))
        assert req.client_accepts_xml
        assert req.client_accepts_json
        assert req.client_accepts_msgpack

        headers = {'Accept': 'application/json'}
        req = Request(testing.create_environ(headers=headers))
        assert not req.client_accepts_xml
        assert req.client_accepts_json
        assert not req.client_accepts_msgpack

        headers = {'Accept': 'application/x-msgpack'}
        req = Request(testing.create_environ(headers=headers))
        assert not req.client_accepts_xml
        assert not req.client_accepts_json
        assert req.client_accepts_msgpack

        headers = {'Accept': 'application/msgpack'}
        req = Request(testing.create_environ(headers=headers))
        assert not req.client_accepts_xml
        assert not req.client_accepts_json
        assert req.client_accepts_msgpack

        headers = {
            'Accept': 'application/json,application/xml,application/x-msgpack'
        }
        req = Request(testing.create_environ(headers=headers))
        assert req.client_accepts_xml
        assert req.client_accepts_json
        assert req.client_accepts_msgpack

    def test_client_prefers(self):
        headers = {'Accept': 'application/xml'}
        req = Request(testing.create_environ(headers=headers))
        preferred_type = req.client_prefers(['application/xml'])
        assert preferred_type == 'application/xml'

        headers = {'Accept': '*/*'}
        preferred_type = req.client_prefers(('application/xml',
                                             'application/json'))

        # NOTE(kgriffs): If client doesn't care, "prefer" the first one
        assert preferred_type == 'application/xml'

        headers = {'Accept': 'text/*; q=0.1, application/xhtml+xml; q=0.5'}
        req = Request(testing.create_environ(headers=headers))
        preferred_type = req.client_prefers(['application/xhtml+xml'])
        assert preferred_type == 'application/xhtml+xml'

        headers = {'Accept': '3p12845j;;;asfd;'}
        req = Request(testing.create_environ(headers=headers))
        preferred_type = req.client_prefers(['application/xhtml+xml'])
        assert preferred_type is None

    def test_range(self):
        headers = {'Range': 'bytes=10-'}
        req = Request(testing.create_environ(headers=headers))
        assert req.range == (10, -1)

        headers = {'Range': 'bytes=10-20'}
        req = Request(testing.create_environ(headers=headers))
        assert req.range == (10, 20)

        headers = {'Range': 'bytes=-10240'}
        req = Request(testing.create_environ(headers=headers))
        assert req.range == (-10240, -1)

        headers = {'Range': 'bytes=0-2'}
        req = Request(testing.create_environ(headers=headers))
        assert req.range == (0, 2)

        headers = {'Range': ''}
        req = Request(testing.create_environ(headers=headers))
        with pytest.raises(falcon.HTTPInvalidHeader):
            req.range

        req = Request(testing.create_environ())
        assert req.range is None

    def test_range_unit(self):
        headers = {'Range': 'bytes=10-'}
        req = Request(testing.create_environ(headers=headers))
        assert req.range == (10, -1)
        assert req.range_unit == 'bytes'

        headers = {'Range': 'items=10-'}
        req = Request(testing.create_environ(headers=headers))
        assert req.range == (10, -1)
        assert req.range_unit == 'items'

        headers = {'Range': ''}
        req = Request(testing.create_environ(headers=headers))
        with pytest.raises(falcon.HTTPInvalidHeader):
            req.range_unit

        req = Request(testing.create_environ())
        assert req.range_unit is None

    def test_range_invalid(self):
        headers = {'Range': 'bytes=10240'}
        req = Request(testing.create_environ(headers=headers))
        with pytest.raises(falcon.HTTPBadRequest):
            req.range

        headers = {'Range': 'bytes=-'}
        expected_desc = ('The value provided for the Range header is '
                         'invalid. The range offsets are missing.')
        self._test_error_details(headers, 'range',
                                 falcon.HTTPInvalidHeader,
                                 'Invalid header value', expected_desc)

        headers = {'Range': 'bytes=--'}
        req = Request(testing.create_environ(headers=headers))
        with pytest.raises(falcon.HTTPBadRequest):
            req.range

        headers = {'Range': 'bytes=-3-'}
        req = Request(testing.create_environ(headers=headers))
        with pytest.raises(falcon.HTTPBadRequest):
            req.range

        headers = {'Range': 'bytes=-3-4'}
        req = Request(testing.create_environ(headers=headers))
        with pytest.raises(falcon.HTTPBadRequest):
            req.range

        headers = {'Range': 'bytes=3-3-4'}
        req = Request(testing.create_environ(headers=headers))
        with pytest.raises(falcon.HTTPBadRequest):
            req.range

        headers = {'Range': 'bytes=3-3-'}
        req = Request(testing.create_environ(headers=headers))
        with pytest.raises(falcon.HTTPBadRequest):
            req.range

        headers = {'Range': 'bytes=3-3- '}
        req = Request(testing.create_environ(headers=headers))
        with pytest.raises(falcon.HTTPBadRequest):
            req.range

        headers = {'Range': 'bytes=fizbit'}
        req = Request(testing.create_environ(headers=headers))
        with pytest.raises(falcon.HTTPBadRequest):
            req.range

        headers = {'Range': 'bytes=a-'}
        req = Request(testing.create_environ(headers=headers))
        with pytest.raises(falcon.HTTPBadRequest):
            req.range

        headers = {'Range': 'bytes=a-3'}
        req = Request(testing.create_environ(headers=headers))
        with pytest.raises(falcon.HTTPBadRequest):
            req.range

        headers = {'Range': 'bytes=-b'}
        req = Request(testing.create_environ(headers=headers))
        with pytest.raises(falcon.HTTPBadRequest):
            req.range

        headers = {'Range': 'bytes=3-b'}
        req = Request(testing.create_environ(headers=headers))
        with pytest.raises(falcon.HTTPBadRequest):
            req.range

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
        assert req.range is None

        req = Request(testing.create_environ())
        assert req.content_length is None

    def test_content_length(self):
        headers = {'content-length': '5656'}
        req = Request(testing.create_environ(headers=headers))
        assert req.content_length == 5656

        headers = {'content-length': ''}
        req = Request(testing.create_environ(headers=headers))
        assert req.content_length is None

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

    @pytest.mark.parametrize('header,attr', [
        ('Date', 'date'),
        ('If-Modified-Since', 'if_modified_since'),
        ('If-Unmodified-Since', 'if_unmodified_since'),
    ])
    def test_date(self, header, attr):
        date = datetime.datetime(2013, 4, 4, 5, 19, 18)
        date_str = 'Thu, 04 Apr 2013 05:19:18 GMT'

        self._test_header_expected_value(header, date_str, attr, date)

    @pytest.mark.parametrize('header,attr', [
        ('Date', 'date'),
        ('If-Modified-Since', 'if_modified_since'),
        ('If-Unmodified-Since', 'if_unmodified_since'),
    ])
    def test_date_invalid(self, header, attr):

        # Date formats don't conform to RFC 1123
        headers = {header: 'Thu, 04 Apr 2013'}
        expected_desc = ('The value provided for the {} '
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

    @pytest.mark.parametrize('attr', ('date', 'if_modified_since', 'if_unmodified_since'))
    def test_date_missing(self, attr):
        req = Request(testing.create_environ())
        assert getattr(req, attr) is None

    def test_attribute_headers(self):
        date = 'Wed, 21 Oct 2015 07:28:00 GMT'
        auth = 'HMAC_SHA1 c590afa9bb59191ffab30f223791e82d3fd3e3af'
        agent = 'testing/1.0.1'
        default_agent = 'curl/7.24.0 (x86_64-apple-darwin12.0)'
        referer = 'https://www.google.com/'

        self._test_attribute_header('Accept', 'x-falcon', 'accept',
                                    default='*/*')

        self._test_attribute_header('Authorization', auth, 'auth')

        self._test_attribute_header('Content-Type', 'text/plain',
                                    'content_type')
        self._test_attribute_header('Expect', '100-continue', 'expect')

        self._test_attribute_header('If-Range', date, 'if_range')

        self._test_attribute_header('User-Agent', agent, 'user_agent',
                                    default=default_agent)
        self._test_attribute_header('Referer', referer, 'referer')

    def test_method(self):
        assert self.req.method == 'GET'

        self.req = Request(testing.create_environ(path='', method='HEAD'))
        assert self.req.method == 'HEAD'

    def test_empty_path(self):
        self.req = Request(testing.create_environ(path=''))
        assert self.req.path == '/'

    def test_content_type_method(self):
        assert self.req.get_header('content-type') == 'text/plain'

    def test_content_length_method(self):
        assert self.req.get_header('content-length') == '4829'

    # TODO(kgriffs): Migrate to pytest and parametrized fixtures
    # to DRY things up a bit.
    @pytest.mark.parametrize('protocol', _PROTOCOLS)
    def test_port_explicit(self, protocol):
        port = 9000
        req = Request(testing.create_environ(
            protocol=protocol,
            port=port,
            app=self.app,
            path='/hello',
            query_string=self.qs,
            headers=self.headers))

        assert req.port == port

    @pytest.mark.parametrize('protocol', _PROTOCOLS)
    def test_scheme_https(self, protocol):
        scheme = 'https'
        req = Request(testing.create_environ(
            protocol=protocol,
            scheme=scheme,
            app=self.app,
            path='/hello',
            query_string=self.qs,
            headers=self.headers))

        assert req.scheme == scheme
        assert req.port == 443

    @pytest.mark.parametrize(
        'protocol, set_forwarded_proto',
        list(itertools.product(_PROTOCOLS, [True, False]))
    )
    def test_scheme_http(self, protocol, set_forwarded_proto):
        scheme = 'http'
        forwarded_scheme = 'HttPs'

        headers = dict(self.headers)

        if set_forwarded_proto:
            headers['X-Forwarded-Proto'] = forwarded_scheme

        req = Request(testing.create_environ(
            protocol=protocol,
            scheme=scheme,
            app=self.app,
            path='/hello',
            query_string=self.qs,
            headers=headers))

        assert req.scheme == scheme
        assert req.port == 80

        if set_forwarded_proto:
            assert req.forwarded_scheme == forwarded_scheme.lower()
        else:
            assert req.forwarded_scheme == scheme

    @pytest.mark.parametrize('protocol', _PROTOCOLS)
    def test_netloc_default_port(self, protocol):
        req = Request(testing.create_environ(
            protocol=protocol,
            app=self.app,
            path='/hello',
            query_string=self.qs,
            headers=self.headers))

        assert req.netloc == 'falconframework.org'

    @pytest.mark.parametrize('protocol', _PROTOCOLS)
    def test_netloc_nondefault_port(self, protocol):
        req = Request(testing.create_environ(
            protocol=protocol,
            port='8080',
            app=self.app,
            path='/hello',
            query_string=self.qs,
            headers=self.headers))

        assert req.netloc == 'falconframework.org:8080'

    @pytest.mark.parametrize('protocol', _PROTOCOLS)
    def test_netloc_from_env(self, protocol):
        port = 9000
        host = 'example.org'
        env = testing.create_environ(
            protocol=protocol,
            host=host,
            port=port,
            app=self.app,
            path='/hello',
            query_string=self.qs,
            headers=self.headers)

        req = Request(env)

        assert req.port == port
        assert req.netloc == '{}:{}'.format(host, port)

    def test_app_present(self):
        req = Request(testing.create_environ(app='/moving-pictures'))
        assert req.app == '/moving-pictures'

    def test_app_blank(self):
        req = Request(testing.create_environ(app=''))
        assert req.app == ''

    def test_app_missing(self):
        env = testing.create_environ()
        del env['SCRIPT_NAME']
        req = Request(env)

        assert req.app == ''

    @pytest.mark.parametrize('etag,expected', [
        ('', None),
        (' ', None),
        ('   ', None),
        ('\t', None),
        (' \t', None),
        (',', None),
        (',,', None),
        (',, ', None),
        (', , ', None),
        ('*', ['*']),
        (
            'W/"67ab43"',
            [_make_etag('67ab43', is_weak=True)]
        ),
        (
            'w/"67ab43"',
            [_make_etag('67ab43', is_weak=True)]
        ),
        (
            ' w/"67ab43"',
            [_make_etag('67ab43', is_weak=True)]
        ),
        (
            'w/"67ab43" ',
            [_make_etag('67ab43', is_weak=True)]
        ),
        (
            'w/"67ab43 " ',
            [_make_etag('67ab43 ', is_weak=True)]
        ),
        (
            '"67ab43"',
            [_make_etag('67ab43')]
        ),
        (
            ' "67ab43"',
            [_make_etag('67ab43')]
        ),
        (
            ' "67ab43" ',
            [_make_etag('67ab43')]
        ),
        (
            '"67ab43" ',
            [_make_etag('67ab43')]
        ),
        (
            '" 67ab43" ',
            [_make_etag(' 67ab43')]
        ),
        (
            '67ab43"',
            [_make_etag('67ab43"')]
        ),
        (
            '"67ab43',
            [_make_etag('"67ab43')]
        ),
        (
            '67ab43',
            [_make_etag('67ab43')]
        ),
        (
            '67ab43 ',
            [_make_etag('67ab43')]
        ),
        (
            '  67ab43 ',
            [_make_etag('67ab43')]
        ),
        (
            '  67ab43',
            [_make_etag('67ab43')]
        ),
        (
            # NOTE(kgriffs): To simplify parsing and improve performance, we
            #   do not attempt to handle unquoted entity-tags when there is
            #   a list; it is non-standard anyway, and has been since 1999.
            'W/"67ab43", "54ed21", junk"F9,22", junk "41, 7F", unquoted, w/"22, 41, 7F", "", W/""',
            [
                _make_etag('67ab43', is_weak=True),
                _make_etag('54ed21'),

                # NOTE(kgriffs): Test that the ETag initializer defaults to
                #   is_weak == False
                ETag('F9,22'),

                _make_etag('41, 7F'),
                _make_etag('22, 41, 7F', is_weak=True),

                # NOTE(kgriffs): According to the grammar in RFC 7232, zero
                #  etagc's is acceptable.
                _make_etag(''),
                _make_etag('', is_weak=True),
            ]
        ),
    ])
    def test_etag(self, etag, expected):
        self._test_header_etag('If-Match', etag, 'if_match', expected)
        self._test_header_etag('If-None-Match', etag, 'if_none_match', expected)

    def test_etag_is_missing(self):
        # NOTE(kgriffs): Loop in order to test caching
        for __ in range(3):
            assert self.req.if_match is None
            assert self.req.if_none_match is None

    @pytest.mark.parametrize('header_value', ['', ' ', '  '])
    def test_etag_parsing_helper(self, header_value):
        # NOTE(kgriffs): Test a couple of cases that are not directly covered
        #   elsewhere (but that we want the helper to still support
        #   for the sake of avoiding suprises if they are ever called without
        #   preflighting the header value).

        assert _parse_etags(header_value) is None

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _test_attribute_header(self, name, value, attr, default=None):
        headers = {name: value}
        req = Request(testing.create_environ(headers=headers))
        assert getattr(req, attr) == value

        req = Request(testing.create_environ())
        assert getattr(req, attr) == default

    def _test_header_expected_value(self, name, value, attr, expected_value):
        headers = {name: value}
        req = Request(testing.create_environ(headers=headers))
        assert getattr(req, attr) == expected_value

    def _test_header_etag(self, name, value, attr, expected_value):
        headers = {name: value}
        req = Request(testing.create_environ(headers=headers))

        # NOTE(kgriffs): Loop in order to test caching
        for __ in range(3):
            value = getattr(req, attr)

            if expected_value is None:
                assert value is None
                return

            assert value is not None

            for element, expected_element in zip(value, expected_value):
                assert element == expected_element
                if isinstance(expected_element, ETag):
                    assert element.is_weak == expected_element.is_weak

    def _test_error_details(self, headers, attr_name,
                            error_type, title, description):
        req = Request(testing.create_environ(headers=headers))

        try:
            getattr(req, attr_name)
            pytest.fail('{} not raised'.format(error_type.__name__))
        except error_type as ex:
            assert ex.title == title
            assert ex.description == description
