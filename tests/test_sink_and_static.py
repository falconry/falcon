import pytest

import falcon
from falcon import testing

from _util import create_app  # NOQA


def sink(req, res, **kw):
    res.body = 'sink'


async def sink_async(req, res, **kw):
    res.body = 'sink'


@pytest.fixture
def client(asgi, tmp_path):
    file = tmp_path / 'file.txt'
    file.write_text('foo bar')

    def make(sink_before_static_routes):
        app = create_app(asgi=asgi, sink_before_static_routes=sink_before_static_routes)
        app.add_sink(sink_async if asgi else sink, '/sink')
        app.add_static_route('/sink/static', str(tmp_path))

        return testing.TestClient(app)
    return make


def test_sink_before_static_routes(client):
    cl = client(True)
    res = cl.simulate_get('/sink/foo')
    assert res.text == 'sink'
    res = cl.simulate_get('/sink/static/file.txt')
    assert res.text == 'sink'
    res = cl.simulate_get('/sink/static/')
    assert res.text == 'sink'


def test_sink_after_static_routes(client):
    cl = client(False)
    res = cl.simulate_get('/sink/foo')
    assert res.text == 'sink'
    res = cl.simulate_get('/sink/static/file.txt')
    assert res.text == 'foo bar'
    res = cl.simulate_get('/sink/static/')
    assert res.status == falcon.HTTP_404
