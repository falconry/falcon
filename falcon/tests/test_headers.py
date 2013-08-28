from collections import defaultdict
from datetime import datetime

import six
from testtools.matchers import Contains, Not

import falcon
import falcon.testing as testing


class StatusTestResource:
    sample_body = testing.rand_string(0, 128 * 1024)

    def __init__(self, status):
        self.status = status

    def on_get(self, req, resp):
        resp.status = self.status
        resp.body = self.sample_body


class XmlResource:
    def __init__(self, content_type):
        self.content_type = content_type

    def on_get(self, req, resp):
        resp.set_header('Content-Type', self.content_type)


class DefaultContentTypeResource:
    def __init__(self, body=None):
        self.body = body

    def on_get(self, req, resp):
        if self.body is not None:
            resp.body = self.body


class HeaderHelpersResource:

    def __init__(self, last_modified=None):
        if last_modified is not None:
            self.last_modified = last_modified
        else:
            self.last_modified = datetime.utcnow()

    def on_get(self, req, resp):
        resp.body = "{}"
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

        # bytes 0-499/10240
        resp.content_range = (0, 499, 10 * 1024)

        self.resp = resp

    def on_head(self, req, resp):
        resp.set_header('Content-Type', 'x-swallow/unladen')
        resp.set_header('X-Auth-Token', 'setecastronomy')
        resp.set_header('X-Auth-Token', 'toomanysecrets')
        resp.content_type = 'x-falcon/peregrine'
        resp.cache_control = ['no-store']

        resp.location = '/things/87'
        del resp.location

        self.resp = resp


class LocationHeaderUnicodeResource:

    URL1 = u'/\u00e7runchy/bacon'
    URL2 = u'ab\u00e7' if six.PY3 else 'ab\xc3\xa7'

    def on_get(self, req, resp):
        resp.location = self.URL1
        resp.content_location = self.URL2

    def on_head(self, req, resp):
        resp.location = self.URL2
        resp.content_location = self.URL1


class VaryHeaderResource:

    def __init__(self, vary):
        self.vary = vary

    def on_get(self, req, resp):
        resp.body = "{}"
        resp.vary = self.vary


