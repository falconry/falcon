from pathlib import Path

import pytest

import falcon
from falcon import testing


@pytest.fixture
def client(asgi, util):
    app = util.create_app(asgi)
    return testing.TestClient(app)


@pytest.fixture(scope='function')
def cors_client(asgi, util):
    # NOTE(kgriffs): Disable wrapping to test that built-in middleware does
    #   not require it (since this will be the case for non-test apps).
    with util.disable_asgi_non_coroutine_wrapping():
        app = util.create_app(asgi, cors_enable=True)
    return testing.TestClient(app)


class CORSHeaderResource:
    def on_get(self, req, resp):
        resp.text = "I'm a CORS test response"

    def on_delete(self, req, resp):
        resp.set_header('Access-Control-Allow-Origin', 'example.com')
        resp.text = "I'm a CORS test response"


class CORSOptionsResource:
    def on_options(self, req, resp):
        # No allow header set
        resp.set_header('Content-Length', '0')


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
        assert (
            'Access-Control-Allow-Origin'.lower()
            in dict(result.headers.lower_items()).keys()
        )

    def test_enabled_cors_should_accept_all_origins_requests(self, cors_client):
        cors_client.app.add_route('/', CORSHeaderResource())

        result = cors_client.simulate_get(headers={'Origin': 'localhost'})
        assert result.headers['Access-Control-Allow-Origin'] == '*'

        result = cors_client.simulate_delete(headers={'Origin': 'localhost'})
        assert result.headers['Access-Control-Allow-Origin'] == 'example.com'

    def test_enabled_cors_handles_preflighting(self, cors_client):
        cors_client.app.add_route('/', CORSHeaderResource())
        result = cors_client.simulate_options(
            headers=(
                ('Origin', 'localhost'),
                ('Access-Control-Request-Method', 'GET'),
                ('Access-Control-Request-Headers', 'X-PINGOTHER, Content-Type'),
            )
        )
        assert result.headers['Access-Control-Allow-Methods'] == 'DELETE, GET'
        assert (
            result.headers['Access-Control-Allow-Headers']
            == 'X-PINGOTHER, Content-Type'
        )
        assert (
            result.headers['Access-Control-Max-Age'] == '86400'
        )  # 24 hours in seconds

    def test_enabled_cors_handles_preflight_custom_option(self, cors_client):
        cors_client.app.add_route('/', CORSOptionsResource())
        result = cors_client.simulate_options(
            headers=(
                ('Origin', 'localhost'),
                ('Access-Control-Request-Method', 'GET'),
                ('Access-Control-Request-Headers', 'X-PINGOTHER, Content-Type'),
            )
        )
        assert 'Access-Control-Allow-Methods' not in result.headers
        assert 'Access-Control-Allow-Headers' not in result.headers
        assert 'Access-Control-Max-Age' not in result.headers
        assert 'Access-Control-Expose-Headers' not in result.headers
        assert 'Access-Control-Allow-Origin' not in result.headers

    def test_enabled_cors_handles_preflighting_no_headers_in_req(self, cors_client):
        cors_client.app.add_route('/', CORSHeaderResource())
        result = cors_client.simulate_options(
            headers=(
                ('Origin', 'localhost'),
                ('Access-Control-Request-Method', 'POST'),
            )
        )
        assert result.headers['Access-Control-Allow-Methods'] == 'DELETE, GET'
        assert result.headers['Access-Control-Allow-Headers'] == '*'
        assert (
            result.headers['Access-Control-Max-Age'] == '86400'
        )  # 24 hours in seconds

    def test_enabled_cors_static_route(self, cors_client):
        cors_client.app.add_static_route('/static', Path(__file__).parent)
        result = cors_client.simulate_options(
            f'/static/{Path(__file__).name}',
            headers=(
                ('Origin', 'localhost'),
                ('Access-Control-Request-Method', 'GET'),
            ),
        )

        assert result.headers['Access-Control-Allow-Methods'] == 'GET'
        assert result.headers['Access-Control-Allow-Headers'] == '*'
        assert result.headers['Access-Control-Max-Age'] == '86400'
        assert result.headers['Access-Control-Allow-Origin'] == '*'

    @pytest.mark.parametrize('support_options', [True, False])
    def test_enabled_cors_sink_route(self, cors_client, support_options):
        def my_sink(req, resp):
            if req.method == 'OPTIONS' and support_options:
                resp.set_header('ALLOW', 'GET')
            else:
                resp.text = 'my sink'

        cors_client.app.add_sink(my_sink, '/sink')
        result = cors_client.simulate_options(
            '/sink/123',
            headers=(
                ('Origin', 'localhost'),
                ('Access-Control-Request-Method', 'GET'),
            ),
        )

        if support_options:
            assert result.headers['Access-Control-Allow-Methods'] == 'GET'
            assert result.headers['Access-Control-Allow-Headers'] == '*'
            assert result.headers['Access-Control-Max-Age'] == '86400'
            assert result.headers['Access-Control-Allow-Origin'] == '*'
        else:
            assert 'Access-Control-Allow-Methods' not in result.headers
            assert 'Access-Control-Allow-Headers' not in result.headers
            assert 'Access-Control-Max-Age' not in result.headers
            assert 'Access-Control-Expose-Headers' not in result.headers
            assert 'Access-Control-Allow-Origin' not in result.headers

    @pytest.mark.parametrize('include_request_private_network', (True, False))
    def test_disabled_cors_private_network(
        self, cors_client, include_request_private_network
    ):
        # default scenario for cors middleware, where
        # allow private network is off by default

        cors_client.app.add_route('/', CORSHeaderResource())

        headers = (
            ('Origin', 'localhost'),
            ('Access-Control-Request-Method', 'GET'),
        )

        if include_request_private_network:
            headers = (
                *headers,
                ('Access-Control-Request-Private-Network', 'true'),
            )

        result = cors_client.simulate_options('/', headers=headers)

        h = result.headers

        assert 'Access-Control-Allow-Private-Network' not in h


