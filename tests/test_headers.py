from collections import defaultdict
from datetime import datetime

import pytest

import falcon
from falcon import testing
from falcon.util.deprecation import DeprecatedWarning
from falcon.util.misc import _utcnow

SAMPLE_BODY = testing.rand_string(0, 128 * 1024)


@pytest.fixture
def client(asgi, util):
    app = util.create_app(asgi)
    return testing.TestClient(app)


class XmlResource:
    def __init__(self, content_type):
        self.content_type = content_type

    def on_get(self, req, resp):
        resp.set_header('content-type', self.content_type)


class HeaderHelpersResource:
    def __init__(self, last_modified=None):
        if last_modified is not None:
            self.last_modified = last_modified
        else:
            self.last_modified = _utcnow()

    def _overwrite_headers(self, req, resp):
        resp.content_type = 'x-falcon/peregrine'
        resp.cache_control = ['no-store']

    def on_get(self, req, resp):
        resp.text = '{}'
        resp.content_type = 'x-falcon/peregrine'
        resp.cache_control = [
            'public',
            'private',
            'no-cache',
            'no-store',
            'must-revalidate',
            'proxy-revalidate',
            'max-age=3600',
            's-maxage=60',
            'no-transform',
        ]

        resp.etag = None  # Header not set yet, so should be a noop
        resp.etag = 'fa0d1a60ef6616bb28038515c8ea4cb2'
        resp.last_modified = self.last_modified
        resp.retry_after = 3601

        # Relative URI's are OK per
        # https://datatracker.ietf.org/doc/html/rfc7231#section-7.1.2
        resp.location = '/things/87'
        resp.content_location = '/things/78'

        resp.downloadable_as = None  # Header not set yet, so should be a noop
        resp.downloadable_as = 'Some File.zip'

        if req.range_unit is None or req.range_unit == 'bytes':
            # bytes 0-499/10240
            resp.content_range = (0, 499, 10 * 1024)
        else:
            resp.content_range = (0, 25, 100, req.range_unit)

        resp.accept_ranges = None  # Header not set yet, so should be a noop
        resp.accept_ranges = 'bytes'

        # Test the removal of custom headers
        resp.set_header('X-Client-Should-Never-See-This', 'abc')
        assert resp.get_header('x-client-should-never-see-this') == 'abc'
        resp.delete_header('x-client-should-never-see-this')

        self.req = req
        self.resp = resp

    def on_head(self, req, resp):
        resp.set_header('Content-Type', 'x-swallow/unladen')
        resp.set_header('X-Auth-Token', 'setecastronomy')
        resp.set_header('X-AUTH-TOKEN', 'toomanysecrets')

        resp.location = '/things/87'
        del resp.location

        self._overwrite_headers(req, resp)

        self.resp = resp

    def on_post(self, req, resp):
        resp.set_headers(
            [
                ('CONTENT-TYPE', 'x-swallow/unladen'),
                ('X-Auth-Token', 'setecastronomy'),
                ('X-AUTH-TOKEN', 'toomanysecrets'),
            ]
        )

        self._overwrite_headers(req, resp)

        self.resp = resp

    def on_put(self, req, resp):
        resp.set_headers(
            {'CONTENT-TYPE': 'x-swallow/unladen', 'X-aUTH-tOKEN': 'toomanysecrets'}
        )

        self._overwrite_headers(req, resp)

        self.resp = resp


class LocationHeaderUnicodeResource:
    URL1 = '/\u00e7runchy/bacon'
    URL2 = 'ab\u00e7'

    def on_get(self, req, resp):
        resp.location = self.URL1
        resp.content_location = self.URL2

    def on_head(self, req, resp):
        resp.location = self.URL2
        resp.content_location = self.URL1


class UnicodeHeaderResource:
    def on_connect(self, req, resp):
        # A way to CONNECT with people.
        resp.set_header('X-Clinking-Beer-Mugs', '🍺')

    def on_get(self, req, resp):
        resp.set_headers(
            [
                ('X-auTH-toKEN', 'toomanysecrets'),
                ('Content-TYpE', 'application/json'),
                ('X-symbOl', '@'),
            ]
        )

    def on_patch(self, req, resp):
        resp.set_headers(
            [
                ('X-Thing', '\x01\x02\xff'),
            ]
        )

    def on_post(self, req, resp):
        resp.set_headers(
            [
                ('X-symb\u00f6l', 'thing'),
            ]
        )

    def on_put(self, req, resp):
        resp.set_headers(
            [
                ('X-Thing', '\u00ff'),
            ]
        )


