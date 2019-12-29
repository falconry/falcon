import falcon
import falcon.testing as testing


class MediaTypeResource:
    def on_get(self, req, resp):
        resp.body = 'foo bar'


def test_api_media_type_overriding():
    expected_header = 'text/html'

    api = falcon.API(media_type=expected_header)
    api.add_route('/', MediaTypeResource())
    client = testing.TestClient(api)

    response = client.simulate_get('/')
    actual_header = response.headers['content-type']

    assert expected_header == actual_header


def test_app_media_type_overriding():
    expected_header = 'text/html'

    api = falcon.App(media_type=expected_header)
    api.add_route('/', MediaTypeResource())
    client = testing.TestClient(api)

    response = client.simulate_get('/')
    actual_header = response.headers['content-type']

    assert expected_header == actual_header
