from falcon import status_codes
from falcon.testing import TestClient


def another_dummy_wsgi_app(environ, start_response):
    start_response(status_codes.HTTP_OK, [('Content-Type', 'text/plain')])

    yield b'It works!'


def test_testing_client_handles_generator_wsgi_apps_properly():
    client = TestClient(another_dummy_wsgi_app)

    response = client.simulate_get('/nevermind')

    assert response.status == status_codes.HTTP_OK
    assert response.text == 'It works!'