@pytest.fixture(scope='function')
def make_cors_client(asgi, util):
    def make(middleware):
        app = util.create_app(asgi, middleware=middleware)
        return testing.TestClient(app)

    return make


class TestCustomCorsMiddleware:
    def test_raises(self):
        with pytest.raises(ValueError, match='passed to allow_origins'):
            falcon.CORSMiddleware(allow_origins=['*'])
        with pytest.raises(ValueError, match='passed to allow_credentials'):
            falcon.CORSMiddleware(allow_credentials=['*'])

    @pytest.mark.parametrize(
        'allow, fail_origins, success_origins',
        (
            ('*', [None], ['foo', 'bar']),
            ('test', ['other', 'Test', 'TEST'], ['test']),
            (
                ['foo', 'bar'],
                ['foo, bar', 'foobar', 'foo,bar', 'Foo', 'BAR'],
                ['foo', 'bar'],
            ),
        ),
    )
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
            assert (
                res.headers['Access-Control-Allow-Origin'] == '*'
                if allow == '*'
                else origin
            )
            h = dict(res.headers.lower_items()).keys()
            assert 'Access-Control-Allow-Credentials'.lower() not in h
            assert 'Access-Control-Expose-Headers'.lower() not in h

    def test_allow_credential_wildcard(self, make_cors_client):
        client = make_cors_client(falcon.CORSMiddleware(allow_credentials='*'))
        client.app.add_route('/', CORSHeaderResource())

        res = client.simulate_get(headers={'Origin': 'localhost'})
        assert res.headers['Access-Control-Allow-Origin'] == 'localhost'
        assert res.headers['Access-Control-Allow-Credentials'] == 'true'

    @pytest.mark.parametrize(
        'allow, successOrigin',
        (
            (['foo', 'bar'], ['foo', 'bar']),
            ('foo', ['foo']),
        ),
    )
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
            falcon.CORSMiddleware(allow_origins='test', allow_credentials='*')
        )
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

    @pytest.mark.parametrize(
        'attr, exp',
        (
            ('foo', 'foo'),
            ('foo, bar', 'foo, bar'),
            (['foo', 'bar'], 'foo, bar'),
        ),
    )
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

    def test_enabled_cors_private_network_headers(self, make_cors_client):
        client = make_cors_client(falcon.CORSMiddleware(allow_private_network=True))

        client.app.add_route('/', CORSHeaderResource())

        res = client.simulate_options(
            '/',
            headers=(
                ('Origin', 'localhost'),
                ('Access-Control-Request-Method', 'GET'),
                ('Access-Control-Request-Private-Network', 'true'),
            ),
        )

        assert res.headers['Access-Control-Allow-Private-Network'] == 'true'
