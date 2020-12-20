import pytest

from falcon.testing import TestClient
from metrics import hello
from metrics import media


@pytest.mark.hello
def test_hello():
    client = TestClient(hello.create_app())

    resp = client.simulate_get('/')
    assert resp.status_code == 200
    assert resp.headers.get('Content-Type') == 'text/plain; charset=utf-8'


@pytest.mark.media
def test_media():
    client = TestClient(media.create_app())

    resp1 = client.simulate_post('/items', json={'foo': 'bar'})
    assert resp1.status_code == 201
    assert resp1.headers.get('Content-Type') == 'application/json'
    assert resp1.headers.get('Location') == '/items/bar001337'
    assert resp1.json == {'foo': 'bar', 'id': 'bar001337'}

    resp2 = client.simulate_post('/items', json={'apples': 'oranges'})
    assert resp2.status_code == 201
    assert resp2.headers.get('Content-Type') == 'application/json'
    assert resp2.headers.get('Location') == '/items/bar001337'
    assert resp2.json == {'apples': 'oranges', 'id': 'bar001337'}
