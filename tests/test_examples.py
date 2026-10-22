import pytest

import falcon.testing as testing


@pytest.fixture(scope='session')
def httpx2():
    return pytest.importorskip('httpx2')


@pytest.fixture(scope='session')
def requests():
    return pytest.importorskip('requests')


def test_quote(util):
    quote = util.load_module('examples/quote.py')

    resp = testing.simulate_get(quote.app, '/quote')

    assert resp.status_code == 200
    assert resp.json == {
        'author': 'Grace Hopper',
        'quote': "I've always been more interested in the future than in the past.",
    }


def test_things(asgi, util):
    suffix = '_asgi' if asgi else ''
    things = util.load_module(f'examples/things{suffix}.py')

    resp = testing.simulate_get(things.app, '/things')

    assert resp.status_code == 200
    assert resp.text == (
        '\nTwo things awe me most, the starry sky above me and the moral law within me.'
        '\n\n    ~ Immanuel Kant\n\n'
    )


def test_things_advanced(asgi, util, httpx2, requests):
    suffix = '_asgi' if asgi else ''
    advanced = util.load_module(f'examples/things_advanced{suffix}.py')

    resp1 = testing.simulate_get(advanced.app, '/1337/things')
    assert resp1.status_code == 401

    resp2 = testing.simulate_get(
        advanced.app,
        '/1337/things',
        headers={'Authorization': 'custom-token'},
    )
    assert resp2.status_code == 200
    assert len(resp2.json) == 1
    assert resp2.json[0]['color'] == 'green'

    resp3 = testing.simulate_post(
        advanced.app,
        '/1337/things',
        headers={'Authorization': 'custom-token', 'Content-Type': 'application/json'},
        body='{"key": "value"}',
    )
    assert resp3.status_code == 201

    resp4 = testing.simulate_post(
        advanced.app,
        '/1337/things',
        headers={
            'Authorization': 'custom-token',
            'Content-Type': 'application/json',
            'Content-Length': '1',
        },
        body='',
    )
    assert resp4.status_code == 400


@pytest.mark.parametrize('engine', ['ddg', 'y'])
@pytest.mark.parametrize('status_code', [200, 302, 503])
def test_things_advanced_asgi_sink(util, httpx2, monkeypatch, engine, status_code):
    advanced = util.load_module('examples/things_advanced_asgi.py')
    query = 'Falcon ASGI + café'
    body = '<html>Search results: café</html>'
    content_type = 'text/html; charset=utf-8'
    upstream_requests = []

    def upstream(request):
        upstream_requests.append(request)
        assert request.url.copy_with(query=None) == httpx2.URL(
            advanced.sink.engines[engine]
        )
        assert request.method == 'GET'
        assert dict(request.url.params) == {'q': query}
        return httpx2.Response(
            status_code, text=body, headers={'Content-Type': content_type}
        )

    client_type = httpx2.AsyncClient

    def create_client():
        return client_type(transport=httpx2.MockTransport(upstream))

    monkeypatch.setattr(httpx2, 'AsyncClient', create_client)

    resp = testing.simulate_get(
        advanced.app,
        f'/search/{engine}',
        params={'q': query},
        headers={'Authorization': 'custom-token'},
    )

    assert len(upstream_requests) == 1
    assert resp.status_code == status_code
    assert resp.content_type == content_type
    assert resp.text == body
