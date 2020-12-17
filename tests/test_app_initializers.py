import pytest

import falcon
from falcon import media, testing


class MediaResource:
    def on_get(self, req, resp):
        resp.media = {'foo': 'bar'}

    def on_post(self, req, resp):
        resp.media = req.media


class PlainTextHandler(media.BaseHandler):
    def serialize(self, media, content_type):
        return str(media).encode()

    def deserialize(self, stream, content_type, content_length):
        return stream.read().decode()


@pytest.fixture
def client(request):
    app = request.param(media_type=falcon.MEDIA_XML)
    app.add_route('/', MediaResource())

    app.resp_options.default_media_type = falcon.MEDIA_TEXT

    handlers = falcon.media.Handlers({
        'text/plain': PlainTextHandler()
    })
    app.req_options.media_handlers = handlers
    app.resp_options.media_handlers = handlers

    return testing.TestClient(app)


@pytest.mark.parametrize('client', (falcon.App, falcon.API,), indirect=True)
@pytest.mark.filterwarnings('ignore:Call to deprecated function')
def test_api_media_type_overriding(client):
    response = client.simulate_get('/')
    assert response.text == "{'foo': 'bar'}"
    assert response.headers['content-type'] == falcon.MEDIA_TEXT

    response = client.simulate_post('/', body='foobar', content_type=falcon.MEDIA_TEXT)
    assert response.text == 'foobar'
    assert response.headers['content-type'] == falcon.MEDIA_TEXT
