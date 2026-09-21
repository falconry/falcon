def test_list_images(client):
    resp = client.simulate_get('/images')

    assert resp.status_code == 200
    assert resp.json == []
