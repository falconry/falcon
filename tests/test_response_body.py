import pytest

from ._util import create_resp


@pytest.fixture(params=[True, False])
def resp(request):
    return create_resp(asgi=request.param)


class TestResponseBody:

    def test_append_body(self, resp):
        text = 'Hello beautiful world! '
        resp.body = ''

        for token in text.split():
            resp.body += token
            resp.body += ' '

        assert resp.body == text

    def test_response_repr(self, resp):
        _repr = '<%s: %s>' % (resp.__class__.__name__, resp.status)
        assert resp.__repr__() == _repr
