from examples.things import app
import falcon.testing as testing


def test_things_resource_response():
    client = testing.TestClient(app)

    resp = client.simulate_get('/things')

    assert resp.status_code == 200
    assert resp.text == (
        '\nTwo things awe me most, the starry sky above me and the moral law within me.'
        '\n\n    ~ Immanuel Kant\n\n'
    )
