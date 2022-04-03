def test_list_images(client):
    resp1 = client.simulate_get('/images')
    assert resp1.status_code == 200
    assert resp1.headers.get('X-ASGILook-Cache') == 'Miss'
    assert resp1.json == []

    resp2 = client.simulate_get('/images')
    assert resp2.status_code == 200
    assert resp2.headers.get('X-ASGILook-Cache') == 'Hit'
    assert resp2.json == resp1.json


def test_missing_in_store(client):
    resp = client.simulate_get('/images/1a256a8a-2063-46ff-b53f-d04d5bcf5eee.jpeg')
    assert resp.status_code == 404


def test_post_one_image(client, png_image, image_size):
    resp1 = client.simulate_post('/images', body=png_image)
    location = resp1.headers.get('Location')
    assert resp1.status_code == 201
    assert location == '/images/36562622-48e5-4a61-be67-e426b11821ed.jpeg'

    resp2 = client.simulate_get(location)
    assert resp2.status_code == 200
    assert resp2.headers['Content-Type'] == 'image/jpeg'
    assert image_size(resp2.content) == (640, 360)


def test_post_three_images(client, png_image):
    for _ in range(3):
        client.simulate_post('/images', body=png_image)

    resp = client.simulate_get('/images')
    images = [(item['image'], item['size']) for item in resp.json]
    assert images == [
        ('/images/36562622-48e5-4a61-be67-e426b11821ed.jpeg', [640, 360]),
        ('/images/3bc731ac-8cd8-4f39-b6fe-1a195d3b4e74.jpeg', [640, 360]),
        ('/images/ba1c4951-73bc-45a4-a1f6-aa2b958dafa4.jpeg', [640, 360]),
    ]
