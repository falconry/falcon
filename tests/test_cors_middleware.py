import pytest

import falcon
from falcon import testing

from _util import create_app, disable_asgi_non_coroutine_wrapping  # NOQA


@pytest.fixture
def client(asgi):
    app = create_app(asgi)
    return testing.TestClient(app)


@pytest.fixture(scope='function')
def cors_client(asgi):
    # NOTE(kgriffs): Disable wrapping to test that built-in middleware does
    #   not require it (since this will be the case for non-test apps).
    with disable_asgi_non_coroutine_wrapping():
        app = create_app(asgi, cors_enable=True)
    return testing.TestClient(app)


class CORSHeaderResource:

    def on_get(self, req, resp):
        resp.text = "I'm a CORS test response"

    def on_delete(self, req, resp):
        resp.set_header('Access-Control-Allow-Origin', 'example.com')
        resp.text = "I'm a CORS test response"


class TestCorsMiddleware:

    def test_disabled_cors_should_not_add_any_extra_headers(self, client):
        client.app.add_route('/', CORSHeaderResource())
        result = client.simulate_get(headers={'Origin': 'localhost'})
        h = dict(result.headers.lower_items()).keys()
        assert 'Access-Control-Allow-Origin'.lower() not in h
        assert 'Access-Control-Allow-Credentials'.lower() not in h
        assert 'Access-Control-Expose-Headers'.lower() not in h

    def test_enabled_cors_no_origin(self, client):
        client.app.add_route('/', CORSHeaderResource())
        result = client.simulate_get()
        h = dict(result.headers.lower_items()).keys()
        assert 'Access-Control-Allow-Origin'.lower() not in h
        assert 'Access-Control-Allow-Credentials'.lower() not in h
        assert 'Access-Control-Expose-Headers'.lower() not in h

    def test_enabled_cors_should_add_extra_headers_on_response(self, cors_client):
        cors_client.app.add_route('/', CORSHeaderResource())
        result = cors_client.simulate_get(headers={'Origin': 'localhost'})
        assert 'Access-Control-Allow-Origin'.lower() in dict(
            result.headers.lower_items()).keys()

    def test_enabled_cors_should_accept_all_origins_requests(self, cors_client):
        cors_client.app.add_route('/', CORSHeaderResource())

        result = cors_client.simulate_get(headers={'Origin': 'localhost'})
        assert result.headers['Access-Control-Allow-Origin'] == '*'

        result = cors_client.simulate_delete(headers={'Origin': 'localhost'})
        assert result.headers['Access-Control-Allow-Origin'] == 'example.com'

    def test_enabled_cors_handles_preflighting(self, cors_client):
        cors_client.app.add_route('/', CORSHeaderResource())
        result = cors_client.simulate_options(headers=(
            ('Origin', 'localhost'),
            ('Access-Control-Request-Method', 'GET'),
            ('Access-Control-Request-Headers', 'X-PINGOTHER, Content-Type'),
        ))
        assert result.headers['Access-Control-Allow-Methods'] == 'DELETE, GET'
        assert result.headers['Access-Control-Allow-Headers'] == 'X-PINGOTHER, Content-Type'
        assert result.headers['Access-Control-Max-Age'] == '86400'  # 24 hours in seconds

    def test_enabled_cors_handles_preflighting_no_headers_in_req(self, cors_client):
        cors_client.app.add_route('/', CORSHeaderResource())
        result = cors_client.simulate_options(headers=(
            ('Origin', 'localhost'),
            ('Access-Control-Request-Method', 'POST'),
        ))
        assert result.headers['Access-Control-Allow-Methods'] == 'DELETE, GET'
        assert result.headers['Access-Control-Allow-Headers'] == '*'
        assert result.headers['Access-Control-Max-Age'] == '86400'  # 24 hours in seconds


@pytest.fixture(scope='function')
def make_cors_client(asgi):
    def make(middleware):
        app = create_app(asgi, middleware=middleware)
        return testing.TestClient(app)
    return make


