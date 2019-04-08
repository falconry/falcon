from collections import defaultdict
from datetime import datetime

import pytest

import falcon
from falcon import testing
from falcon.util import compat


SAMPLE_BODY = testing.rand_string(0, 128 * 1024)


@pytest.fixture
def client():
    app = falcon.API()
    return testing.TestClient(app)


class XmlResource(object):
    def __init__(self, content_type):
        self.content_type = content_type

    def on_get(self, req, resp):
        resp.set_header('content-type', self.content_type)


class HeaderHelpersResource(object):

    def __init__(self, last_modified=None):
        if last_modified is not None:
            self.last_modified = last_modified
        else:
            self.last_modified = datetime.utcnow()

    def _overwrite_headers(self, req, resp):
        resp.content_type = 'x-falcon/peregrine'
        resp.cache_control = ['no-store']

    def on_get(self, req, resp):
        resp.body = '{}'
        resp.content_type = 'x-falcon/peregrine'
        resp.cache_control = [
            'public', 'private', 'no-cache', 'no-store', 'must-revalidate',
            'proxy-revalidate', 'max-age=3600', 's-maxage=60', 'no-transform'
        ]

        resp.etag = None  # Header not set yet, so should be a noop
        resp.etag = 'fa0d1a60ef6616bb28038515c8ea4cb2'
        resp.last_modified = self.last_modified
        resp.retry_after = 3601

        # Relative URI's are OK per http://goo.gl/DbVqR
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
        resp.set_headers([
            ('CONTENT-TYPE', 'x-swallow/unladen'),
            ('X-Auth-Token', 'setecastronomy'),
            ('X-AUTH-TOKEN', 'toomanysecrets')
        ])

        self._overwrite_headers(req, resp)

        self.resp = resp

    def on_put(self, req, resp):
        resp.set_headers({
            'CONTENT-TYPE': 'x-swallow/unladen',
            'X-aUTH-tOKEN': 'toomanysecrets'
        })

        self._overwrite_headers(req, resp)

        self.resp = resp


class LocationHeaderUnicodeResource(object):

    URL1 = u'/\u00e7runchy/bacon'
    URL2 = u'ab\u00e7' if compat.PY3 else 'ab\xc3\xa7'

    def on_get(self, req, resp):
        resp.location = self.URL1
        resp.content_location = self.URL2

    def on_head(self, req, resp):
        resp.location = self.URL2
        resp.content_location = self.URL1


class UnicodeHeaderResource(object):

    def on_get(self, req, resp):
        resp.set_headers([
            (u'X-auTH-toKEN', 'toomanysecrets'),
            ('Content-TYpE', u'application/json'),
            (u'X-symBOl', u'@'),
        ])

    def on_post(self, req, resp):
        resp.set_headers([
            (u'X-symb\u00F6l', 'thing'),
        ])

    def on_put(self, req, resp):
        resp.set_headers([
            ('X-Thing', u'\u00FF'),
        ])


class VaryHeaderResource(object):

    def __init__(self, vary):
        self.vary = vary

    def on_get(self, req, resp):
        resp.body = '{}'
        resp.vary = self.vary


class LinkHeaderResource(object):

    def __init__(self):
        self._links = []

    def add_link(self, *args, **kwargs):
        self._links.append((args, kwargs))

    def on_get(self, req, resp):
        resp.body = '{}'

        for args, kwargs in self._links:
            resp.add_link(*args, **kwargs)


class AppendHeaderResource(object):

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

        c1 = 'ut_existing_user=1; expires=Mon, 14-Jan-2019 21:20:08 GMT; Max-Age=600; path=/'
        resp.append_header('Set-Cookie', c1)
        c2 = 'partner_source=deleted; expires=Thu, 01-Jan-1970 00:00:01 GMT; Max-Age=0'
        resp.append_header('seT-cookie', c2)


