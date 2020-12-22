import re

import pytest

import falcon
import falcon.testing as testing

from _util import create_app, disable_asgi_non_coroutine_wrapping  # NOQA


class Proxy:
    def forward(self, req):
        return falcon.HTTP_503


class Sink:
    def __init__(self):
        self._proxy = Proxy()

    def __call__(self, req, resp, **kwargs):
        resp.status = self._proxy.forward(req)
        self.kwargs = kwargs


class SinkAsync(Sink):
    async def __call__(self, req, resp, **kwargs):
        super().__call__(req, resp, **kwargs)


def kitchen_sink(req, resp, **kwargs):
    resp.set_header('X-Missing-Feature', 'kitchen-sink')


async def async_kitchen_sink(req, resp, **kwargs):
    kitchen_sink(req, resp, **kwargs)


class BookCollection(testing.SimpleTestResource):
    pass


@pytest.fixture
def resource():
    return BookCollection()


@pytest.fixture
def sink(asgi):
    return SinkAsync() if asgi else Sink()


@pytest.fixture
def client(asgi):
    app = create_app(asgi)
    return testing.TestClient(app)


class TestDefaultRouting:

    def test_single_default_pattern(self, client, sink, resource):
        client.app.add_sink(sink)

        response = client.simulate_request(path='/')
        assert response.status == falcon.HTTP_503

    def test_single_simple_pattern(self, client, sink, resource):
        client.app.add_sink(sink, r'/foo')

        response = client.simulate_request(path='/foo/bar')
        assert response.status == falcon.HTTP_503

    def test_single_compiled_pattern(self, client, sink, resource):
        client.app.add_sink(sink, re.compile(r'/foo'))

        response = client.simulate_request(path='/foo/bar')
        assert response.status == falcon.HTTP_503

        response = client.simulate_request(path='/auth')
        assert response.status == falcon.HTTP_404

    def test_named_groups(self, client, sink, resource):
        client.app.add_sink(sink, r'/user/(?P<id>\d+)')

        response = client.simulate_request(path='/user/309')
        assert response.status == falcon.HTTP_503
        assert sink.kwargs['id'] == '309'

        response = client.simulate_request(path='/user/sally')
        assert response.status == falcon.HTTP_404

    def test_multiple_patterns(self, asgi, client, sink, resource):
        if asgi:
            async def sink_too(req, resp):
                resp.status = falcon.HTTP_781
        else:
            def sink_too(req, resp):
                resp.status = falcon.HTTP_781

        client.app.add_sink(sink, r'/foo')
        client.app.add_sink(sink_too, r'/foo')  # Last duplicate wins

        client.app.add_sink(sink, r'/katza')

        response = client.simulate_request(path='/foo/bar')
        assert response.status == falcon.HTTP_781

        response = client.simulate_request(path='/katza')
        assert response.status == falcon.HTTP_503

    def test_with_route(self, client, sink, resource):
        client.app.add_route('/books', resource)
        client.app.add_sink(sink, '/proxy')

        response = client.simulate_request(path='/proxy/books')
        assert not resource.called
        assert response.status == falcon.HTTP_503

        response = client.simulate_request(path='/books')
        assert resource.called
        assert response.status == falcon.HTTP_200

    def test_route_precedence(self, client, sink, resource):
        # NOTE(kgriffs): In case of collision, the route takes precedence.
        client.app.add_route('/books', resource)
        client.app.add_sink(sink, '/books')

        response = client.simulate_request(path='/books')
        assert resource.called
        assert response.status == falcon.HTTP_200

    def test_route_precedence_with_id(self, client, sink, resource):
        # NOTE(kgriffs): In case of collision, the route takes precedence.
        client.app.add_route('/books/{id}', resource)
        client.app.add_sink(sink, '/books')

        response = client.simulate_request(path='/books')
        assert not resource.called
        assert response.status == falcon.HTTP_503

    def test_route_precedence_with_both_id(self, client, sink, resource):
        # NOTE(kgriffs): In case of collision, the route takes precedence.
        client.app.add_route('/books/{id}', resource)
        client.app.add_sink(sink, r'/books/\d+')

        response = client.simulate_request(path='/books/123')
        assert resource.called
        assert response.status == falcon.HTTP_200


class TestSinkMethodCompatibility:

    def _verify_kitchen_sink(self, client):
        resp = client.simulate_request('BREW', '/features')
        assert resp.status_code == 200
        assert resp.headers.get('X-Missing-Feature') == 'kitchen-sink'

    def test_add_async_sink(self, client, asgi):
        if not asgi:
            with pytest.raises(falcon.CompatibilityError):
                client.app.add_sink(async_kitchen_sink)
        else:
            client.app.add_sink(async_kitchen_sink, '/features')
            self._verify_kitchen_sink(client)

    def test_add_sync_sink(self, client, asgi):
        if asgi:
            with disable_asgi_non_coroutine_wrapping():
                with pytest.raises(falcon.CompatibilityError):
                    client.app.add_sink(kitchen_sink)
        else:
            client.app.add_sink(kitchen_sink, '/features')
            self._verify_kitchen_sink(client)

    def test_add_sync_sink_with_wrapping(self, client, asgi):
        client.app.add_sink(kitchen_sink, '/features')
        self._verify_kitchen_sink(client)