class VaryHeaderResource:
    def __init__(self, vary):
        self.vary = vary

    def on_get(self, req, resp):
        resp.text = '{}'
        resp.vary = self.vary


class LinkHeaderResource:
    def __init__(self):
        self._links = []

    def add_link(self, *args, **kwargs):
        self._links.append(('add_link', args, kwargs))

    def append_link(self, *args, **kwargs):
        self._links.append(('append_link', args, kwargs))

    def on_get(self, req, resp):
        resp.text = '{}'

        for method_name, args, kwargs in self._links:
            append_method = getattr(resp, method_name)
            if method_name == 'append_link':
                append_method(*args, **kwargs)
            else:
                with pytest.warns(
                    DeprecatedWarning,
                    match='Call to deprecated function add_link(...)',
                ):
                    append_method(*args, **kwargs)


class AppendHeaderResource:
    def on_get(self, req, resp):
        resp.append_header('X-Things', 'thing-1')
        resp.append_header('X-THINGS', 'thing-2')
        resp.append_header('x-thiNgs', 'thing-3')

    def on_head(self, req, resp):
        resp.set_header('X-things', 'thing-1')
        resp.append_header('X-THINGS', 'thing-2')
        resp.append_header('x-thiNgs', 'thing-3')

    def on_post(self, req, resp):
        resp.append_header('X-Things', 'thing-1')

        c1 = (
            'ut_existing_user=1; expires=Mon, 14-Jan-2019 21:20:08 GMT;'
            ' Max-Age=600; path=/'
        )
        resp.append_header('Set-Cookie', c1)
        c2 = 'partner_source=deleted; expires=Thu, 01-Jan-1970 00:00:01 GMT; Max-Age=0'
        resp.append_header('seT-cookie', c2)


class RemoveHeaderResource:
    def __init__(self, with_double_quotes):
        self.with_double_quotes = with_double_quotes

    def on_get(self, req, resp):
        etag = 'fa0d1a60ef6616bb28038515c8ea4cb2'
        if self.with_double_quotes:
            etag = '"' + etag + '"'

        resp.etag = etag
        assert resp.etag == '"fa0d1a60ef6616bb28038515c8ea4cb2"'
        resp.etag = None

        resp.downloadable_as = 'foo.zip'
        assert resp.downloadable_as == 'attachment; filename="foo.zip"'
        resp.downloadable_as = None


class DownloadableResource:
    def __init__(self, filename):
        self.filename = filename

    def on_get(self, req, resp):
        resp.text = 'Hello, World!\n'
        resp.content_type = falcon.MEDIA_TEXT
        resp.downloadable_as = self.filename


class ViewableResource:
    def __init__(self, filename):
        self.filename = filename

    def on_get(self, req, resp):
        resp.text = 'Hello, World!\n'
        resp.content_type = falcon.MEDIA_TEXT
        resp.viewable_as = self.filename


class ContentLengthHeaderResource:
    def __init__(self, content_length, body=None, data=None):
        self._content_length = content_length
        self._body = body
        self._data = data

    def on_get(self, req, resp):
        resp.content_length = self._content_length

        if self._body:
            resp.text = self._body

        if self._data:
            resp.data = self._data

    def on_head(self, req, resp):
        resp.content_length = self._content_length


class ExpiresHeaderResource:
    def __init__(self, expires):
        self._expires = expires

    def on_get(self, req, resp):
        resp.expires = self._expires


class CustomHeaders:
    def items(self):
        return [('test-header', 'test-value')]


class CustomHeadersNotCallable:
    def __init__(self):
        self.items = {'test-header': 'test-value'}


class CustomHeadersResource:
    def on_get(self, req, resp):
        headers = CustomHeaders()
        resp.set_headers(headers)

    def on_post(self, req, resp):
        resp.set_headers(CustomHeadersNotCallable())


class HeadersDebugResource:
    def on_get(self, req, resp):
        resp.media = {
            'raw': req.headers,
            'lower': req.headers_lower,
        }

    def on_get_header(self, req, resp, header):
        resp.media = {header.lower(): req.get_header(header)}


