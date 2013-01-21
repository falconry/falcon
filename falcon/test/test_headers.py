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

    def test_no_body_on_1xx(self):
        self.resource = StatusTestResource(falcon.HTTP_102)
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

    def test_default_content_type(self):
        self.resource = DefaultContentTypeResource('Hello world!')
        self.api.add_route(self.test_route, self.resource)
        self._simulate_request(self.test_route)

        content_type = 'application/json; charset=utf-8'
        self.assertIn(('Content-Type', content_type), self.srmock.headers)

    def test_no_content_type(self):
        self.resource = DefaultContentTypeResource()
        self.api.add_route(self.test_route, self.resource)
        self._simulate_request(self.test_route)

        content_type = 'application/json; charset=utf-8'
        self.assertNotIn(('Content-Type', content_type), self.srmock.headers)

    def test_custom_content_type(self):
        content_type = 'application/xml; charset=utf-8'
        self.resource = XmlResource(content_type)
        self.api.add_route(self.test_route, self.resource)

        self._simulate_request(self.test_route)
        self.assertIn(('Content-Type', content_type), self.srmock.headers)
