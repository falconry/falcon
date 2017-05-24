import pytest

from falcon import Response


class TestRequestContext(object):

    def test_default_response_context(self):
        resp = Response()
        assert isinstance(resp.context, dict)

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
