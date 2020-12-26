import pytest

from falcon.testing import TestClient
from metrics import asgi
from metrics import hello
from metrics import media
from metrics import query


@pytest.mark.asgi
def test_asgi():
    client = TestClient(asgi.create_app())

    resp = client.simulate_get('/')
    assert resp.status_code == 200
    assert resp.headers.get('Content-Type') == 'text/plain; charset=utf-8'
    assert resp.text == 'Hello, World!\n'


@pytest.mark.hello
def test_hello():
    client = TestClient(hello.create_app())

    resp = client.simulate_get('/')
    assert resp.status_code == 200
    assert resp.headers.get('Content-Type') == 'text/plain; charset=utf-8'
    assert resp.text == 'Hello, World!\n'


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


@pytest.mark.query
def test_query():
    client = TestClient(query.create_app())

    resp1 = client.simulate_get(
        '/path?flag1&flag2=&flag3&framework=falcon&resp_status=204&'
        'fruit=apple&flag4=true&fruit=orange&status=%F0%9F%8E%89&'
        'fruit=banana',
        headers={'X-Framework': 'falcon', 'X-Falcon': 'peregrine'},
    )
    assert resp1.status_code == 204
    assert resp1.headers.get('X-Falcon') == 'peregrine'
    assert resp1.text == ''

    resp2 = client.simulate_get(
        '/path?flag1&flag2=&flag3&framework=falcon&resp_status=200&'
        'fruit=apple&flag4=true&fruit=orange&status=%F0%9F%8E%89&'
        'fruit=banana',
        headers={'X-Framework': 'falcon', 'X-Falcon': 'peregrine'},
    )
    assert resp2.status_code == 200
    assert resp2.headers.get('X-Falcon') == 'peregrine'
    assert resp2.text == 'falcon'