class TestHeaders(testing.TestBase):

    def before(self):
        self.resource = testing.TestResource()
        self.api.add_route(self.test_route, self.resource)

    def test_content_length(self):
        self.simulate_request(self.test_route)

        headers = self.srmock.headers

        # Test Content-Length header set
        content_length = str(len(self.resource.sample_body))
        content_length_header = ('Content-Length', content_length)
        self.assertThat(headers, Contains(content_length_header))

    def test_default_value(self):
        self.simulate_request(self.test_route)

        value = self.resource.req.get_header('X-Not-Found') or '876'
        self.assertEquals(value, '876')

    def test_required_header(self):
        self.simulate_request(self.test_route)

        self.assertRaises(falcon.HTTPBadRequest,
                          self.resource.req.get_header, 'X-Not-Found',
                          required=True)

    def test_prefer_host_header(self):
        self.simulate_request(self.test_route)

        # Make sure we picked up host from HTTP_HOST, not SERVER_NAME
        host = self.resource.req.get_header('host')
        self.assertEquals(host, testing.DEFAULT_HOST)

    def test_host_fallback(self):
        # Set protocol to 1.0 so that we won't get a host header
        self.simulate_request(self.test_route, protocol='HTTP/1.0')

        # Make sure we picked up host from HTTP_HOST, not SERVER_NAME
        host = self.resource.req.get_header('host')
        self.assertEquals(host, 'localhost')

    def test_host_fallback_port8000(self):
        # Set protocol to 1.0 so that we won't get a host header
        self.simulate_request(self.test_route, protocol='HTTP/1.0',
                              port='8000')

        # Make sure we picked up host from HTTP_HOST, not SERVER_NAME
        host = self.resource.req.get_header('host')
        self.assertEquals(host, 'localhost:8000')

    def test_no_body_on_100(self):
        self.resource = StatusTestResource(falcon.HTTP_100)
        self.api.add_route('/1xx', self.resource)

        body = self.simulate_request('/1xx')
        self.assertThat(self.srmock.headers_dict,
                        Not(Contains('Content-Length')))

        self.assertEquals(body, [])

    def test_no_body_on_101(self):
        self.resource = StatusTestResource(falcon.HTTP_101)
        self.api.add_route('/1xx', self.resource)

        body = self.simulate_request('/1xx')
        self.assertThat(self.srmock.headers_dict,
                        Not(Contains('Content-Length')))

        self.assertEquals(body, [])

    def test_no_body_on_204(self):
        self.resource = StatusTestResource(falcon.HTTP_204)
        self.api.add_route('/204', self.resource)

        body = self.simulate_request('/204')
        self.assertThat(self.srmock.headers_dict,
                        Not(Contains('Content-Length')))

        self.assertEquals(body, [])

    def test_no_body_on_304(self):
        self.resource = StatusTestResource(falcon.HTTP_304)
        self.api.add_route('/304', self.resource)

        body = self.simulate_request('/304')
        self.assertThat(self.srmock.headers_dict,
                        Not(Contains('Content-Length')))

        self.assertEquals(body, [])

    def test_passthrough_req_headers(self):
        req_headers = {
            'X-Auth-Token': 'Setec Astronomy',
            'Content-Type': 'text/plain; charset=utf-8'
        }
        self.simulate_request(self.test_route, headers=req_headers)

        for name, expected_value in req_headers.items():
            actual_value = self.resource.req.get_header(name)
            self.assertEquals(actual_value, expected_value)

        self.simulate_request(self.test_route,
                              headers=self.resource.req.headers)

        # Compare the request HTTP headers with the original headers
        for name, expected_value in req_headers.items():
            actual_value = self.resource.req.get_header(name)
            self.assertEquals(actual_value, expected_value)

    def test_passthrough_resp_headers(self):
        self.simulate_request(self.test_route)

        resp_headers = self.srmock.headers

        for h in self.resource.resp_headers.items():
            self.assertThat(resp_headers, Contains(h))

    def test_default_media_type(self):
        self.resource = DefaultContentTypeResource('Hello world!')
        self.api.add_route(self.test_route, self.resource)
        self.simulate_request(self.test_route)

        content_type = falcon.DEFAULT_MEDIA_TYPE
        self.assertIn(('Content-Type', content_type), self.srmock.headers)

    def test_custom_media_type(self):
        self.resource = DefaultContentTypeResource('Hello world!')
        self.api = falcon.API(media_type='application/atom+xml')
        self.api.add_route(self.test_route, self.resource)
        self.simulate_request(self.test_route)

        content_type = 'application/atom+xml'
        self.assertIn(('Content-Type', content_type), self.srmock.headers)

    def test_response_header_helpers_on_get(self):
        last_modified = datetime(2013, 1, 1, 10, 30, 30)
        self.resource = HeaderHelpersResource(last_modified)
        self.api.add_route(self.test_route, self.resource)
        self.simulate_request(self.test_route)

        resp = self.resource.resp

        content_type = 'x-falcon/peregrine'
        self.assertEqual(content_type, resp.content_type)
        self.assertIn(('Content-Type', content_type), self.srmock.headers)

        cache_control = ('public, private, no-cache, no-store, '
                         'must-revalidate, proxy-revalidate, max-age=3600, '
                         's-maxage=60, no-transform')

        self.assertEqual(cache_control, resp.cache_control)
        self.assertIn(('Cache-Control', cache_control), self.srmock.headers)

        etag = 'fa0d1a60ef6616bb28038515c8ea4cb2'
        self.assertEqual(etag, resp.etag)
        self.assertIn(('ETag', etag), self.srmock.headers)

        last_modified_http_date = 'Tue, 01 Jan 2013 10:30:30 GMT'
        self.assertEqual(last_modified_http_date, resp.last_modified)
        self.assertIn(('Last-Modified', last_modified_http_date),
                      self.srmock.headers)

        self.assertEqual('3601', resp.retry_after)
        self.assertIn(('Retry-After', '3601'), self.srmock.headers)

        self.assertEqual('/things/87', resp.location)
        self.assertIn(('Location', '/things/87'), self.srmock.headers)

        self.assertEqual('/things/78', resp.content_location)
        self.assertIn(('Content-Location', '/things/78'), self.srmock.headers)

        self.assertEqual('bytes 0-499/10240', resp.content_range)
        self.assertIn(('Content-Range', 'bytes 0-499/10240'),
                      self.srmock.headers)

        # Check for duplicate headers
        hist = defaultdict(lambda: 0)
        for name, value in self.srmock.headers:
            hist[name] += 1
            self.assertEqual(1, hist[name])

    def test_unicode_location_headers(self):
        self.api.add_route(self.test_route, LocationHeaderUnicodeResource())
        self.simulate_request(self.test_route)

        location = ('Location', '/%C3%A7runchy/bacon')
        self.assertIn(location, self.srmock.headers)

        content_location = ('Content-Location', 'ab%C3%A7')
        self.assertIn(content_location, self.srmock.headers)

        # Test with the values swapped
        self.simulate_request(self.test_route, method='HEAD')

        location = ('Location', 'ab%C3%A7')
        self.assertIn(location, self.srmock.headers)

        content_location = ('Content-Location', '/%C3%A7runchy/bacon')
        self.assertIn(content_location, self.srmock.headers)

    def test_response_header_helpers_on_head(self):
        self.resource = HeaderHelpersResource()
        self.api.add_route(self.test_route, self.resource)
        self.simulate_request(self.test_route, method="HEAD")

        content_type = 'x-falcon/peregrine'
        self.assertIn(('Content-Type', content_type), self.srmock.headers)
        self.assertIn(('Cache-Control', 'no-store'), self.srmock.headers)
        self.assertIn(('X-Auth-Token', 'toomanysecrets'), self.srmock.headers)

        self.assertEqual(None, self.resource.resp.location)

        # Check for duplicate headers
        hist = defaultdict(lambda: 0)
        for name, value in self.srmock.headers:
            hist[name] += 1
            self.assertEqual(1, hist[name])

    def test_vary_star(self):
        self.resource = VaryHeaderResource(['*'])
        self.api.add_route(self.test_route, self.resource)
        self.simulate_request(self.test_route)

        self.assertIn(('Vary', '*'), self.srmock.headers)

    def test_vary_header(self):
        self.resource = VaryHeaderResource(['accept-encoding'])
        self.api.add_route(self.test_route, self.resource)
        self.simulate_request(self.test_route)

        self.assertIn(('Vary', 'accept-encoding'), self.srmock.headers)

    def test_vary_headers(self):
        self.resource = VaryHeaderResource(['accept-encoding', 'x-auth-token'])
        self.api.add_route(self.test_route, self.resource)
        self.simulate_request(self.test_route)

        vary = 'accept-encoding, x-auth-token'
        self.assertIn(('Vary', vary), self.srmock.headers)

    def test_vary_headers_tuple(self):
        self.resource = VaryHeaderResource(('accept-encoding', 'x-auth-token'))
        self.api.add_route(self.test_route, self.resource)
        self.simulate_request(self.test_route)

        vary = 'accept-encoding, x-auth-token'
        self.assertIn(('Vary', vary), self.srmock.headers)

    def test_no_content_type(self):
        self.resource = DefaultContentTypeResource()
        self.api.add_route(self.test_route, self.resource)
        self.simulate_request(self.test_route)

        self.assertNotIn('Content-Type', self.srmock.headers_dict)

    def test_custom_content_type(self):
        content_type = 'application/xml; charset=utf-8'
        self.resource = XmlResource(content_type)
        self.api.add_route(self.test_route, self.resource)

        self.simulate_request(self.test_route)
        self.assertIn(('Content-Type', content_type), self.srmock.headers)
