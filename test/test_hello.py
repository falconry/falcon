import falcon
import helpers


class HelloRequestHandler:
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
        self.on_hello = HelloRequestHandler()
        self.api.add_route(self.test_route, self.on_hello)

        self.root_reqhandler = helpers.RequestHandler()
        self.api.add_route('', self.root_reqhandler)

    def test_empty_route(self):
        self._simulate_request('')
        self.assertTrue(self.root_reqhandler.called)

    def test_hello_route_negative(self):
        bogus_route = self.test_route + 'x'
        self._simulate_request(bogus_route)

        # Ensure the request was NOT routed to on_hello
        self.assertFalse(self.on_hello.called)
        self.assertEquals(self.srmock.status, falcon.HTTP_404)

    def test_hello_route(self):
        self._simulate_request(self.test_route)
        resp = self.on_hello.resp

        self.assertEquals(resp.status, self.on_hello.sample_status)

        self.assertEquals(resp.body, self.on_hello.sample_body)
