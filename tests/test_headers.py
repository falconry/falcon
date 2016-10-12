from collections import defaultdict
from datetime import datetime

import ddt
import six

import falcon
from falcon import testing


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

        resp.etag = 'fa0d1a60ef6616bb28038515c8ea4cb2'
        resp.last_modified = self.last_modified
        resp.retry_after = 3601

        # Relative URI's are OK per http://goo.gl/DbVqR
        resp.location = '/things/87'
        resp.content_location = '/things/78'

        if req.range_unit is None or req.range_unit == 'bytes':
            # bytes 0-499/10240
            resp.content_range = (0, 499, 10 * 1024)
        else:
            resp.content_range = (0, 25, 100, req.range_unit)

        resp.accept_ranges = 'bytes'

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
    URL2 = u'ab\u00e7' if six.PY3 else 'ab\xc3\xa7'

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


@ddt.ddt
class TestHeaders(testing.TestCase):

    def setUp(self):
        super(TestHeaders, self).setUp()

        self.sample_body = testing.rand_string(0, 128 * 1024)
        self.resource = testing.SimpleTestResource(body=self.sample_body)
        self.api.add_route('/', self.resource)

    def test_content_length(self):
        result = self.simulate_get()

        content_length = str(len(self.sample_body))
        self.assertEqual(result.headers['Content-Length'], content_length)

    def test_default_value(self):
        self.simulate_get()

        req = self.resource.captured_req
        value = req.get_header('X-Not-Found') or '876'
        self.assertEqual(value, '876')

    def test_required_header(self):
        self.simulate_get()

        try:
            req = self.resource.captured_req
            req.get_header('X-Not-Found', required=True)
            self.fail('falcon.HTTPMissingHeader not raised')
        except falcon.HTTPMissingHeader as ex:
            self.assertIsInstance(ex, falcon.HTTPBadRequest)
            self.assertEqual(ex.title, 'Missing header value')
            expected_desc = 'The X-Not-Found header is required.'
            self.assertEqual(ex.description, expected_desc)

    @ddt.data(falcon.HTTP_204, falcon.HTTP_304)
    def test_no_content_length(self, status):
        self.api.add_route('/xxx', testing.SimpleTestResource(status=status))

        result = self.simulate_get('/xxx')
        self.assertNotIn('Content-Length', result.headers)
        self.assertFalse(result.content)

    def test_content_header_missing(self):
        environ = testing.create_environ()
        req = falcon.Request(environ)
        for header in ('Content-Type', 'Content-Length'):
            self.assertIs(req.get_header(header), None)

    def test_passthrough_request_headers(self):
        request_headers = {
            'X-Auth-Token': 'Setec Astronomy',
            'Content-Type': 'text/plain; charset=utf-8'
        }
        self.simulate_get(headers=request_headers)

        for name, expected_value in request_headers.items():
            actual_value = self.resource.captured_req.get_header(name)
            self.assertEqual(actual_value, expected_value)

        self.simulate_get(headers=self.resource.captured_req.headers)

        # Compare the request HTTP headers with the original headers
        for name, expected_value in request_headers.items():
            actual_value = self.resource.captured_req.get_header(name)
            self.assertEqual(actual_value, expected_value)

    def test_headers_as_list(self):
        headers = [
            ('Client-ID', '692ba466-74bb-11e3-bf3f-7567c531c7ca'),
            ('Accept', 'audio/*; q=0.2, audio/basic')
        ]

        # Unit test
        environ = testing.create_environ(headers=headers)
        req = falcon.Request(environ)

        for name, value in headers:
            self.assertIn((name.upper(), value), req.headers.items())

        # Functional test
        self.api.add_route('/', testing.SimpleTestResource(headers=headers))
        result = self.simulate_get()

        for name, value in headers:
            self.assertEqual(result.headers[name], value)

    def test_default_media_type(self):
        resource = testing.SimpleTestResource(body='Hello world!')
        self._check_header(resource, 'Content-Type', falcon.DEFAULT_MEDIA_TYPE)

    @ddt.data(
        ('text/plain; charset=UTF-8', u'Hello Unicode! \U0001F638'),

        # NOTE(kgriffs): This only works because the client defaults to
        # ISO-8859-1 IFF the media type is 'text'.
        ('text/plain', 'Hello ISO-8859-1!'),
    )
    @ddt.unpack
    def test_override_default_media_type(self, content_type, body):
        self.api = falcon.API(media_type=content_type)
        self.api.add_route('/', testing.SimpleTestResource(body=body))
        result = self.simulate_get()

        self.assertEqual(result.text, body)
        self.assertEqual(result.headers['Content-Type'], content_type)

    def test_override_default_media_type_missing_encoding(self):
        body = u'{"msg": "Hello Unicode! \U0001F638"}'

        self.api = falcon.API(media_type='application/json')
        self.api.add_route('/', testing.SimpleTestResource(body=body))
        result = self.simulate_get()

        self.assertEqual(result.content, body.encode('utf-8'))
        self.assertIsInstance(result.text, six.text_type)
        self.assertEqual(result.text, body)
        self.assertEqual(result.json, {u'msg': u'Hello Unicode! \U0001F638'})

    def test_response_header_helpers_on_get(self):
        last_modified = datetime(2013, 1, 1, 10, 30, 30)
        resource = HeaderHelpersResource(last_modified)
        self.api.add_route('/', resource)
        result = self.simulate_get()

        resp = resource.resp

        content_type = 'x-falcon/peregrine'
        self.assertEqual(resp.content_type, content_type)
        self.assertEqual(result.headers['Content-Type'], content_type)

        cache_control = ('public, private, no-cache, no-store, '
                         'must-revalidate, proxy-revalidate, max-age=3600, '
                         's-maxage=60, no-transform')

        self.assertEqual(resp.cache_control, cache_control)
        self.assertEqual(result.headers['Cache-Control'], cache_control)

        etag = 'fa0d1a60ef6616bb28038515c8ea4cb2'
        self.assertEqual(resp.etag, etag)
        self.assertEqual(result.headers['Etag'], etag)

        lm_date = 'Tue, 01 Jan 2013 10:30:30 GMT'
        self.assertEqual(resp.last_modified, lm_date)
        self.assertEqual(result.headers['Last-Modified'], lm_date)

        self.assertEqual(resp.retry_after, '3601')
        self.assertEqual(result.headers['Retry-After'], '3601')

        self.assertEqual(resp.location, '/things/87')
        self.assertEqual(result.headers['Location'], '/things/87')

        self.assertEqual(resp.content_location, '/things/78')
        self.assertEqual(result.headers['Content-Location'], '/things/78')

        content_range = 'bytes 0-499/10240'
        self.assertEqual(resp.content_range, content_range)
        self.assertEqual(result.headers['Content-Range'], content_range)

        resp.content_range = (1, 499, 10 * 1024, u'bytes')
        self.assertIsInstance(resp.content_range, str)
        self.assertEqual(resp.content_range, 'bytes 1-499/10240')

        self.assertEqual(resp.accept_ranges, 'bytes')
        self.assertEqual(result.headers['Accept-Ranges'], 'bytes')

        req_headers = {'Range': 'items=0-25'}
        result = self.simulate_get(headers=req_headers)
        self.assertEqual(result.headers['Content-Range'], 'items 0-25/100')

        # Check for duplicate headers
        hist = defaultdict(lambda: 0)
        for name, value in result.headers.items():
            hist[name] += 1
            self.assertEqual(1, hist[name])

    def test_unicode_location_headers(self):
        self.api.add_route('/', LocationHeaderUnicodeResource())

        result = self.simulate_get()
        self.assertEqual(result.headers['Location'], '/%C3%A7runchy/bacon')
        self.assertEqual(result.headers['Content-Location'], 'ab%C3%A7')

        # Test with the values swapped
        result = self.simulate_head()
        self.assertEqual(result.headers['Content-Location'],
                         '/%C3%A7runchy/bacon')
        self.assertEqual(result.headers['Location'], 'ab%C3%A7')

    def test_unicode_headers_convertable(self):
        self.api.add_route('/', UnicodeHeaderResource())

        result = self.simulate_get('/')

        self.assertEqual(result.headers['Content-Type'], 'application/json')
        self.assertEqual(result.headers['X-Auth-Token'], 'toomanysecrets')
        self.assertEqual(result.headers['X-Symbol'], '@')

    def test_unicode_headers_not_convertable(self):
        if six.PY3:
            self.skipTest('Test only applies to Python 2')

        self.api.add_route('/', UnicodeHeaderResource())
        self.assertRaises(UnicodeEncodeError, self.simulate_post, '/')
        self.assertRaises(UnicodeEncodeError, self.simulate_put, '/')

    def test_response_set_and_get_header(self):
        resource = HeaderHelpersResource()
        self.api.add_route('/', resource)

        for method in ('HEAD', 'POST', 'PUT'):
            result = self.simulate_request(method=method)

            content_type = 'x-falcon/peregrine'
            self.assertEqual(result.headers['Content-Type'], content_type)
            self.assertEqual(resource.resp.get_header('content-TyPe'),
                             content_type)

            self.assertEqual(result.headers['Cache-Control'], 'no-store')
            self.assertEqual(result.headers['X-Auth-Token'], 'toomanysecrets')

            self.assertEqual(resource.resp.location, None)
            self.assertEqual(resource.resp.get_header('not-real'), None)

            # Check for duplicate headers
            hist = defaultdict(int)
            for name, value in result.headers.items():
                hist[name] += 1
                self.assertEqual(hist[name], 1)

    def test_response_append_header(self):
        self.api.add_route('/', AppendHeaderResource())

        for method in ('HEAD', 'GET'):
            result = self.simulate_request(method=method)
            value = result.headers['x-things']
            self.assertEqual(value, 'thing-1,thing-2,thing-3')

        result = self.simulate_request(method='POST')
        self.assertEqual(result.headers['x-things'], 'thing-1')

    def test_vary_star(self):
        self.api.add_route('/', VaryHeaderResource(['*']))
        result = self.simulate_get()
        self.assertEqual(result.headers['vary'], '*')

    @ddt.data(
        (['accept-encoding'], 'accept-encoding'),
        ([u'accept-encoding', 'x-auth-token'], 'accept-encoding, x-auth-token'),
        (('accept-encoding', u'x-auth-token'), 'accept-encoding, x-auth-token'),
    )
    @ddt.unpack
    def test_vary_header(self, vary, expected_value):
        resource = VaryHeaderResource(vary)
        self._check_header(resource, 'Vary', expected_value)

    def test_content_type_no_body(self):
        self.api.add_route('/', testing.SimpleTestResource())
        result = self.simulate_get()

        # NOTE(kgriffs): Even when there is no body, Content-Type
        # should still be included per wsgiref.validate
        self.assertIn('Content-Type', result.headers)
        self.assertEqual(result.headers['Content-Length'], '0')

    @ddt.data(falcon.HTTP_204, falcon.HTTP_304)
    def test_no_content_type(self, status):
        self.api.add_route('/', testing.SimpleTestResource(status=status))

        result = self.simulate_get()
        self.assertNotIn('Content-Type', result.headers)

    def test_custom_content_type(self):
        content_type = 'application/xml; charset=utf-8'
        resource = XmlResource(content_type)
        self._check_header(resource, 'Content-Type', content_type)

    def test_add_link_single(self):
        expected_value = '</things/2842>; rel=next'

        resource = LinkHeaderResource()
        resource.add_link('/things/2842', 'next')

        self._check_link_header(resource, expected_value)

    def test_add_link_multiple(self):
        expected_value = (
            '</things/2842>; rel=next, ' +
            '<http://%C3%A7runchy/bacon>; rel=contents, ' +
            '<ab%C3%A7>; rel="http://example.com/ext-type", ' +
            '<ab%C3%A7>; rel="http://example.com/%C3%A7runchy", ' +
            '<ab%C3%A7>; rel="https://example.com/too-%C3%A7runchy", ' +
            '</alt-thing>; rel="alternate http://example.com/%C3%A7runchy"')

        uri = u'ab\u00e7' if six.PY3 else 'ab\xc3\xa7'

        resource = LinkHeaderResource()
        resource.add_link('/things/2842', 'next')
        resource.add_link(u'http://\u00e7runchy/bacon', 'contents')
        resource.add_link(uri, 'http://example.com/ext-type')
        resource.add_link(uri, u'http://example.com/\u00e7runchy')
        resource.add_link(uri, u'https://example.com/too-\u00e7runchy')
        resource.add_link('/alt-thing',
                          u'alternate http://example.com/\u00e7runchy')

        self._check_link_header(resource, expected_value)

    def test_add_link_with_title(self):
        expected_value = ('</related/thing>; rel=item; '
                          'title="A related thing"')

        resource = LinkHeaderResource()
        resource.add_link('/related/thing', 'item',
                          title='A related thing')

        self._check_link_header(resource, expected_value)

    def test_add_link_with_title_star(self):
        expected_value = ('</related/thing>; rel=item; '
                          "title*=UTF-8''A%20related%20thing, "
                          '</%C3%A7runchy/thing>; rel=item; '
                          "title*=UTF-8'en'A%20%C3%A7runchy%20thing")

        resource = LinkHeaderResource()
        resource.add_link('/related/thing', 'item',
                          title_star=('', 'A related thing'))

        resource.add_link(u'/\u00e7runchy/thing', 'item',
                          title_star=('en', u'A \u00e7runchy thing'))

        self._check_link_header(resource, expected_value)

    def test_add_link_with_anchor(self):
        expected_value = ('</related/thing>; rel=item; '
                          'anchor="/some%20thing/or-other"')

        resource = LinkHeaderResource()
        resource.add_link('/related/thing', 'item',
                          anchor='/some thing/or-other')

        self._check_link_header(resource, expected_value)

    def test_add_link_with_hreflang(self):
        expected_value = ('</related/thing>; rel=about; '
                          'hreflang=en')

        resource = LinkHeaderResource()
        resource.add_link('/related/thing', 'about', hreflang='en')

        self._check_link_header(resource, expected_value)

    def test_add_link_with_hreflang_multi(self):
        expected_value = ('</related/thing>; rel=about; '
                          'hreflang=en-GB; hreflang=de')

        resource = LinkHeaderResource()
        resource.add_link('/related/thing', 'about',
                          hreflang=('en-GB', 'de'))

        self._check_link_header(resource, expected_value)

    def test_add_link_with_type_hint(self):
        expected_value = ('</related/thing>; rel=alternate; '
                          'type="video/mp4; codecs=avc1.640028"')

        resource = LinkHeaderResource()
        resource.add_link('/related/thing', 'alternate',
                          type_hint='video/mp4; codecs=avc1.640028')

        self._check_link_header(resource, expected_value)

    def test_add_link_complex(self):
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

        self._check_link_header(resource, expected_value)

    def test_content_length_options(self):
        result = self.simulate_options()

        content_length = '0'
        self.assertEqual(result.headers['Content-Length'], content_length)

    # ----------------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------------

    def _check_link_header(self, resource, expected_value):
        self._check_header(resource, 'Link', expected_value)

    def _check_header(self, resource, header, expected_value):
        self.api.add_route('/', resource)

        result = self.simulate_get()
        self.assertEqual(result.headers[header], expected_value)
