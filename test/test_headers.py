import testtools
from testtools.matchers import Equals, MatchesRegex, Contains, Not

import falcon
import test.helpers as helpers

class RequestHandler:
    sample_status = "200 OK"
    sample_body = helpers.rand_string(0, 128 * 1024)
    resp_headers = {
        'Content-Type': 'text/plain; charset=utf-8',
        'ETag': '10d4555ebeb53b30adf724ca198b32a2',
        'X-Hello': 'OH HAI'
    }

    def __init__(self):
        self.called = False

    def __call__(self, ctx, req, resp):
        self.called = True

        self.ctx, self.req, self.resp = ctx, req, resp

        resp.status = falcon.HTTP_200
        resp.body = self.sample_body
        resp.set_headers(self.resp_headers)

class RequestHandlerTestStatus:
    sample_body = helpers.rand_string(0, 128 * 1024)

    def __init__(self, status):
        self.status = status

    def __call__(self, ctx, req, resp):
        resp.status = self.status
        resp.body = self.sample_body


class TestHeaders(helpers.TestSuite):

    def prepare(self):
        self.on_hello = RequestHandler()
        self.api.add_route(self.test_route, self.on_hello)

    def test_content_length(self):
        self._simulate_request(self.test_route)

        headers = self.srmock.headers

        # Test Content-Length header set
        content_length = str(len(self.on_hello.sample_body))
        content_length_header = ('Content-Length', content_length)
        self.assertThat(headers, Contains(content_length_header))

    def test_prefer_host_header(self):
        self._simulate_request(self.test_route)

        # Make sure we picked up host from HTTP_HOST, not SERVER_NAME
        host = self.on_hello.req.get_header('host')
        self.assertThat(host, Equals('falconer'))

    def test_host_fallback(self):
        # Set protocol to 1.0 so that we won't get a host header
        self._simulate_request(self.test_route, protocol='HTTP/1.0')

        # Make sure we picked up host from HTTP_HOST, not SERVER_NAME
        host = self.on_hello.req.get_header('host')
        self.assertThat(host, Equals('localhost'))

    def test_host_fallback_port8000(self):
        # Set protocol to 1.0 so that we won't get a host header
        self._simulate_request(self.test_route, protocol='HTTP/1.0',
                               port='8000')

        # Make sure we picked up host from HTTP_HOST, not SERVER_NAME
        host = self.on_hello.req.get_header('host')
        self.assertThat(host, Equals('localhost:8000'))

    def test_no_body_on_1xx(self):
        self.request_handler = RequestHandlerTestStatus(falcon.HTTP_102)
        self.api.add_route('/1xx', self.request_handler)

        body = self._simulate_request('/1xx')
        self.assertThat(self.srmock.headers_dict,
                        Not(Contains('Content-Length')))

        self.assertThat(body, Equals([]))

    def test_no_body_on_101(self):
        self.request_handler = RequestHandlerTestStatus(falcon.HTTP_101)
        self.api.add_route('/1xx', self.request_handler)

        body = self._simulate_request('/1xx')
        self.assertThat(self.srmock.headers_dict,
                        Not(Contains('Content-Length')))

        self.assertThat(body, Equals([]))

    def test_no_body_on_204(self):
        self.request_handler = RequestHandlerTestStatus(falcon.HTTP_204)
        self.api.add_route('/204', self.request_handler)

        body = self._simulate_request('/204')
        self.assertThat(self.srmock.headers_dict,
                        Not(Contains('Content-Length')))

        self.assertThat(body, Equals([]))

    def test_no_body_on_304(self):
        self.request_handler = RequestHandlerTestStatus(falcon.HTTP_304)
        self.api.add_route('/304', self.request_handler)

        body = self._simulate_request('/304')
        self.assertThat(self.srmock.headers_dict,
                        Not(Contains('Content-Length')))

        self.assertThat(body, Equals([]))

    def test_passthrough_req_headers(self):
        req_headers = {
            'X-Auth-Token': 'Setec Astronomy',
            'Content-Type': 'text/plain; charset=utf-8'
        }
        self._simulate_request(self.test_route, headers=req_headers)

        for name, expected_value in req_headers.iteritems():
            actual_value = self.on_hello.req.get_header(name)
            self.assertThat(actual_value, Equals(expected_value))

    def test_passthrough_resp_headers(self):
        self._simulate_request(self.test_route)

        resp_headers = self.srmock.headers

        for h in self.on_hello.resp_headers.iteritems():
            self.assertThat(resp_headers, Contains(h))
