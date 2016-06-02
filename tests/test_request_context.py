from falcon.request import Request
import falcon.testing as testing


class TestRequestContext(testing.TestBase):

    def test_default_request_context(self):
        env = testing.create_environ()
        req = Request(env)
        self.assertIsInstance(req.context, dict)

    def test_custom_request_context(self):

        # Define a Request-alike with a custom context type
        class MyCustomContextType():
            pass

        class MyCustomRequest(Request):
            context_type = MyCustomContextType

        env = testing.create_environ()
        req = MyCustomRequest(env)
        self.assertIsInstance(req.context, MyCustomContextType)

    def test_custom_request_context_failure(self):

        # Define a Request-alike with a non-callable custom context type
        class MyCustomRequest(Request):
            context_type = False

        env = testing.create_environ()
        self.assertRaises(TypeError, MyCustomRequest, env)

    def test_custom_request_context_request_access(self):

        def create_context(req):
            return {'uri': req.uri}

        # Define a Request-alike with a custom context type
        class MyCustomRequest(Request):
            context_type = create_context

        env = testing.create_environ()
        req = MyCustomRequest(env)
        self.assertIsInstance(req.context, dict)
        self.assertEqual(req.context['uri'], req.uri)
