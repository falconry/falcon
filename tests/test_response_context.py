import pytest

from falcon import Response


class TestResponseContext(object):

    def test_default_response_context(self):
        resp = Response()

        resp.context.hello = 'World!'
        assert resp.context.hello == 'World!'
        assert resp.context['hello'] == 'World!'

        resp.context['note'] = 'Default Response.context_type used to be dict.'
        assert 'note' in resp.context
        assert hasattr(resp.context, 'note')
        assert resp.context.get('note') == resp.context['note']

    def test_custom_response_context(self):

        class MyCustomContextType(object):
            pass

        class MyCustomResponse(Response):
            context_type = MyCustomContextType

        resp = MyCustomResponse()
        assert isinstance(resp.context, MyCustomContextType)

    def test_custom_response_context_failure(self):

        class MyCustomResponse(Response):
            context_type = False

        with pytest.raises(TypeError):
            MyCustomResponse()

    def test_custom_response_context_factory(self):

        def create_context(resp):
            return {'resp': resp}

        class MyCustomResponse(Response):
            context_type = create_context

        resp = MyCustomResponse()
        assert isinstance(resp.context, dict)
        assert resp.context['resp'] is resp
