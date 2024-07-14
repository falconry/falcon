def test_hello_http_call(client):
    response = client.simulate_get('/hello')
    assert response.status_code == 200
    data = response.json
    assert data == {'hello': 'world'}


def test_missing_endpoint(client):
    response = client.simulate_get('/missing')
    assert response.status_code == 404
