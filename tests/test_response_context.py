import pytest

import falcon
import falcon.asgi


@pytest.fixture(params=[True, False], ids=['asgi.Response', 'Response'])
def resp_type(request):
    if request.param:
        return falcon.asgi.Response

    return falcon.Response


class TestResponseContext:
    def test_default_response_context(self, resp_type):
        resp = resp_type()

        resp.context.hello = 'World!'
        assert resp.context.hello == 'World!'
        assert resp.context['hello'] == 'World!'

        resp.context['note'] = 'Default Response.context_type used to be dict.'
        assert 'note' in resp.context
        assert hasattr(resp.context, 'note')
        assert resp.context.get('note') == resp.context['note']

    def test_custom_response_context(self, resp_type):
        class MyCustomContextType:
            pass

        class MyCustomResponse(resp_type):
            context_type = MyCustomContextType

        resp = MyCustomResponse()
        assert isinstance(resp.context, MyCustomContextType)

    def test_custom_response_context_failure(self, resp_type):
        class MyCustomResponse(resp_type):
            context_type = False

        with pytest.raises(TypeError):
            MyCustomResponse()

    def test_custom_response_context_factory(self, resp_type):
        def create_context(resp):
            return {'resp': resp}

        class MyCustomResponse(resp_type):
            context_type = create_context

        resp = MyCustomResponse()
        assert isinstance(resp.context, dict)
        assert resp.context['resp'] is resp
