import datetime
import itertools

import pytest

import falcon
from falcon.request import Request
from falcon.request import RequestOptions
from falcon.request_helpers import _parse_etags
import falcon.testing as testing
import falcon.uri
from falcon.util import DeprecatedWarning
from falcon.util.structures import ETag

_HTTP_VERSIONS = ['1.0', '1.1', '2']


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


# NOTE(vytas): create_req is very heavily used in this module in unittest-style
#   classes, so we simply recreate the function here.
def create_req(asgi, options=None, **environ_or_scope_kwargs):
    create_method = testing.create_asgi_req if asgi else testing.create_req
    return create_method(options=options, **environ_or_scope_kwargs)


def test_missing_qs():
    env = testing.create_environ()
    if 'QUERY_STRING' in env:
        del env['QUERY_STRING']

    # Should not cause an exception when Request is instantiated
    Request(env)


def test_app_missing():
    env = testing.create_environ()
    del env['SCRIPT_NAME']
    req = Request(env)

    assert req.root_path == ''
    with pytest.warns(DeprecatedWarning):
        assert req.app == ''


class TestRequestAttributes:
    def setup_method(self, method):
        asgi = self._item.callspec.getparam('asgi')

        self.qs = 'marker=deadbeef&limit=10'

        self.headers = {
            'Content-Type': 'text/plain',
            'Content-Length': '4829',
            'Authorization': '',
        }

        self.root_path = '/test'
        self.path = '/hello'
        self.relative_uri = self.path + '?' + self.qs

        self.req = create_req(
            asgi,
            root_path=self.root_path,
            port=8080,
            path='/hello',
            query_string=self.qs,
            headers=self.headers,
        )

        self.req_noqs = create_req(
            asgi, root_path=self.root_path, path='/hello', headers=self.headers
        )

    def test_empty(self, asgi):
        assert self.req.auth is None

    def test_host(self, asgi):
        assert self.req.host == testing.DEFAULT_HOST

    def test_subdomain(self, asgi):
        req = create_req(asgi, host='com', path='/hello', headers=self.headers)
        assert req.subdomain is None

        req = create_req(asgi, host='example.com', path='/hello', headers=self.headers)
        assert req.subdomain == 'example'

        req = create_req(
            asgi, host='highwire.example.com', path='/hello', headers=self.headers
        )
        assert req.subdomain == 'highwire'

        req = create_req(
            asgi,
            host='lb01.dfw01.example.com',
            port=8080,
            path='/hello',
            headers=self.headers,
        )
        assert req.subdomain == 'lb01'

        # NOTE(kgriffs): Behavior for IP addresses is undefined,
        # so just make sure it doesn't blow up.
        req = create_req(asgi, host='127.0.0.1', path='/hello', headers=self.headers)
        assert type(req.subdomain) is str

        # NOTE(kgriffs): Test fallback to SERVER_NAME by using
        # HTTP 1.0, which will cause .create_environ to not set
        # HTTP_HOST.
        req = create_req(
            asgi,
            http_version='1.0',
            host='example.com',
            path='/hello',
            headers=self.headers,
        )
        assert req.subdomain == 'example'

    def test_reconstruct_url(self, asgi):
        req = self.req

        scheme = req.scheme
        host = req.get_header('host')
        app = req.root_path
        with pytest.warns(DeprecatedWarning):
            assert req.app == app
        path = req.path
        query_string = req.query_string

        expected_prefix = ''.join([scheme, '://', host, app])
        expected_uri = ''.join([expected_prefix, path, '?', query_string])

        assert req.uri == expected_uri
        assert req.prefix == expected_prefix
        assert req.prefix == expected_prefix  # Check cached value

    @pytest.mark.parametrize(
        'test_path',
        [
            '/hello_\u043f\u0440\u0438\u0432\u0435\u0442',
            '/test/%E5%BB%B6%E5%AE%89',
            '/test/%C3%A4%C3%B6%C3%BC%C3%9F%E2%82%AC',
        ],
    )
    def test_nonlatin_path(self, asgi, test_path):
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

        req = create_req(asgi, host='com', path=test_path, headers=self.headers)

        assert req.path == falcon.uri.decode(test_path)

    def test_uri(self, asgi):
        prefix = 'http://' + testing.DEFAULT_HOST + ':8080' + self.root_path
        uri = prefix + self.relative_uri

        assert self.req.url == uri
        assert self.req.prefix == prefix

        # NOTE(kgriffs): Call twice to check caching works
        assert self.req.uri == uri
        assert self.req.uri == uri

        uri_noqs = 'http://' + testing.DEFAULT_HOST + self.root_path + self.path
        assert self.req_noqs.uri == uri_noqs

    def test_uri_https(self, asgi):
        # =======================================================
        # Default port, implicit
        # =======================================================
        req = create_req(asgi, path='/hello', scheme='https')
        uri = 'https://' + testing.DEFAULT_HOST + '/hello'

        assert req.uri == uri

        # =======================================================
        # Default port, explicit
        # =======================================================
        req = create_req(asgi, path='/hello', scheme='https', port=443)
        uri = 'https://' + testing.DEFAULT_HOST + '/hello'

        assert req.uri == uri

        # =======================================================
        # Non-default port
        # =======================================================
        req = create_req(asgi, path='/hello', scheme='https', port=22)
        uri = 'https://' + testing.DEFAULT_HOST + ':22/hello'

        assert req.uri == uri

    def test_uri_http_1_0(self, asgi):
        # =======================================================
        # HTTP, 80
        # =======================================================
        req = create_req(
            asgi,
            http_version='1.0',
            root_path=self.root_path,
            port=80,
            path='/hello',
            query_string=self.qs,
            headers=self.headers,
        )

        uri = 'http://' + testing.DEFAULT_HOST + self.root_path + self.relative_uri

        assert req.uri == uri

        # =======================================================
        # HTTP, 80
        # =======================================================
        req = create_req(
            asgi,
            http_version='1.0',
            root_path=self.root_path,
            port=8080,
            path='/hello',
            query_string=self.qs,
            headers=self.headers,
        )

        uri = (
            'http://'
            + testing.DEFAULT_HOST
            + ':8080'
            + self.root_path
            + self.relative_uri
        )

        assert req.uri == uri

        # =======================================================
        # HTTP, 80
        # =======================================================
        req = create_req(
            asgi,
            http_version='1.0',
            scheme='https',
            root_path=self.root_path,
            port=443,
            path='/hello',
            query_string=self.qs,
            headers=self.headers,
        )

        uri = 'https://' + testing.DEFAULT_HOST + self.root_path + self.relative_uri

        assert req.uri == uri

        # =======================================================
        # HTTP, 80
        # =======================================================
        req = create_req(
            asgi,
            http_version='1.0',
            scheme='https',
            root_path=self.root_path,
            port=22,
            path='/hello',
            query_string=self.qs,
            headers=self.headers,
        )

        uri = (
            'https://'
            + testing.DEFAULT_HOST
            + ':22'
            + self.root_path
            + self.relative_uri
        )

        assert req.uri == uri

    def test_relative_uri(self, asgi):
        assert self.req.relative_uri == self.root_path + self.relative_uri
        assert self.req_noqs.relative_uri == self.root_path + self.path

        req_noapp = create_req(
            asgi, path='/hello', query_string=self.qs, headers=self.headers
        )

        assert req_noapp.relative_uri == self.relative_uri

        req_noapp = create_req(
            asgi, path='/hello/', query_string=self.qs, headers=self.headers
        )

        relative_trailing_uri = self.path + '/?' + self.qs
        # NOTE(kgriffs): Call twice to check caching works
        assert req_noapp.relative_uri == relative_trailing_uri
        assert req_noapp.relative_uri == relative_trailing_uri

        options = RequestOptions()
        options.strip_url_path_trailing_slash = False
        req_noapp = create_req(
            asgi,
            options=options,
            path='/hello/',
            query_string=self.qs,
            headers=self.headers,
        )

        assert req_noapp.relative_uri == '/hello/' + '?' + self.qs

    def test_client_accepts(self, asgi):
        headers = {'Accept': 'application/xml'}
        req = create_req(asgi, headers=headers)
        assert req.client_accepts('application/xml')

        headers = {'Accept': '*/*'}
        req = create_req(asgi, headers=headers)
        assert req.client_accepts('application/xml')
        assert req.client_accepts('application/json')
        assert req.client_accepts('application/x-msgpack')

        headers = {'Accept': 'application/x-msgpack'}
        req = create_req(asgi, headers=headers)
        assert not req.client_accepts('application/xml')
        assert not req.client_accepts('application/json')
        assert req.client_accepts('application/x-msgpack')

        headers = {}  # NOTE(kgriffs): Equivalent to '*/*' per RFC
        req = create_req(asgi, headers=headers)
        assert req.client_accepts('application/xml')

        headers = {'Accept': 'application/json'}
        req = create_req(asgi, headers=headers)
        assert not req.client_accepts('application/xml')

        headers = {'Accept': 'application/x-msgpack'}
        req = create_req(asgi, headers=headers)
        assert req.client_accepts('application/x-msgpack')

        headers = {'Accept': 'application/xm'}
        req = create_req(asgi, headers=headers)
        assert not req.client_accepts('application/xml')

        headers = {'Accept': 'application/*'}
        req = create_req(asgi, headers=headers)
        assert req.client_accepts('application/json')
        assert req.client_accepts('application/xml')
        assert req.client_accepts('application/x-msgpack')

        headers = {'Accept': 'text/*'}
        req = create_req(asgi, headers=headers)
        assert req.client_accepts('text/plain')
        assert req.client_accepts('text/csv')
        assert not req.client_accepts('application/xhtml+xml')

        headers = {'Accept': 'text/*, application/xhtml+xml; q=0.0'}
        req = create_req(asgi, headers=headers)
        assert req.client_accepts('text/plain')
        assert req.client_accepts('text/csv')
        assert not req.client_accepts('application/xhtml+xml')

        headers = {'Accept': 'text/*; q=0.1, application/xhtml+xml; q=0.5'}
        req = create_req(asgi, headers=headers)
        assert req.client_accepts('text/plain')
        assert req.client_accepts('application/xhtml+xml')

        headers = {'Accept': 'text/*,         application/*'}
        req = create_req(asgi, headers=headers)
        assert req.client_accepts('text/plain')
        assert req.client_accepts('application/xml')
        assert req.client_accepts('application/json')
        assert req.client_accepts('application/x-msgpack')

        headers = {'Accept': 'text/*,application/*'}
        req = create_req(asgi, headers=headers)
        assert req.client_accepts('text/plain')
        assert req.client_accepts('application/xml')
        assert req.client_accepts('application/json')
        assert req.client_accepts('application/x-msgpack')

    def test_client_accepts_bogus(self, asgi):
        headers = {'Accept': '~'}
        req = create_req(asgi, headers=headers)
        assert not req.client_accepts('text/plain')
        assert not req.client_accepts('application/json')

    def test_client_accepts_props(self, asgi):
        headers = {'Accept': 'application/xml'}
        req = create_req(asgi, headers=headers)
        assert req.client_accepts_xml
        assert not req.client_accepts_json
        assert not req.client_accepts_msgpack

        headers = {'Accept': 'application/*'}
        req = create_req(asgi, headers=headers)
        assert req.client_accepts_xml
        assert req.client_accepts_json
        assert req.client_accepts_msgpack

        headers = {'Accept': 'application/json'}
        req = create_req(asgi, headers=headers)
        assert not req.client_accepts_xml
        assert req.client_accepts_json
        assert not req.client_accepts_msgpack

        headers = {'Accept': 'application/x-msgpack'}
        req = create_req(asgi, headers=headers)
        assert not req.client_accepts_xml
        assert not req.client_accepts_json
        assert req.client_accepts_msgpack

        headers = {'Accept': 'application/msgpack'}
        req = create_req(asgi, headers=headers)
        assert not req.client_accepts_xml
        assert not req.client_accepts_json
        assert req.client_accepts_msgpack

        headers = {'Accept': 'application/json,application/xml,application/x-msgpack'}
        req = create_req(asgi, headers=headers)
        assert req.client_accepts_xml
        assert req.client_accepts_json
        assert req.client_accepts_msgpack

    def test_client_prefers(self, asgi):
        headers = {'Accept': 'application/xml'}
        req = create_req(asgi, headers=headers)
        preferred_type = req.client_prefers(['application/xml'])
        assert preferred_type == 'application/xml'

        headers = {'Accept': '*/*'}
        preferred_type = req.client_prefers(('application/xml', 'application/json'))

        # NOTE(kgriffs): If client doesn't care, "prefer" the first one
        assert preferred_type == 'application/xml'

        headers = {'Accept': 'text/*; q=0.1, application/xhtml+xml; q=0.5'}
        req = create_req(asgi, headers=headers)
        preferred_type = req.client_prefers(['application/xhtml+xml'])
        assert preferred_type == 'application/xhtml+xml'

        headers = {'Accept': '3p12845j;;;asfd;'}
        req = create_req(asgi, headers=headers)
        preferred_type = req.client_prefers(['application/xhtml+xml'])
        assert preferred_type is None

    def test_range(self, asgi):
        headers = {'Range': 'bytes=10-'}
        req = create_req(asgi, headers=headers)
        assert req.range == (10, -1)

        headers = {'Range': 'bytes=10-20'}
        req = create_req(asgi, headers=headers)
        assert req.range == (10, 20)

        headers = {'Range': 'bytes=-10240'}
        req = create_req(asgi, headers=headers)
        assert req.range == (-10240, -1)

        headers = {'Range': 'bytes=0-2'}
        req = create_req(asgi, headers=headers)
        assert req.range == (0, 2)

        headers = {'Range': ''}
        req = create_req(asgi, headers=headers)
        with pytest.raises(falcon.HTTPInvalidHeader):
            req.range

        req = create_req(asgi)
        assert req.range is None

    def test_range_unit(self, asgi):
        headers = {'Range': 'bytes=10-'}
        req = create_req(asgi, headers=headers)
        assert req.range == (10, -1)
        assert req.range_unit == 'bytes'

        headers = {'Range': 'items=10-'}
        req = create_req(asgi, headers=headers)
        assert req.range == (10, -1)
        assert req.range_unit == 'items'

        headers = {'Range': ''}
        req = create_req(asgi, headers=headers)
        with pytest.raises(falcon.HTTPInvalidHeader):
            req.range_unit

        req = create_req(asgi)
        assert req.range_unit is None

    def test_range_invalid(self, asgi):
        headers = {'Range': 'bytes=10240'}
        req = create_req(asgi, headers=headers)
        with pytest.raises(falcon.HTTPBadRequest):
            req.range

        headers = {'Range': 'bytes=-'}
        expected_desc = (
            'The value provided for the "Range" header is '
            'invalid. The range offsets are missing.'
        )
        self._test_error_details(
            headers,
            'range',
            falcon.HTTPInvalidHeader,
            'Invalid header value',
            expected_desc,
            asgi,
        )

        headers = {'Range': 'bytes=--'}
        req = create_req(asgi, headers=headers)
        with pytest.raises(falcon.HTTPBadRequest):
            req.range

        headers = {'Range': 'bytes=--1'}
        req = create_req(asgi, headers=headers)
        with pytest.raises(falcon.HTTPBadRequest):
            req.range

        headers = {'Range': 'bytes=--0'}
        req = create_req(asgi, headers=headers)
        with pytest.raises(falcon.HTTPBadRequest):
            req.range

        headers = {'Range': 'bytes=-3-'}
        req = create_req(asgi, headers=headers)
        with pytest.raises(falcon.HTTPBadRequest):
            req.range

        headers = {'Range': 'bytes=-3-4'}
        req = create_req(asgi, headers=headers)
        with pytest.raises(falcon.HTTPBadRequest):
            req.range

        headers = {'Range': 'bytes=4-3'}
        req = create_req(asgi, headers=headers)
        with pytest.raises(falcon.HTTPBadRequest):
            req.range

        headers = {'Range': 'bytes=3-3-4'}
        req = create_req(asgi, headers=headers)
        with pytest.raises(falcon.HTTPBadRequest):
            req.range

        headers = {'Range': 'bytes=3-3-'}
        req = create_req(asgi, headers=headers)
        with pytest.raises(falcon.HTTPBadRequest):
            req.range

        headers = {'Range': 'bytes=3-3- '}
        req = create_req(asgi, headers=headers)
        with pytest.raises(falcon.HTTPBadRequest):
            req.range

        headers = {'Range': 'bytes=fizbit'}
        req = create_req(asgi, headers=headers)
        with pytest.raises(falcon.HTTPBadRequest):
            req.range

        headers = {'Range': 'bytes=a-'}
        req = create_req(asgi, headers=headers)
        with pytest.raises(falcon.HTTPBadRequest):
            req.range

        headers = {'Range': 'bytes=a-3'}
        req = create_req(asgi, headers=headers)
        with pytest.raises(falcon.HTTPBadRequest):
            req.range

        headers = {'Range': 'bytes=-b'}
        req = create_req(asgi, headers=headers)
        with pytest.raises(falcon.HTTPBadRequest):
            req.range

        headers = {'Range': 'bytes=3-b'}
        req = create_req(asgi, headers=headers)
        with pytest.raises(falcon.HTTPBadRequest):
            req.range

        headers = {'Range': 'bytes=x-y'}
        expected_desc = (
            'The value provided for the "Range" header is '
            'invalid. It must be a range formatted '
            'according to RFC 7233.'
        )
        self._test_error_details(
            headers,
            'range',
            falcon.HTTPInvalidHeader,
            'Invalid header value',
            expected_desc,
            asgi,
        )

        headers = {'Range': 'bytes=0-0,-1'}
        expected_desc = (
            'The value provided for the "Range" '
            'header is invalid. The value must be a '
            'continuous range.'
        )
        self._test_error_details(
            headers,
            'range',
            falcon.HTTPInvalidHeader,
            'Invalid header value',
            expected_desc,
            asgi,
        )

        headers = {'Range': '10-'}
        expected_desc = (
            'The value provided for the "Range" '
            'header is invalid. The value must be '
            "prefixed with a range unit, e.g. 'bytes='"
        )
        self._test_error_details(
            headers,
            'range',
            falcon.HTTPInvalidHeader,
            'Invalid header value',
            expected_desc,
            asgi,
        )

    def test_missing_attribute_header(self, asgi):
        req = create_req(asgi)
        assert req.range is None

        req = create_req(asgi)
        assert req.content_length is None

    def test_content_length(self, asgi):
        headers = {'content-length': '5656'}
        req = create_req(asgi, headers=headers)
        assert req.content_length == 5656

        headers = {'content-length': ''}
        req = create_req(asgi, headers=headers)
        assert req.content_length is None

    def test_bogus_content_length_nan(self, asgi):
        headers = {'content-length': 'fuzzy-bunnies'}
        expected_desc = (
            'The value provided for the '
            '"Content-Length" header is invalid. The value '
            'of the header must be a number.'
        )
        self._test_error_details(
            headers,
            'content_length',
            falcon.HTTPInvalidHeader,
            'Invalid header value',
            expected_desc,
            asgi,
        )

    def test_bogus_content_length_neg(self, asgi):
        headers = {'content-length': '-1'}
        expected_desc = (
            'The value provided for the "Content-Length" '
            'header is invalid. The value of the header '
            'must be a positive number.'
        )
        self._test_error_details(
            headers,
            'content_length',
            falcon.HTTPInvalidHeader,
            'Invalid header value',
            expected_desc,
            asgi,
        )

    @pytest.mark.parametrize(
        'header,attr',
        [
            ('Date', 'date'),
            ('If-Modified-Since', 'if_modified_since'),
            ('If-Unmodified-Since', 'if_unmodified_since'),
        ],
    )
    def test_date(self, asgi, header, attr):
        date = datetime.datetime(2013, 4, 4, 5, 19, 18, tzinfo=datetime.timezone.utc)
        date_str = 'Thu, 04 Apr 2013 05:19:18 GMT'

        headers = {header: date_str}
        req = create_req(asgi, headers=headers)
        assert getattr(req, attr) == date

    @pytest.mark.parametrize(
        'header,attr',
        [
            ('Date', 'date'),
            ('If-Modified-Since', 'if_modified_since'),
            ('If-Unmodified-Since', 'if_unmodified_since'),
        ],
    )
    def test_date_invalid(self, asgi, header, attr):
        # Date formats don't conform to RFC 1123
        headers = {header: 'Thu, 04 Apr 2013'}
        expected_desc = (
            'The value provided for the "{}" '
            'header is invalid. It must be formatted '
            'according to RFC 7231, Section 7.1.1.1'
        )

        self._test_error_details(
            headers,
            attr,
            falcon.HTTPInvalidHeader,
            'Invalid header value',
            expected_desc.format(header),
            asgi,
        )

        headers = {header: ''}
        self._test_error_details(
            headers,
            attr,
            falcon.HTTPInvalidHeader,
            'Invalid header value',
            expected_desc.format(header),
            asgi,
        )

    @pytest.mark.parametrize(
        'attr', ('date', 'if_modified_since', 'if_unmodified_since')
    )
    def test_date_missing(self, asgi, attr):
        req = create_req(asgi)
        assert getattr(req, attr) is None

    @pytest.mark.parametrize(
        'name,value,attr,default',
        [
            ('Accept', 'x-falcon', 'accept', '*/*'),
            (
                'Authorization',
                'HMAC_SHA1 c590afa9bb59191ffab30f223791e82d3fd3e3af',
                'auth',
                None,
            ),
            ('Content-Type', 'text/plain', 'content_type', None),
            ('Expect', '100-continue', 'expect', None),
            ('If-Range', 'Wed, 21 Oct 2015 07:28:00 GMT', 'if_range', None),
            (
                'User-Agent',
                'testing/3.0',
                'user_agent',
                'falcon-client/' + falcon.__version__,
            ),
            ('Referer', 'https://www.google.com/', 'referer', None),
        ],
    )
    def test_attribute_headers(self, asgi, name, value, attr, default):
        headers = {name: value}
        req = create_req(asgi, headers=headers)
        assert getattr(req, attr) == value

        req = create_req(asgi)
        assert getattr(req, attr) == default

    def test_method(self, asgi):
        assert self.req.method == 'GET'

        self.req = create_req(asgi, path='', method='HEAD')
        assert self.req.method == 'HEAD'

    def test_empty_path(self, asgi):
        self.req = create_req(asgi, path='')
        assert self.req.path == '/'

    def test_content_type_method(self, asgi):
        assert self.req.get_header('content-type') == 'text/plain'

    def test_content_length_method(self, asgi):
        assert self.req.get_header('content-length') == '4829'

    # TODO(kgriffs): Migrate to pytest and parametrized fixtures
    # to DRY things up a bit.
    @pytest.mark.parametrize('http_version', _HTTP_VERSIONS)
    def test_port_explicit(self, asgi, http_version):
        port = 9000
        req = create_req(
            asgi,
            http_version=http_version,
            port=port,
            root_path=self.root_path,
            path='/hello',
            query_string=self.qs,
            headers=self.headers,
        )

        assert req.port == port

    @pytest.mark.parametrize('http_version', _HTTP_VERSIONS)
    def test_scheme_https(self, asgi, http_version):
        scheme = 'https'
        req = create_req(
            asgi,
            http_version=http_version,
            scheme=scheme,
            root_path=self.root_path,
            path='/hello',
            query_string=self.qs,
            headers=self.headers,
        )

        assert req.scheme == scheme
        assert req.port == 443

    @pytest.mark.parametrize(
        'http_version, set_forwarded_proto',
        list(itertools.product(_HTTP_VERSIONS, [True, False])),
    )
    def test_scheme_http(self, asgi, http_version, set_forwarded_proto):
        scheme = 'http'
        forwarded_scheme = 'HttPs'

        headers = dict(self.headers)

        if set_forwarded_proto:
            headers['X-Forwarded-Proto'] = forwarded_scheme

        req = create_req(
            asgi,
            http_version=http_version,
            scheme=scheme,
            root_path=self.root_path,
            path='/hello',
            query_string=self.qs,
            headers=headers,
        )

        assert req.scheme == scheme
        assert req.port == 80

        if set_forwarded_proto:
            assert req.forwarded_scheme == forwarded_scheme.lower()
        else:
            assert req.forwarded_scheme == scheme

    @pytest.mark.parametrize('http_version', _HTTP_VERSIONS)
    def test_netloc_default_port(self, asgi, http_version):
        req = create_req(
            asgi,
            http_version=http_version,
            root_path=self.root_path,
            path='/hello',
            query_string=self.qs,
            headers=self.headers,
        )

        assert req.netloc == 'falconframework.org'

    @pytest.mark.parametrize('http_version', _HTTP_VERSIONS)
    def test_netloc_nondefault_port(self, asgi, http_version):
        req = create_req(
            asgi,
            http_version=http_version,
            port='8080',
            root_path=self.root_path,
            path='/hello',
            query_string=self.qs,
            headers=self.headers,
        )

        assert req.netloc == 'falconframework.org:8080'

    @pytest.mark.parametrize('http_version', _HTTP_VERSIONS)
    def test_netloc_from_env(self, asgi, http_version):
        port = 9000
        host = 'example.org'

        req = create_req(
            asgi,
            http_version=http_version,
            host=host,
            port=port,
            root_path=self.root_path,
            path='/hello',
            query_string=self.qs,
            headers=self.headers,
        )

        assert req.port == port
        assert req.netloc == '{}:{}'.format(host, port)

    def test_app_present(self, asgi):
        req = create_req(asgi, root_path='/moving-pictures')
        with pytest.warns(DeprecatedWarning):
            assert req.app == '/moving-pictures'
        assert req.root_path == '/moving-pictures'

    def test_app_blank(self, asgi):
        req = create_req(asgi, root_path='')
        with pytest.warns(DeprecatedWarning):
            assert req.app == ''
        assert req.root_path == ''

    @pytest.mark.parametrize(
        'etag,expected_value',
        [
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
            ('W/"67ab43"', [_make_etag('67ab43', is_weak=True)]),
            ('w/"67ab43"', [_make_etag('67ab43', is_weak=True)]),
            (' w/"67ab43"', [_make_etag('67ab43', is_weak=True)]),
            ('w/"67ab43" ', [_make_etag('67ab43', is_weak=True)]),
            ('w/"67ab43 " ', [_make_etag('67ab43 ', is_weak=True)]),
            ('"67ab43"', [_make_etag('67ab43')]),
            (' "67ab43"', [_make_etag('67ab43')]),
            (' "67ab43" ', [_make_etag('67ab43')]),
            ('"67ab43" ', [_make_etag('67ab43')]),
            ('" 67ab43" ', [_make_etag(' 67ab43')]),
            ('67ab43"', [_make_etag('67ab43"')]),
            ('"67ab43', [_make_etag('"67ab43')]),
            ('67ab43', [_make_etag('67ab43')]),
            ('67ab43 ', [_make_etag('67ab43')]),
            ('  67ab43 ', [_make_etag('67ab43')]),
            ('  67ab43', [_make_etag('67ab43')]),
            (
                # NOTE(kgriffs): To simplify parsing and improve performance, we
                #   do not attempt to handle unquoted entity-tags when there is
                #   a list; it is non-standard anyway, and has been since 1999.
                'W/"67ab43", "54ed21", junk"F9,22", junk "41, 7F", '
                'unquoted, w/"22, 41, 7F", "", W/""',
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
                ],
            ),
        ],
    )
    @pytest.mark.parametrize(
        'name,attr',
        [
            ('If-Match', 'if_match'),
            ('If-None-Match', 'if_none_match'),
        ],
    )
    def test_etag(self, asgi, name, attr, etag, expected_value):
        headers = {name: etag}
        req = create_req(asgi, headers=headers)

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

    def test_etag_is_missing(self, asgi):
        # NOTE(kgriffs): Loop in order to test caching
        for __ in range(3):
            assert self.req.if_match is None
            assert self.req.if_none_match is None

    @pytest.mark.parametrize('header_value', ['', ' ', '  '])
    def test_etag_parsing_helper(self, asgi, header_value):
        # NOTE(kgriffs): Test a couple of cases that are not directly covered
        #   elsewhere (but that we want the helper to still support
        #   for the sake of avoiding surprises if they are ever called without
        #   preflighting the header value).

        assert _parse_etags(header_value) is None

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _test_error_details(
        self, headers, attr_name, error_type, title, description, asgi
    ):
        req = create_req(asgi, headers=headers)

        try:
            getattr(req, attr_name)
            pytest.fail('{} not raised'.format(error_type.__name__))
        except error_type as ex:
            assert ex.title == title
            assert ex.description == description
