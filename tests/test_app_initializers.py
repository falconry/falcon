import pytest

import falcon
from falcon import media, testing


class MediaResource:
    def on_get(self, req, resp):
        resp.media = {"foo": "bar"}


class MediaHTMLHandler(media.BaseHandler):
    def serialize(self, media, content_type):
        return str(media).encode()

    def deserialize(self, stream, content_type, content_length):
        return stream.read().decode()


@pytest.fixture
def client(request):
    app = request.param(media_type=falcon.MEDIA_XML)
    app.add_route('/', MediaResource())

    app.resp_options.default_media_type = falcon.MEDIA_HTML

    handlers = falcon.media.Handlers({
        'text/html': MediaHTMLHandler()
    })
    app.resp_options.media_handlers = handlers

    return testing.TestClient(app)


@pytest.mark.parametrize('client', (falcon.App,), indirect=True)
def test_api_media_type_overriding(client):
    response = client.simulate_get('/')
    actual_header = response.headers['content-type']
    actual_text = response.text

    assert actual_header == falcon.MEDIA_HTML
    assert actual_text == "{'foo': 'bar'}"


@pytest.mark.parametrize('client', (falcon.API,), indirect=True)
def test_app_media_type_overriding(client):
    response = client.simulate_get('/')
    actual_header = response.headers['content-type']
    actual_text = response.text

    assert actual_header == falcon.MEDIA_HTML
    assert actual_text == "{'foo': 'bar'}"