class TestCustomCorsMiddleware:

    def test_raises(self):
        with pytest.raises(ValueError, match='passed to allow_origins'):
            falcon.CORSMiddleware(allow_origins=['*'])
        with pytest.raises(ValueError, match='passed to allow_credentials'):
            falcon.CORSMiddleware(allow_credentials=['*'])

    @pytest.mark.parametrize('allow, fail_origins, success_origins', (
        ('*', [None], ['foo', 'bar']),
        ('test', ['other', 'Test', 'TEST'], ['test']),
        (['foo', 'bar'], ['foo, bar', 'foobar', 'foo,bar', 'Foo', 'BAR'], ['foo', 'bar']),
    ))
    def test_allow_origin(self, make_cors_client, allow, fail_origins, success_origins):
        client = make_cors_client(falcon.CORSMiddleware(allow_origins=allow))
        client.app.add_route('/', CORSHeaderResource())

        for origin in fail_origins:
            h = {'Origin': origin} if origin is not None else {}
            res = client.simulate_get(headers=h)
            h = dict(res.headers.lower_items()).keys()
            assert 'Access-Control-Allow-Origin'.lower() not in h
            assert 'Access-Control-Allow-Credentials'.lower() not in h
            assert 'Access-Control-Expose-Headers'.lower() not in h

        for origin in success_origins:
            res = client.simulate_get(headers={'Origin': origin})
            assert res.headers['Access-Control-Allow-Origin'] == '*' if allow == '*' else origin
            h = dict(res.headers.lower_items()).keys()
            assert 'Access-Control-Allow-Credentials'.lower() not in h
            assert 'Access-Control-Expose-Headers'.lower() not in h

    def test_allow_credential_wildcard(self, make_cors_client):
        client = make_cors_client(falcon.CORSMiddleware(allow_credentials='*'))
        client.app.add_route('/', CORSHeaderResource())

        res = client.simulate_get(headers={'Origin': 'localhost'})
        assert res.headers['Access-Control-Allow-Origin'] == 'localhost'
        assert res.headers['Access-Control-Allow-Credentials'] == 'true'

    @pytest.mark.parametrize('allow, successOrigin', (
        (['foo', 'bar'], ['foo', 'bar']),
        ('foo', ['foo']),
    ))
    def test_allow_credential_list_or_str(self, make_cors_client, allow, successOrigin):
        client = make_cors_client(falcon.CORSMiddleware(allow_credentials=allow))
        client.app.add_route('/', CORSHeaderResource())

        for origin in ('foo, bar', 'foobar', 'foo,bar', 'Foo', 'BAR'):
            res = client.simulate_get(headers={'Origin': origin})
            assert res.headers['Access-Control-Allow-Origin'] == '*'
            h = dict(res.headers.lower_items()).keys()
            assert 'Access-Control-Allow-Credentials'.lower() not in h
            assert 'Access-Control-Expose-Headers'.lower() not in h

        for origin in successOrigin:
            res = client.simulate_get(headers={'Origin': origin})
            assert res.headers['Access-Control-Allow-Origin'] == origin
            assert res.headers['Access-Control-Allow-Credentials'] == 'true'
            h = dict(res.headers.lower_items()).keys()
            assert 'Access-Control-Expose-Headers'.lower() not in h

    def test_allow_credential_existing_origin(self, make_cors_client):
        client = make_cors_client(falcon.CORSMiddleware(allow_credentials='*'))
        client.app.add_route('/', CORSHeaderResource())

        res = client.simulate_delete(headers={'Origin': 'something'})
        assert res.headers['Access-Control-Allow-Origin'] == 'example.com'
        h = dict(res.headers.lower_items()).keys()
        assert 'Access-Control-Allow-Credentials'.lower() not in h

    def test_allow_origin_allow_credential(self, make_cors_client):
        client = make_cors_client(
            falcon.CORSMiddleware(allow_origins='test', allow_credentials='*'))
        client.app.add_route('/', CORSHeaderResource())

        for origin in ['foo', 'TEST']:
            res = client.simulate_get(headers={'Origin': origin})
            h = dict(res.headers.lower_items()).keys()
            assert 'Access-Control-Allow-Origin'.lower() not in h
            assert 'Access-Control-Allow-Credentials'.lower() not in h
            assert 'Access-Control-Expose-Headers'.lower() not in h

        res = client.simulate_get(headers={'Origin': 'test'})
        assert res.headers['Access-Control-Allow-Origin'] == 'test'
        assert res.headers['Access-Control-Allow-Credentials'] == 'true'
        h = dict(res.headers.lower_items()).keys()
        assert 'Access-Control-Expose-Headers'.lower() not in h

    @pytest.mark.parametrize('attr, exp', (
        ('foo', 'foo'),
        ('foo, bar', 'foo, bar'),
        (['foo', 'bar'], 'foo, bar'),
    ))
    def test_expose_headers(self, make_cors_client, attr, exp):
        client = make_cors_client(
            falcon.CORSMiddleware(expose_headers=attr, allow_credentials=None)
        )
        client.app.add_route('/', CORSHeaderResource())

        res = client.simulate_get(headers={'Origin': 'something'})
        assert res.headers['Access-Control-Allow-Origin'] == '*'
        assert res.headers['Access-Control-Expose-Headers'] == exp
        h = dict(res.headers.lower_items()).keys()
        assert 'Access-Control-Allow-Credentials'.lower() not in h
