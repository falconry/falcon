from pathlib import Path


def test_hello_http_call(client):
    response = client.simulate_get('/hello')
    assert response.status_code == 200
    data = response.json
    assert data == {'hello': 'world'}


def test_fallback(client):
    response = client.simulate_get('/missing')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/html'
    index = Path(__file__).parent.parent / 'ws_tutorial/static/index.html'
    assert response.text == index.read_text()