class TestHeaders:
    def test_content_length(self, client):
        resource = testing.SimpleTestResource(body=SAMPLE_BODY)
        client.app.add_route('/', resource)
        result = client.simulate_get()

        content_length = str(len(SAMPLE_BODY))
        assert result.headers['Content-Length'] == content_length

    def test_declared_content_length_on_head(self, client):
        client.app.add_route('/', ContentLengthHeaderResource(42))
        result = client.simulate_head()
        assert result.headers['Content-Length'] == '42'

    def test_declared_content_length_overridden_by_no_body(self, client):
        client.app.add_route('/', ContentLengthHeaderResource(42))
        result = client.simulate_get()
        assert result.headers['Content-Length'] == '0'

    def test_declared_content_length_overridden_by_body_length(self, client):
        resource = ContentLengthHeaderResource(42, body=SAMPLE_BODY)
        client.app.add_route('/', resource)
        result = client.simulate_get()

        assert result.headers['Content-Length'] == str(len(SAMPLE_BODY))

    def test_declared_content_length_overridden_by_data_length(self, client):
        data = SAMPLE_BODY.encode()

        resource = ContentLengthHeaderResource(42, data=data)
        client.app.add_route('/', resource)
        result = client.simulate_get()

        assert result.headers['Content-Length'] == str(len(data))

    def test_expires_header(self, client):
        expires = datetime(2013, 1, 1, 10, 30, 30)
        client.app.add_route('/', ExpiresHeaderResource(expires))
        result = client.simulate_get()

        assert result.headers['Expires'] == 'Tue, 01 Jan 2013 10:30:30 GMT'

    def test_get_header_as_int(self, client):
        resource = testing.SimpleTestResource(body=SAMPLE_BODY)
        client.app.add_route('/', resource)
        request_headers = {
            'X-Int-Val': '42',
            'X-Str-Val': 'test-val',
            'X-Float-Val': '3.14',
        }
        client.simulate_get(headers=request_headers)

        req = resource.captured_req
        value = req.get_header_as_int('X-Int-Val')
        assert value == 42

        value = req.get_header_as_int('X-Not-Found')
        assert value is None

        with pytest.raises(falcon.HTTPInvalidHeader) as exc_info:
            req.get_header_as_int('X-Float-Val')
        assert exc_info.value.args[0] == 'The value of the header must be an integer.'

        with pytest.raises(falcon.HTTPInvalidHeader) as exc_info:
            req.get_header_as_int('X-Str-Val')
        assert exc_info.value.args[0] == 'The value of the header must be an integer.'

        with pytest.raises(falcon.HTTPMissingHeader) as exc_info:
            req.get_header_as_int('X-Not-Found', required=True)

    def test_default_value(self, client):
        resource = testing.SimpleTestResource(body=SAMPLE_BODY)
        client.app.add_route('/', resource)
        client.simulate_get()

        req = resource.captured_req
        value = req.get_header('X-Not-Found') or '876'
        assert value == '876'

        value = req.get_header('X-Not-Found', default='some-value')
        assert value == 'some-value'

        # Exercise any result caching and associated abuse mitigations
        for i in range(10000):
            assert req.get_header('X-Not-Found-{0}'.format(i)) is None

    @pytest.mark.parametrize('with_double_quotes', [True, False])
    def test_unset_header(self, client, with_double_quotes):
        client.app.add_route('/', RemoveHeaderResource(with_double_quotes))
        result = client.simulate_get()

        assert 'Etag' not in result.headers
        assert 'Content-Disposition' not in result.headers

    def test_required_header(self, client):
        resource = testing.SimpleTestResource(body=SAMPLE_BODY)
        client.app.add_route('/', resource)
        client.simulate_get()

        try:
            req = resource.captured_req
            req.get_header('X-Not-Found', required=True)
            pytest.fail('falcon.HTTPMissingHeader not raised')
        except falcon.HTTPMissingHeader as ex:
            assert isinstance(ex, falcon.HTTPBadRequest)
            assert ex.title == 'Missing header value'
            expected_desc = 'The "X-Not-Found" header is required.'
            assert ex.description == expected_desc

    @pytest.mark.parametrize('status', (falcon.HTTP_204, falcon.HTTP_304))
    def test_no_content_length(self, client, status):
        client.app.add_route('/xxx', testing.SimpleTestResource(status=status))

        result = client.simulate_get('/xxx')
        assert 'Content-Length' not in result.headers
        assert not result.content

    def test_content_header_missing(self, client):
        environ = testing.create_environ()
        req = falcon.Request(environ)
        for header in ('Content-Type', 'Content-Length'):
            assert req.get_header(header) is None

    def test_passthrough_request_headers(self, client):
        resource = testing.SimpleTestResource(body=SAMPLE_BODY)
        client.app.add_route('/', resource)
        request_headers = {
            'X-Auth-Token': 'Setec Astronomy',
            'Content-Type': 'text/plain; charset=utf-8',
        }
        client.simulate_get(headers=request_headers)

        for name, expected_value in request_headers.items():
            actual_value = resource.captured_req.get_header(name)
            assert actual_value == expected_value

        client.simulate_get(headers=resource.captured_req.headers)

        # Validate that the property has been cached
        assert resource.captured_req.headers is resource.captured_req.headers

        # Compare the request HTTP headers with the original headers
        for name, expected_value in request_headers.items():
            actual_value = resource.captured_req.get_header(name)
            assert actual_value == expected_value

    def test_headers_as_list(self, client):
        headers = [
            ('Client-ID', '692ba466-74bb-11e3-bf3f-7567c531c7ca'),
            ('Accept', 'audio/*; q=0.2, audio/basic'),
        ]

        # Unit test
        environ = testing.create_environ(headers=headers)
        req = falcon.Request(environ)

        for name, value in headers:
            assert (name.upper(), value) in req.headers.items()
            assert (name.lower(), value) in req.headers_lower.items()

        # Functional test
        client.app.add_route('/', testing.SimpleTestResource(headers=headers))
        result = client.simulate_get()

        for name, value in headers:
            assert result.headers[name] == value

    def test_default_media_type(self, client):
        resource = testing.SimpleTestResource(body='Hello world!')
        self._check_header(client, resource, 'Content-Type', falcon.DEFAULT_MEDIA_TYPE)

    @pytest.mark.parametrize('asgi', [True, False])
    @pytest.mark.parametrize(
        'content_type,body',
        [
            ('text/plain; charset=UTF-8', 'Hello Unicode! \U0001f638'),
            # NOTE(kgriffs): This only works because the client defaults to
            # ISO-8859-1 IFF the media type is 'text'.
            ('text/plain', 'Hello ISO-8859-1!'),
        ],
    )
    def test_override_default_media_type(self, asgi, util, client, content_type, body):
        client.app = util.create_app(asgi=asgi, media_type=content_type)
        client.app.add_route('/', testing.SimpleTestResource(body=body))
        result = client.simulate_get()

        assert result.text == body
        assert result.headers['Content-Type'] == content_type

    @pytest.mark.parametrize('asgi', [True, False])
    def test_override_default_media_type_missing_encoding(self, asgi, util, client):
        body = '{"msg": "Hello Unicode! \U0001f638"}'

        client.app = util.create_app(asgi=asgi, media_type='application/json')
        client.app.add_route('/', testing.SimpleTestResource(body=body))
        result = client.simulate_get()

        assert result.content == body.encode('utf-8')
        assert isinstance(result.text, str)
        assert result.text == body
        assert result.json == {'msg': 'Hello Unicode! \U0001f638'}

    def test_response_header_helpers_on_get(self, client):
        last_modified = datetime(2013, 1, 1, 10, 30, 30)
        resource = HeaderHelpersResource(last_modified)
        client.app.add_route('/', resource)
        result = client.simulate_get()

        resp = resource.resp

        content_type = 'x-falcon/peregrine'
        assert resp.content_type == content_type
        assert result.headers['Content-Type'] == content_type
        assert (
            result.headers['Content-Disposition']
            == 'attachment; filename="Some File.zip"'
        )

        cache_control = (
            'public, private, no-cache, no-store, '
            'must-revalidate, proxy-revalidate, max-age=3600, '
            's-maxage=60, no-transform'
        )

        assert resp.cache_control == cache_control
        assert result.headers['Cache-Control'] == cache_control

        etag = '"fa0d1a60ef6616bb28038515c8ea4cb2"'
        assert resp.etag == etag
        assert result.headers['Etag'] == etag

        lm_date = 'Tue, 01 Jan 2013 10:30:30 GMT'
        assert resp.last_modified == lm_date
        assert result.headers['Last-Modified'] == lm_date

        assert resp.retry_after == '3601'
        assert result.headers['Retry-After'] == '3601'

        assert resp.location == '/things/87'
        assert result.headers['Location'] == '/things/87'

        assert resp.content_location == '/things/78'
        assert result.headers['Content-Location'] == '/things/78'

        content_range = 'bytes 0-499/10240'
        assert resp.content_range == content_range
        assert result.headers['Content-Range'] == content_range

        resp.content_range = (1, 499, 10 * 1024, 'bytes')
        assert isinstance(resp.content_range, str)
        assert resp.content_range == 'bytes 1-499/10240'

        assert resp.accept_ranges == 'bytes'
        assert result.headers['Accept-Ranges'] == 'bytes'

        req_headers = {'Range': 'items=0-25'}
        result = client.simulate_get(headers=req_headers)
        assert result.headers['Content-Range'] == 'items 0-25/100'

        # Check for duplicate headers
        hist = defaultdict(lambda: 0)
        for name, value in result.headers.items():
            hist[name] += 1
            assert 1 == hist[name]

    @pytest.mark.parametrize(
        'filename,expected',
        [
            ('report.csv', 'attachment; filename="report.csv"'),
            ('Hello World.txt', 'attachment; filename="Hello World.txt"'),
            (
                'Bold Digit 𝟏.txt',
                'attachment; filename=Bold_Digit_1.txt; '
                "filename*=UTF-8''Bold%20Digit%20%F0%9D%9F%8F.txt",
            ),
            (
                'Ångström unit.txt',
                'attachment; filename=A_ngstro_m_unit.txt; '
                "filename*=UTF-8''%C3%85ngstr%C3%B6m%20unit.txt",
            ),
            ('one,two.txt', 'attachment; filename="one,two.txt"'),
            (
                '½,²⁄₂.txt',
                'attachment; filename=1_2_2_2.txt; '
                "filename*=UTF-8''%C2%BD%2C%C2%B2%E2%81%84%E2%82%82.txt",
            ),
            ('[foo] @ bar.txt', 'attachment; filename="[foo] @ bar.txt"'),
            (
                '[fòó]@bàr,bäz.txt',
                'attachment; filename=_fo_o___ba_r_ba_z.txt; '
                "filename*=UTF-8''%5Bf%C3%B2%C3%B3%5D%40b%C3%A0r%2Cb%C3%A4z.txt",
            ),
        ],
    )
    def test_content_disposition_attachment_header(self, client, filename, expected):
        resource = DownloadableResource(filename)
        client.app.add_route('/', resource)
        resp = client.simulate_get()

        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == expected

    @pytest.mark.parametrize(
        'filename,expected',
        [
            ('report.csv', 'inline; filename="report.csv"'),
            ('Hello World.txt', 'inline; filename="Hello World.txt"'),
            (
                'Bold Digit 𝟏.txt',
                'inline; filename=Bold_Digit_1.txt; '
                "filename*=UTF-8''Bold%20Digit%20%F0%9D%9F%8F.txt",
            ),
        ],
    )
    def test_content_disposition_inline_header(self, client, filename, expected):
        resource = ViewableResource(filename)
        client.app.add_route('/', resource)
        resp = client.simulate_get()

        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == expected

    def test_request_latin1_headers(self, client):
        client.app.add_route('/headers', HeadersDebugResource())
        client.app.add_route(
            '/headers/{header}', HeadersDebugResource(), suffix='header'
        )

        headers = {
            'User-Agent': 'Mosaic/0.9',
            'X-Latin1-Header': 'Förmånsrätt',
            'X-Size': 'groß',
        }
        resp = client.simulate_get('/headers', headers=headers)
        assert resp.status_code == 200

        headers_lower = {
            'host': 'falconframework.org',
            'user-agent': 'Mosaic/0.9',
            'x-latin1-header': 'Förmånsrätt',
            'x-size': 'groß',
        }

        headers_upper = {key.upper(): value for key, value in headers_lower.items()}

        headers_received = resp.json

        if client.app._ASGI:
            assert resp.json['raw'] == headers_lower
        else:
            assert resp.json['raw'] == headers_upper

        assert headers_received['lower'] == headers_lower

        resp = client.simulate_get('/headers/X-Latin1-Header', headers=headers)
        assert resp.json == {'x-latin1-header': 'Förmånsrätt'}
        resp = client.simulate_get('/headers/X-Size', headers=headers)
        assert resp.json == {'x-size': 'groß'}

    def test_unicode_location_headers(self, client):
        client.app.add_route('/', LocationHeaderUnicodeResource())

        result = client.simulate_get()
        assert result.headers['Location'] == '/%C3%A7runchy/bacon'
        assert result.headers['Content-Location'] == 'ab%C3%A7'

        # Test with the values swapped
        result = client.simulate_head()
        assert result.headers['Content-Location'] == '/%C3%A7runchy/bacon'
        assert result.headers['Location'] == 'ab%C3%A7'

    def test_unicode_headers_contain_only_ascii(self, client):
        client.app.add_route('/', UnicodeHeaderResource())

        result = client.simulate_get('/')

        assert result.headers['Content-Type'] == 'application/json'
        assert result.headers['X-Auth-Token'] == 'toomanysecrets'
        assert result.headers['X-Symbol'] == '@'

    @pytest.mark.parametrize('method', ['CONNECT', 'PATCH', 'POST', 'PUT'])
    def test_unicode_headers_contain_non_ascii(self, method, client):
        app = client.app
        app.add_route('/', UnicodeHeaderResource())

        if method == 'CONNECT':
            # NOTE(vytas): Response headers cannot be encoded to Latin-1.
            if not app._ASGI:
                pytest.skip('wsgiref.validate sees no evil here')

            # NOTE(vytas): Shouldn't this result in an HTTP 500 instead of
            #   bubbling up a ValueError to the app server?
            with pytest.raises(ValueError):
                client.simulate_request(method, '/')
        elif method == 'PUT':
            # NOTE(vytas): Latin-1 header values are allowed.
            resp = client.simulate_request(method, '/')
            assert resp.headers
        else:
            if app._ASGI:
                # NOTE(kgriffs): Unlike PEP-3333, the ASGI spec requires the
                #   app to encode header names and values to a byte string. This
                #   gives Falcon the opportunity to verify the character set
                #   in the process and raise an error as appropriate.
                error_type = ValueError
            else:
                # NOTE(kgriffs): The wsgiref validator that is integrated into
                #   Falcon's testing framework will catch this. However, Falcon
                #   itself does not do the check to avoid potential overhead
                #   in a production deployment.
                error_type = AssertionError

            pattern = 'Bad header name' if method == 'POST' else 'Bad header value'

            with pytest.raises(error_type, match=pattern):
                client.simulate_request(method, '/')

    def test_response_set_and_get_header(self, client):
        resource = HeaderHelpersResource()
        client.app.add_route('/', resource)

        for method in ('HEAD', 'POST', 'PUT'):
            result = client.simulate_request(method=method)

            content_type = 'x-falcon/peregrine'
            assert result.headers['Content-Type'] == content_type
            assert resource.resp.get_header('content-TyPe') == content_type

            content_type_alt = 'x-falcon/merlin'
            value = resource.resp.get_header('Content-Type', default=content_type_alt)
            assert value == content_type

            assert result.headers['Cache-Control'] == 'no-store'
            assert result.headers['X-Auth-Token'] == 'toomanysecrets'

            assert resource.resp.location is None
            assert resource.resp.get_header('X-Header-Not-Set') is None
            assert resource.resp.get_header('X-Header-Not-Set', 'Yes') == 'Yes'
            assert resource.resp.get_header('X-Header-Not-Set', default='') == ''

            value = resource.resp.get_header(
                'X-Header-Not-Set', default=content_type_alt
            )
            assert value == content_type_alt

            # Check for duplicate headers
            hist = defaultdict(int)
            for name, value in result.headers.items():
                hist[name] += 1
                assert hist[name] == 1

            # Ensure that deleted headers were not sent
            assert resource.resp.get_header('x-client-should-never-see-this') is None

    def test_response_append_header(self, client):
        client.app.add_route('/', AppendHeaderResource())

        for method in ('HEAD', 'GET'):
            result = client.simulate_request(method=method)
            value = result.headers['x-things']
            assert value == 'thing-1, thing-2, thing-3'

        result = client.simulate_request(method='POST')
        assert result.headers['x-things'] == 'thing-1'
        assert result.cookies['ut_existing_user'].max_age == 600
        assert result.cookies['partner_source'].max_age == 0

    @pytest.mark.parametrize('header_name', ['Set-Cookie', 'set-cookie', 'seT-cookie'])
    @pytest.mark.parametrize('error_type', [ValueError, falcon.HeaderNotSupported])
    def test_set_cookie_disallowed(self, client, header_name, error_type):
        resp = falcon.Response()

        cookie = (
            'ut_existing_user=1; expires=Mon, 14-Jan-2019 21:20:08 GMT; '
            'Max-Age=600; path=/'
        )

        with pytest.raises(error_type):
            resp.set_header(header_name, cookie)

        with pytest.raises(error_type):
            resp.set_headers([(header_name, cookie)])

        with pytest.raises(error_type):
            resp.get_header(header_name)

        with pytest.raises(error_type):
            resp.delete_header(header_name)

    def test_vary_star(self, client):
        client.app.add_route('/', VaryHeaderResource(['*']))
        result = client.simulate_get()
        assert result.headers['vary'] == '*'

    @pytest.mark.parametrize(
        'vary,expected_value',
        [
            (['accept-encoding'], 'accept-encoding'),
            (('accept-encoding', 'x-auth-token'), 'accept-encoding, x-auth-token'),
        ],
    )
    def test_vary_header(self, client, vary, expected_value):
        resource = VaryHeaderResource(vary)
        self._check_header(client, resource, 'Vary', expected_value)

    def test_content_type_no_body(self, client):
        client.app.add_route('/', testing.SimpleTestResource())
        result = client.simulate_get()

        # NOTE(kgriffs): Even when there is no body, Content-Type
        # should still be included per wsgiref.validate
        assert 'Content-Type' in result.headers
        assert result.headers['Content-Length'] == '0'

    @pytest.mark.parametrize('status', (falcon.HTTP_204, falcon.HTTP_304))
    def test_no_content_type(self, client, status):
        client.app.add_route('/', testing.SimpleTestResource(status=status))

        result = client.simulate_get()
        assert 'Content-Type' not in result.headers

    def test_custom_content_type(self, client):
        content_type = 'application/xml; charset=utf-8'
        resource = XmlResource(content_type)
        self._check_header(client, resource, 'Content-Type', content_type)

    def test_append_link_single(self, client):
        expected_value = '</things/2842>; rel=next'

        resource = LinkHeaderResource()
        resource.append_link('/things/2842', 'next')

        self._check_link_header(client, resource, expected_value)

    def test_append_link_multiple(self, client):
        expected_value = (
            '</things/2842>; rel=next, '
            + '<http://%C3%A7runchy/bacon>; rel=contents, '
            + '<ab%C3%A7>; rel="http://example.com/ext-type", '
            + '<ab%C3%A7>; rel="http://example.com/%C3%A7runchy", '
            + '<ab%C3%A7>; rel="https://example.com/too-%C3%A7runchy", '
            + '</alt-thing>; rel="alternate http://example.com/%C3%A7runchy"'
        )

        uri = 'ab\u00e7'

        resource = LinkHeaderResource()
        resource.append_link('/things/2842', 'next')
        resource.append_link('http://\u00e7runchy/bacon', 'contents')
        resource.append_link(uri, 'http://example.com/ext-type')
        resource.append_link(uri, 'http://example.com/\u00e7runchy')
        resource.append_link(uri, 'https://example.com/too-\u00e7runchy')
        resource.append_link('/alt-thing', 'alternate http://example.com/\u00e7runchy')

        self._check_link_header(client, resource, expected_value)

    def test_append_link_with_title(self, client):
        expected_value = '</related/thing>; rel=item; title="A related thing"'

        resource = LinkHeaderResource()
        resource.append_link('/related/thing', 'item', title='A related thing')

        self._check_link_header(client, resource, expected_value)

    def test_append_link_with_title_star(self, client):
        expected_value = (
            '</related/thing>; rel=item; '
            "title*=UTF-8''A%20related%20thing, "
            '</%C3%A7runchy/thing>; rel=item; '
            "title*=UTF-8'en'A%20%C3%A7runchy%20thing"
        )

        resource = LinkHeaderResource()
        resource.append_link(
            '/related/thing', 'item', title_star=('', 'A related thing')
        )

        resource.append_link(
            '/\u00e7runchy/thing', 'item', title_star=('en', 'A \u00e7runchy thing')
        )

        self._check_link_header(client, resource, expected_value)

    def test_append_link_with_anchor(self, client):
        expected_value = '</related/thing>; rel=item; anchor="/some%20thing/or-other"'

        resource = LinkHeaderResource()
        resource.append_link('/related/thing', 'item', anchor='/some thing/or-other')

        self._check_link_header(client, resource, expected_value)

    def test_append_link_with_hreflang(self, client):
        expected_value = '</related/thing>; rel=about; hreflang=en'

        resource = LinkHeaderResource()
        resource.append_link('/related/thing', 'about', hreflang='en')

        self._check_link_header(client, resource, expected_value)

    def test_append_link_with_hreflang_multi(self, client):
        expected_value = '</related/thing>; rel=about; hreflang=en-GB; hreflang=de'

        resource = LinkHeaderResource()
        resource.append_link('/related/thing', 'about', hreflang=('en-GB', 'de'))

        self._check_link_header(client, resource, expected_value)

    def test_append_link_with_type_hint(self, client):
        expected_value = (
            '</related/thing>; rel=alternate; type="video/mp4; codecs=avc1.640028"'
        )

        resource = LinkHeaderResource()
        resource.append_link(
            '/related/thing', 'alternate', type_hint='video/mp4; codecs=avc1.640028'
        )

        self._check_link_header(client, resource, expected_value)

    def test_append_link_complex(self, client):
        expected_value = (
            '</related/thing>; rel=alternate; '
            'title="A related thing"; '
            "title*=UTF-8'en'A%20%C3%A7runchy%20thing; "
            'type="application/json"; '
            'hreflang=en-GB; hreflang=de'
        )

        resource = LinkHeaderResource()
        resource.append_link(
            '/related/thing',
            'alternate',
            title='A related thing',
            hreflang=('en-GB', 'de'),
            type_hint='application/json',
            title_star=('en', 'A \u00e7runchy thing'),
        )

        self._check_link_header(client, resource, expected_value)

    @pytest.mark.parametrize(
        'crossorigin,expected_value',
        [
            (None, '</related/thing>; rel=alternate'),
            ('anonymous', '</related/thing>; rel=alternate; crossorigin'),
            ('Anonymous', '</related/thing>; rel=alternate; crossorigin'),
            ('AnOnYmOUs', '</related/thing>; rel=alternate; crossorigin'),
            (
                'Use-Credentials',
                '</related/thing>; rel=alternate; crossorigin="use-credentials"',
            ),
            (
                'use-credentials',
                '</related/thing>; rel=alternate; crossorigin="use-credentials"',
            ),
        ],
    )
    def test_append_link_crossorigin(self, client, crossorigin, expected_value):
        resource = LinkHeaderResource()
        resource.append_link('/related/thing', 'alternate', crossorigin=crossorigin)

        self._check_link_header(client, resource, expected_value)

    @pytest.mark.parametrize(
        'crossorigin',
        [
            '*',
            'Allow-all',
            'Lax',
            'MUST-REVALIDATE',
            'Strict',
            'deny',
        ],
    )
    def test_append_link_invalid_crossorigin_value(self, crossorigin):
        resp = falcon.Response()

        with pytest.raises(ValueError):
            resp.append_link('/related/resource', 'next', crossorigin=crossorigin)

    def test_append_link_with_link_extension(self, client):
        expected_value = '</related/thing>; rel=item; sizes=72x72'

        resource = LinkHeaderResource()
        resource.append_link(
            '/related/thing', 'item', link_extension=[('sizes', '72x72')]
        )

        self._check_link_header(client, resource, expected_value)

    def test_content_length_options(self, client):
        result = client.simulate_options()

        content_length = str(len(falcon.HTTPNotFound().to_json()))
        assert result.headers['Content-Length'] == content_length

    def test_set_headers_with_custom_class(self, client):
        client.app.add_route('/', CustomHeadersResource())

        result = client.simulate_get('/')

        assert 'test-header' in result.headers
        assert result.headers['test-header'] == 'test-value'

    def test_headers_with_custom_class_not_callable(self, client):
        client.app.add_route('/', CustomHeadersResource())

        result = client.simulate_post('/')

        assert 'test-header' not in result.headers

    def test_request_multiple_header(self, client):
        resource = HeaderHelpersResource()
        client.app.add_route('/', resource)

        client.simulate_request(
            headers=[
                # Singletone header; last one wins
                ('Content-Type', 'text/plain'),
                ('Content-Type', 'image/jpeg'),
                # Should be concatenated
                ('X-Thing', '1'),
                ('X-Thing', '2'),
            ]
        )

        assert resource.req.content_type == 'image/jpeg'
        assert resource.req.get_header('X-Thing') == '1,2'

    # ----------------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------------

    def _check_link_header(self, client, resource, expected_value):
        self._check_header(client, resource, 'Link', expected_value)

    def _check_header(self, client, resource, header, expected_value):
        client.app.add_route('/', resource)

        result = client.simulate_get()
        assert result.headers[header] == expected_value
