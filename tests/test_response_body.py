import pytest

import falcon
from falcon import testing


@pytest.fixture
def resp(asgi, util):
    return util.create_resp(asgi)


def test_append_body(resp):
    text = 'Hello beautiful world! '
    resp.text = ''

    for token in text.split():
        resp.text += token
        resp.text += ' '

    assert resp.text == text


def test_response_repr(resp):
    _repr = '<%s: %s>' % (resp.__class__.__name__, resp.status)
    assert resp.__repr__() == _repr


def test_content_length_set_on_head_with_no_body(asgi, util):
    class NoBody:
        def on_get(self, req, resp):
            pass

        on_head = on_get

    app = util.create_app(asgi)
    app.add_route('/', NoBody())

    result = testing.simulate_head(app, '/')

    assert result.status_code == 200
    assert result.headers['content-length'] == '0'


@pytest.mark.parametrize('method', ['GET', 'HEAD'])
def test_content_length_not_set_when_streaming_response(asgi, util, method):
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
            # NOTE(kgriffs): Using an iterator in lieu of a generator tests our
            #   support for iterators vs. generators.
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

    app = util.create_app(asgi)
    app.add_route('/', SynthesizedHeadAsync() if asgi else SynthesizedHead())

    result = testing.simulate_request(app, method)

    assert result.status_code == 200
    assert result.headers['content-type'] == falcon.MEDIA_TEXT
    assert 'content-length' not in result.headers

    if method == 'GET':
        assert result.text == 'Hello, World!'


class CodeResource:
    def on_get(self, req, resp):
        resp.content_type = 'text/x-malbolge'
        resp.media = "'&%$#\"!76543210/43,P0).'&%I6"
        resp.status = falcon.HTTP_725


def test_unsupported_response_content_type(asgi, util):
    app = util.create_app(asgi)
    app.add_route('/test.mal', CodeResource())

    resp = testing.simulate_get(app, '/test.mal')
    assert resp.status_code == 415


def test_response_body_rendition_error(asgi, util):
    class MalbolgeHandler(falcon.media.BaseHandler):
        def serialize(self, media, content_type):
            raise falcon.HTTPError(falcon.HTTP_753)

    app = util.create_app(asgi)
    app.resp_options.media_handlers['text/x-malbolge'] = MalbolgeHandler()
    app.add_route('/test.mal', CodeResource())

    resp = testing.simulate_get(app, '/test.mal')
    assert resp.status_code == 753

    # NOTE(kgriffs): Validate that del works on media handlers.
    del app.resp_options.media_handlers['text/x-malbolge']
    resp = testing.simulate_get(app, '/test.mal')
    assert resp.status_code == 415
