from datetime import datetime

from testtools.matchers import Contains, Not

import falcon
from . import helpers


class StatusTestResource:
    sample_body = helpers.rand_string(0, 128 * 1024)

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

    def on_head(self, req, resp):
        # Alias of set_media_type
        resp.content_type = 'x-falcon/peregrine'

        resp.cache_control = ['no-store']


class VaryHeaderResource:

    def __init__(self, vary):
        self.vary = vary

    def on_get(self, req, resp):
        resp.body = "{}"
        resp.vary = self.vary


class TestHeaders(helpers.TestSuite):

    def prepare(self):
        self.resource = helpers.TestResource()
        self.api.add_route(self.test_route, self.resource)

    def test_content_length(self):
        self._simulate_request(self.test_route)

        headers = self.srmock.headers

        # Test Content-Length header set
        content_length = str(len(self.resource.sample_body))
        content_length_header = ('Content-Length', content_length)
        self.assertThat(headers, Contains(content_length_header))

    def test_default_value(self):
        self._simulate_request(self.test_route)

        value = self.resource.req.get_header('X-Not-Found', '876')
        self.assertEquals(value, '876')

    def test_prefer_host_header(self):
        self._simulate_request(self.test_route)

        # Make sure we picked up host from HTTP_HOST, not SERVER_NAME
        host = self.resource.req.get_header('host')
        self.assertEquals(host, 'falconer')

    def test_host_fallback(self):
        # Set protocol to 1.0 so that we won't get a host header
        self._simulate_request(self.test_route, protocol='HTTP/1.0')

        # Make sure we picked up host from HTTP_HOST, not SERVER_NAME
        host = self.resource.req.get_header('host')
        self.assertEquals(host, 'localhost')

    def test_host_fallback_port8000(self):
        # Set protocol to 1.0 so that we won't get a host header
        self._simulate_request(self.test_route, protocol='HTTP/1.0',
                               port='8000')

        # Make sure we picked up host from HTTP_HOST, not SERVER_NAME
        host = self.resource.req.get_header('host')
        self.assertEquals(host, 'localhost:8000')

    def test_no_body_on_100(self):
        self.resource = StatusTestResource(falcon.HTTP_100)
        self.api.add_route('/1xx', self.resource)

        body = self._simulate_request('/1xx')
        self.assertThat(self.srmock.headers_dict,
                        Not(Contains('Content-Length')))

        self.assertEquals(body, [])

    def test_no_body_on_101(self):
        self.resource = StatusTestResource(falcon.HTTP_101)
        self.api.add_route('/1xx', self.resource)

        body = self._simulate_request('/1xx')
        self.assertThat(self.srmock.headers_dict,
                        Not(Contains('Content-Length')))

        self.assertEquals(body, [])

    def test_no_body_on_204(self):
        self.resource = StatusTestResource(falcon.HTTP_204)
        self.api.add_route('/204', self.resource)

        body = self._simulate_request('/204')
        self.assertThat(self.srmock.headers_dict,
                        Not(Contains('Content-Length')))

        self.assertEquals(body, [])

    def test_no_body_on_304(self):
        self.resource = StatusTestResource(falcon.HTTP_304)
        self.api.add_route('/304', self.resource)

        body = self._simulate_request('/304')
        self.assertThat(self.srmock.headers_dict,
                        Not(Contains('Content-Length')))

        self.assertEquals(body, [])

    def test_passthrough_req_headers(self):
        req_headers = {
            'X-Auth-Token': 'Setec Astronomy',
            'Content-Type': 'text/plain; charset=utf-8'
        }
        self._simulate_request(self.test_route, headers=req_headers)

        for name, expected_value in req_headers.items():
            actual_value = self.resource.req.get_header(name)
            self.assertEquals(actual_value, expected_value)

    def test_passthrough_resp_headers(self):
        self._simulate_request(self.test_route)

        resp_headers = self.srmock.headers

        for h in self.resource.resp_headers.items():
            self.assertThat(resp_headers, Contains(h))

    def test_default_media_type(self):
        self.resource = DefaultContentTypeResource('Hello world!')
        self.api.add_route(self.test_route, self.resource)
        self._simulate_request(self.test_route)

        content_type = falcon.DEFAULT_MEDIA_TYPE
        self.assertIn(('Content-Type', content_type), self.srmock.headers)

    def test_custom_media_type(self):
        self.resource = DefaultContentTypeResource('Hello world!')
        self.api = falcon.API(media_type='application/atom+xml')
        self.api.add_route(self.test_route, self.resource)
        self._simulate_request(self.test_route)

        content_type = 'application/atom+xml'
        self.assertIn(('Content-Type', content_type), self.srmock.headers)

    def test_response_header_helpers_on_get(self):
        last_modified = datetime(2013, 1, 1, 10, 30, 30)
        self.resource = HeaderHelpersResource(last_modified)
        self.api.add_route(self.test_route, self.resource)
        self._simulate_request(self.test_route)

        content_type = 'x-falcon/peregrine'
        self.assertIn(('Content-Type', content_type), self.srmock.headers)

        cache_control = ('public, private, no-cache, no-store, '
                         'must-revalidate, proxy-revalidate, max-age=3600, '
                         's-maxage=60, no-transform')

        self.assertIn(('Cache-Control', cache_control), self.srmock.headers)

        etag = 'fa0d1a60ef6616bb28038515c8ea4cb2'
        self.assertIn(('ETag', etag), self.srmock.headers)

        last_modified_http_date = 'Tue, 01 Jan 2013 10:30:30 GMT'
        self.assertIn(('Last-Modified', last_modified_http_date),
                      self.srmock.headers)

        self.assertIn(('Retry-After', '3601'), self.srmock.headers)
        self.assertIn(('Location', '/things/87'), self.srmock.headers)
        self.assertIn(('Content-Location', '/things/78'), self.srmock.headers)
        self.assertIn(('Content-Range', 'bytes 0-499/10240'),
                      self.srmock.headers)

    def test_response_header_helpers_on_head(self):
        self.resource = HeaderHelpersResource()
        self.api.add_route(self.test_route, self.resource)
        self._simulate_request(self.test_route, method="HEAD")

        content_type = 'x-falcon/peregrine'
        self.assertNotIn(('Content-Type', content_type), self.srmock.headers)

        self.assertIn(('Cache-Control', 'no-store'), self.srmock.headers)

    def test_vary_star(self):
        self.resource = VaryHeaderResource(['*'])
        self.api.add_route(self.test_route, self.resource)
        self._simulate_request(self.test_route)

        self.assertIn(('Vary', '*'), self.srmock.headers)

    def test_vary_header(self):
        self.resource = VaryHeaderResource(['accept-encoding'])
        self.api.add_route(self.test_route, self.resource)
        self._simulate_request(self.test_route)

        self.assertIn(('Vary', 'accept-encoding'), self.srmock.headers)

    def test_vary_headers(self):
        self.resource = VaryHeaderResource(['accept-encoding', 'x-auth-token'])
        self.api.add_route(self.test_route, self.resource)
        self._simulate_request(self.test_route)

        vary = 'accept-encoding, x-auth-token'
        self.assertIn(('Vary', vary), self.srmock.headers)

    def test_no_content_type(self):
        self.resource = DefaultContentTypeResource()
        self.api.add_route(self.test_route, self.resource)
        self._simulate_request(self.test_route)

        content_type = falcon.DEFAULT_MEDIA_TYPE
        self.assertNotIn(('Content-Type', content_type), self.srmock.headers)

    def test_custom_content_type(self):
        content_type = 'application/xml; charset=utf-8'
        self.resource = XmlResource(content_type)
        self.api.add_route(self.test_route, self.resource)

        self._simulate_request(self.test_route)
        self.assertIn(('Content-Type', content_type), self.srmock.headers)
