import falcon
import helpers


class HelloResource:
    sample_status = "200 OK"
    sample_body = "Hello World!"

    def __init__(self):
        self.called = False

    def on_get(self, ctx, req, resp):
        self.called = True

        self.ctx, self.req, self.resp = ctx, req, resp

        resp.status = falcon.HTTP_200
        resp.body = self.sample_body


class TestHelloWorld(helpers.TestSuite):

    def prepare(self):
        self.resource = HelloResource()
        self.api.add_route(self.test_route, self.resource)

        self.root_resource = helpers.TestResource()
        self.api.add_route('', self.root_resource)

    def test_empty_route(self):
        self._simulate_request('')
        self.assertTrue(self.root_resource.called)

    def test_hello_route_negative(self):
        bogus_route = self.test_route + 'x'
        self._simulate_request(bogus_route)

        # Ensure the request was NOT routed to resource
        self.assertFalse(self.resource.called)
        self.assertEquals(self.srmock.status, falcon.HTTP_404)

    def test_hello_route(self):
        self._simulate_request(self.test_route)
        resp = self.resource.resp

        self.assertEquals(resp.status, self.resource.sample_status)

        self.assertEquals(resp.body, self.resource.sample_body)
