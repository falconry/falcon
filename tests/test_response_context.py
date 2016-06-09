from falcon import Response
import falcon.testing as testing


class TestRequestContext(testing.TestBase):

    def test_default_response_context(self):
        resp = Response()
        self.assertIsInstance(resp.context, dict)

    def test_custom_response_context(self):

        class MyCustomContextType(object):
            pass

        class MyCustomResponse(Response):
            context_type = MyCustomContextType

        resp = MyCustomResponse()
        self.assertIsInstance(resp.context, MyCustomContextType)

    def test_custom_response_context_failure(self):

        class MyCustomResponse(Response):
            context_type = False

        self.assertRaises(TypeError, MyCustomResponse)

    def test_custom_response_context_factory(self):

        def create_context(resp):
            return {'resp': resp}

        class MyCustomResponse(Response):
            context_type = create_context

        resp = MyCustomResponse()
        self.assertIsInstance(resp.context, dict)
        self.assertIs(resp.context['resp'], resp)
