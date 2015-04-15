
import falcon
import falcon.testing as testing

from falcon.errors import HTTPUnsupportedProtocol
from falcon.testing.resource import TestResource


class _Middleware():
    """Convenience class for creating middleware."""
    def __init__(self, process_request=None, process_response=None,
                 process_resource=None):
        self._process_request = process_request
        self._process_response = process_response
        self._process_resource = process_resource

    def process_request(self, req, resp):
        if self._process_request is not None:
            self._process_request(req, resp)

    def process_response(self, req, resp, resource):
        if self._process_response is not None:
            self._process_response(req, resp)

    def process_resource(self, req, resp, resource):
        if self._process_resource is not None:
            self._process_resource(req, resp)


class TestEnsureHttps(testing.TestBase):

    def _http_unsupported_handler(self, exc, req, resp, params):
        self.assertEqual(type(exc), HTTPUnsupportedProtocol)
        self._caught_unsupported_protocol = True

    def _get_middleware(self):
        def process_request(req, resp):
            print "called", self._called_mw
            self.assertFalse(self._called_mw)
            self._called_mw = True

        return _Middleware(process_request=process_request)

    def setUp(self):
        super(TestEnsureHttps, self).setUp()
        self.api = falcon.API(middleware=self._get_middleware(),
                              enforce_https=True)
        self.api.add_route('/only_https', TestResource())
        self.api.add_error_handler(HTTPUnsupportedProtocol,
                                   handler=self._http_unsupported_handler)
        self._caught_unsupported_protocol = False
        self._called_mw = False

    def test_allow_https_scheme(self):
        self.simulate_request('/only_https', scheme='https')
        self.assertFalse(self._caught_unsupported_protocol)
        self.assertTrue(self._called_mw)

    def test_disallow_http_scheme(self):
        self.simulate_request('/only_https', scheme='http')
        self.assertTrue(self._caught_unsupported_protocol)
        self.assertFalse(self._called_mw)

    def test_allow_https_forwarded_proto(self):
        self.simulate_request('/only_https', scheme='http',
                              headers=dict(X_FORWARDED_PROTO='https'))
        self.assertFalse(self._caught_unsupported_protocol)
        self.assertTrue(self._called_mw)

    def test_allow_https_forwarded(self):
        forwarded_header = "for=client;proto=https,proto=http"
        headers = dict(X_FORWARDED_PROTO='http', FORWARDED=forwarded_header)
        self.simulate_request('/only_https', scheme='http',
                              headers=headers)
        self.assertFalse(self._caught_unsupported_protocol)
        self.assertTrue(self._called_mw)

    def test_disallow_forwarded_no_proto(self):
        forwarded_header = "for=client,for=nginx"
        headers = dict(X_FORWARDED_PROTO='http', FORWARDED=forwarded_header)
        self.simulate_request('/only_https', scheme='http',
                              headers=headers)
        self.assertTrue(self._caught_unsupported_protocol)
        self.assertFalse(self._called_mw)
