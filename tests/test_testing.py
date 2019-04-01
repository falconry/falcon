import pytest

from falcon import status_codes
from falcon.testing import closed_wsgi_iterable, TestClient


def another_dummy_wsgi_app(environ, start_response):
    start_response(status_codes.HTTP_OK, [('Content-Type', 'text/plain')])

    yield b'It works!'


def test_testing_client_handles_wsgi_generator_app():
    client = TestClient(another_dummy_wsgi_app)

    response = client.simulate_get('/nevermind')

    assert response.status == status_codes.HTTP_OK
    assert response.text == 'It works!'


@pytest.mark.parametrize('items', [
    (),
    (b'1',),
    (b'1', b'2'),
    (b'Hello, ', b'World', b'!\n'),
])
def test_closed_wsgi_iterable(items):
    assert tuple(closed_wsgi_iterable(items)) == items
