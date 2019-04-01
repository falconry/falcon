import pytest

from falcon.request import Request
import falcon.testing as testing


class TestRequestContext(object):

    def test_default_request_context(self):
        env = testing.create_environ()
        req = Request(env)

        req.context.hello = 'World'
        assert req.context.hello == 'World'
        assert req.context['hello'] == 'World'

        req.context['note'] = 'Default Request.context_type used to be dict.'
        assert 'note' in req.context
        assert hasattr(req.context, 'note')
        assert req.context.get('note') == req.context['note']

    def test_custom_request_context(self):

        # Define a Request-alike with a custom context type
        class MyCustomContextType():
            pass

        class MyCustomRequest(Request):
            context_type = MyCustomContextType

        env = testing.create_environ()
        req = MyCustomRequest(env)
        assert isinstance(req.context, MyCustomContextType)

    def test_custom_request_context_failure(self):

        # Define a Request-alike with a non-callable custom context type
        class MyCustomRequest(Request):
            context_type = False

        env = testing.create_environ()
        with pytest.raises(TypeError):
            MyCustomRequest(env)

    def test_custom_request_context_request_access(self):

        def create_context(req):
            return {'uri': req.uri}

        # Define a Request-alike with a custom context type
        class MyCustomRequest(Request):
            context_type = create_context

        env = testing.create_environ()
        req = MyCustomRequest(env)
        assert isinstance(req.context, dict)
        assert req.context['uri'] == req.uri