class RemoveHeaderResource(object):
    def __init__(self, with_double_quotes):
        self.with_double_quotes = with_double_quotes

    def on_get(self, req, resp):
        etag = 'fa0d1a60ef6616bb28038515c8ea4cb2'
        if self.with_double_quotes:
            etag = '\"' + etag + '\"'

        resp.etag = etag
        assert resp.etag == '"fa0d1a60ef6616bb28038515c8ea4cb2"'
        resp.etag = None

        resp.downloadable_as = 'foo.zip'
        assert resp.downloadable_as == 'attachment; filename="foo.zip"'
        resp.downloadable_as = None


class ContentLengthHeaderResource(object):

    def __init__(self, content_length, body=None, data=None):
        self._content_length = content_length
        self._body = body
        self._data = data

    def on_get(self, req, resp):
        # NOTE(kgriffs): Use stream_len for now to cover the deprecated alias
        resp.stream_len = self._content_length

        if self._body:
            resp.body = self._body

        if self._data:
            resp.data = self._data

    def on_head(self, req, resp):
        resp.content_length = self._content_length


class ExpiresHeaderResource(object):

    def __init__(self, expires):
        self._expires = expires

    def on_get(self, req, resp):
        resp.expires = self._expires


class TestHeaders(object):

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

    def test_declared_content_length_overriden_by_body_length(self, client):
        resource = ContentLengthHeaderResource(42, body=SAMPLE_BODY)
        client.app.add_route('/', resource)
        result = client.simulate_get()

        assert result.headers['Content-Length'] == str(len(SAMPLE_BODY))

    def test_declared_content_length_overriden_by_data_length(self, client):
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

    def test_default_value(self, client):
        resource = testing.SimpleTestResource(body=SAMPLE_BODY)
        client.app.add_route('/', resource)
        client.simulate_get()

        req = resource.captured_req
        value = req.get_header('X-Not-Found') or '876'
        assert value == '876'

        value = req.get_header('X-Not-Found', default='some-value')
        assert value == 'some-value'

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
            expected_desc = 'The X-Not-Found header is required.'
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
            'Content-Type': 'text/plain; charset=utf-8'
        }
        client.simulate_get(headers=request_headers)

        for name, expected_value in request_headers.items():
            actual_value = resource.captured_req.get_header(name)
            assert actual_value == expected_value

        client.simulate_get(headers=resource.captured_req.headers)

        # Compare the request HTTP headers with the original headers
        for name, expected_value in request_headers.items():
            actual_value = resource.captured_req.get_header(name)
            assert actual_value == expected_value

    def test_headers_as_list(self, client):
        headers = [
            ('Client-ID', '692ba466-74bb-11e3-bf3f-7567c531c7ca'),
            ('Accept', 'audio/*; q=0.2, audio/basic')
        ]

        # Unit test
        environ = testing.create_environ(headers=headers)
        req = falcon.Request(environ)

        for name, value in headers:
            assert (name.upper(), value) in req.headers.items()

        # Functional test
        client.app.add_route('/', testing.SimpleTestResource(headers=headers))
        result = client.simulate_get()

        for name, value in headers:
            assert result.headers[name] == value

    def test_default_media_type(self, client):
        resource = testing.SimpleTestResource(body='Hello world!')
        self._check_header(client, resource, 'Content-Type', falcon.DEFAULT_MEDIA_TYPE)

    @pytest.mark.parametrize('content_type,body', [
        ('text/plain; charset=UTF-8', u'Hello Unicode! \U0001F638'),
        # NOTE(kgriffs): This only works because the client defaults to
        # ISO-8859-1 IFF the media type is 'text'.
        ('text/plain', 'Hello ISO-8859-1!'),
    ])
    def test_override_default_media_type(self, client, content_type, body):
        client.app = falcon.API(media_type=content_type)
        client.app.add_route('/', testing.SimpleTestResource(body=body))
        result = client.simulate_get()

        assert result.text == body
        assert result.headers['Content-Type'] == content_type

    def test_override_default_media_type_missing_encoding(self, client):
        body = u'{"msg": "Hello Unicode! \U0001F638"}'

        client.app = falcon.API(media_type='application/json')
        client.app.add_route('/', testing.SimpleTestResource(body=body))
        result = client.simulate_get()

        assert result.content == body.encode('utf-8')
        assert isinstance(result.text, compat.text_type)
        assert result.text == body
        assert result.json == {u'msg': u'Hello Unicode! \U0001F638'}

    def test_response_header_helpers_on_get(self, client):
        last_modified = datetime(2013, 1, 1, 10, 30, 30)
        resource = HeaderHelpersResource(last_modified)
        client.app.add_route('/', resource)
        result = client.simulate_get()

        resp = resource.resp

        content_type = 'x-falcon/peregrine'
        assert resp.content_type == content_type
        assert result.headers['Content-Type'] == content_type
        assert result.headers['Content-Disposition'] == 'attachment; filename="Some File.zip"'

        cache_control = ('public, private, no-cache, no-store, '
                         'must-revalidate, proxy-revalidate, max-age=3600, '
                         's-maxage=60, no-transform')

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

        resp.content_range = (1, 499, 10 * 1024, u'bytes')
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

    def test_unicode_location_headers(self, client):
        client.app.add_route('/', LocationHeaderUnicodeResource())

        result = client.simulate_get()
        assert result.headers['Location'] == '/%C3%A7runchy/bacon'
        assert result.headers['Content-Location'] == 'ab%C3%A7'

        # Test with the values swapped
        result = client.simulate_head()
        assert result.headers['Content-Location'] == '/%C3%A7runchy/bacon'
        assert result.headers['Location'] == 'ab%C3%A7'

    def test_unicode_headers_convertable(self, client):
        client.app.add_route('/', UnicodeHeaderResource())

        result = client.simulate_get('/')

        assert result.headers['Content-Type'] == 'application/json'
        assert result.headers['X-Auth-Token'] == 'toomanysecrets'
        assert result.headers['X-Symbol'] == '@'

    @pytest.mark.skipif(compat.PY3, reason='Test only applies to Python 2')
    def test_unicode_headers_not_convertable(self, client):
        client.app.add_route('/', UnicodeHeaderResource())
        with pytest.raises(UnicodeEncodeError):
            client.simulate_post('/')

        with pytest.raises(UnicodeEncodeError):
            client.simulate_put('/')

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

            value = resource.resp.get_header('X-Header-Not-Set', default=content_type_alt)
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

        cookie = 'ut_existing_user=1; expires=Mon, 14-Jan-2019 21:20:08 GMT; Max-Age=600; path=/'

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

    @pytest.mark.parametrize('vary,expected_value', [
        (['accept-encoding'], 'accept-encoding'),
        ([u'accept-encoding', 'x-auth-token'], 'accept-encoding, x-auth-token'),
        (('accept-encoding', u'x-auth-token'), 'accept-encoding, x-auth-token'),
    ])
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

    def test_add_link_single(self, client):
        expected_value = '</things/2842>; rel=next'

        resource = LinkHeaderResource()
        resource.add_link('/things/2842', 'next')

        self._check_link_header(client, resource, expected_value)

    def test_add_link_multiple(self, client):
        expected_value = (
            '</things/2842>; rel=next, ' +
            '<http://%C3%A7runchy/bacon>; rel=contents, ' +
            '<ab%C3%A7>; rel="http://example.com/ext-type", ' +
            '<ab%C3%A7>; rel="http://example.com/%C3%A7runchy", ' +
            '<ab%C3%A7>; rel="https://example.com/too-%C3%A7runchy", ' +
            '</alt-thing>; rel="alternate http://example.com/%C3%A7runchy"')

        uri = u'ab\u00e7' if compat.PY3 else 'ab\xc3\xa7'

        resource = LinkHeaderResource()
        resource.add_link('/things/2842', 'next')
        resource.add_link(u'http://\u00e7runchy/bacon', 'contents')
        resource.add_link(uri, 'http://example.com/ext-type')
        resource.add_link(uri, u'http://example.com/\u00e7runchy')
        resource.add_link(uri, u'https://example.com/too-\u00e7runchy')
        resource.add_link('/alt-thing',
                          u'alternate http://example.com/\u00e7runchy')

        self._check_link_header(client, resource, expected_value)

    def test_add_link_with_title(self, client):
        expected_value = ('</related/thing>; rel=item; '
                          'title="A related thing"')

        resource = LinkHeaderResource()
        resource.add_link('/related/thing', 'item',
                          title='A related thing')

        self._check_link_header(client, resource, expected_value)

    def test_add_link_with_title_star(self, client):
        expected_value = ('</related/thing>; rel=item; '
                          "title*=UTF-8''A%20related%20thing, "
                          '</%C3%A7runchy/thing>; rel=item; '
                          "title*=UTF-8'en'A%20%C3%A7runchy%20thing")

        resource = LinkHeaderResource()
        resource.add_link('/related/thing', 'item',
                          title_star=('', 'A related thing'))

        resource.add_link(u'/\u00e7runchy/thing', 'item',
                          title_star=('en', u'A \u00e7runchy thing'))

        self._check_link_header(client, resource, expected_value)

    def test_add_link_with_anchor(self, client):
        expected_value = ('</related/thing>; rel=item; '
                          'anchor="/some%20thing/or-other"')

        resource = LinkHeaderResource()
        resource.add_link('/related/thing', 'item',
                          anchor='/some thing/or-other')

        self._check_link_header(client, resource, expected_value)

    def test_add_link_with_hreflang(self, client):
        expected_value = ('</related/thing>; rel=about; '
                          'hreflang=en')

        resource = LinkHeaderResource()
        resource.add_link('/related/thing', 'about', hreflang='en')

        self._check_link_header(client, resource, expected_value)

    def test_add_link_with_hreflang_multi(self, client):
        expected_value = ('</related/thing>; rel=about; '
                          'hreflang=en-GB; hreflang=de')

        resource = LinkHeaderResource()
        resource.add_link('/related/thing', 'about',
                          hreflang=('en-GB', 'de'))

        self._check_link_header(client, resource, expected_value)

    def test_add_link_with_type_hint(self, client):
        expected_value = ('</related/thing>; rel=alternate; '
                          'type="video/mp4; codecs=avc1.640028"')

        resource = LinkHeaderResource()
        resource.add_link('/related/thing', 'alternate',
                          type_hint='video/mp4; codecs=avc1.640028')

        self._check_link_header(client, resource, expected_value)

    def test_add_link_complex(self, client):
        expected_value = ('</related/thing>; rel=alternate; '
                          'title="A related thing"; '
                          "title*=UTF-8'en'A%20%C3%A7runchy%20thing; "
                          'type="application/json"; '
                          'hreflang=en-GB; hreflang=de')

        resource = LinkHeaderResource()
        resource.add_link('/related/thing', 'alternate',
                          title='A related thing',
                          hreflang=('en-GB', 'de'),
                          type_hint='application/json',
                          title_star=('en', u'A \u00e7runchy thing'))

        self._check_link_header(client, resource, expected_value)

    def test_content_length_options(self, client):
        result = client.simulate_options()

        content_length = '0'
        assert result.headers['Content-Length'] == content_length

    # ----------------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------------

    def _check_link_header(self, client, resource, expected_value):
        self._check_header(client, resource, 'Link', expected_value)

    def _check_header(self, client, resource, header, expected_value):
        client.app.add_route('/', resource)

        result = client.simulate_get()
        assert result.headers[header] == expected_value
