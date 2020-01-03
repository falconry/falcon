import pytest

import falcon
from falcon import testing

from _util import create_app, create_resp  # NOQA


@pytest.fixture
def resp(asgi):
    return create_resp(asgi)


def test_append_body(resp):
    text = 'Hello beautiful world! '
    resp.body = ''

    for token in text.split():
        resp.body += token
        resp.body += ' '

    assert resp.body == text


def test_response_repr(resp):
    _repr = '<%s: %s>' % (resp.__class__.__name__, resp.status)
    assert resp.__repr__() == _repr


def test_content_length_set_on_head_with_no_body(asgi):
    class NoBody:
        def on_get(self, req, resp):
            pass

        on_head = on_get

    app = create_app(asgi)
    app.add_route('/', NoBody())

    result = testing.simulate_head(app, '/')

    assert result.status_code == 200
    assert result.headers['content-length'] == '0'


@pytest.mark.parametrize('method', ['GET', 'HEAD'])
def test_content_length_not_set_when_streaming_response(asgi, method):
    class SynthesizedHead:
        def on_get(self, req, resp):
            def words():
                for word in ('Hello', ',', ' ', 'World!'):
                    yield word.encode()

            resp.content_type = falcon.MEDIA_TEXT
            resp.stream = words()

        on_head = on_get

    class SynthesizedHeadAsync:
        async def on_get(self, req, resp):
            # NOTE(kgriffs): Using an iterator in lieu of a generator
            #   makes this code parsable by 3.5 and also tests our support
            #   for iterators vs. generators.
            class Words:
                def __init__(self):
                    self._stream = iter(('Hello', ',', ' ', 'World!'))

                def __aiter__(self):
                    return self

                async def __anext__(self):
                    try:
                        return next(self._stream).encode()
                    except StopIteration:
                        pass  # Test Falcon's PEP 479 support

            resp.content_type = falcon.MEDIA_TEXT
            resp.stream = Words()

        on_head = on_get

    app = create_app(asgi)
    app.add_route('/', SynthesizedHeadAsync() if asgi else SynthesizedHead())

    result = testing.simulate_request(app, method)

    assert result.status_code == 200
    assert result.headers['content-type'] == falcon.MEDIA_TEXT
    assert 'content-length' not in result.headers

    if method == 'GET':
        assert result.text == 'Hello, World!'
