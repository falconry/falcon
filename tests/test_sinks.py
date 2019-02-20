import re

import pytest

import falcon
import falcon.testing as testing


class Proxy(object):
    def forward(self, req):
        return falcon.HTTP_503


class Sink(object):

    def __init__(self):
        self._proxy = Proxy()

    def __call__(self, req, resp, **kwargs):
        resp.status = self._proxy.forward(req)
        self.kwargs = kwargs


def sink_too(req, resp):
    resp.status = falcon.HTTP_781


class BookCollection(testing.SimpleTestResource):
    pass


@pytest.fixture
def resource():
    return BookCollection()


@pytest.fixture
def sink():
    return Sink()


@pytest.fixture
def client():
    app = falcon.API()
    return testing.TestClient(app)


class TestDefaultRouting(object):

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

    def test_multiple_patterns(self, client, sink, resource):
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


class TestDefaultRoutingWithBuilderClient(object):

    def test_single_default_pattern(self, sink, resource):
        app = falcon.APIBuilder() \
            .add_sink(sink) \
            .build()
        client = testing.TestClient(app)

        response = client.simulate_request(path='/')
        assert response.status == falcon.HTTP_503

    def test_single_simple_pattern(self, sink, resource):
        app = falcon.APIBuilder() \
            .add_sink(sink, r'/foo') \
            .build()
        client = testing.TestClient(app)

        response = client.simulate_request(path='/foo/bar')
        assert response.status == falcon.HTTP_503

    def test_single_compiled_pattern(self, sink, resource):
        app = falcon.APIBuilder() \
            .add_sink(sink, re.compile(r'/foo')) \
            .build()
        client = testing.TestClient(app)

        response = client.simulate_request(path='/foo/bar')
        assert response.status == falcon.HTTP_503

        response = client.simulate_request(path='/auth')
        assert response.status == falcon.HTTP_404

    def test_named_groups(self, sink, resource):
        app = falcon.APIBuilder() \
            .add_sink(sink, r'/user/(?P<id>\d+)') \
            .build()
        client = testing.TestClient(app)

        response = client.simulate_request(path='/user/309')
        assert response.status == falcon.HTTP_503
        assert sink.kwargs['id'] == '309'

        response = client.simulate_request(path='/user/sally')
        assert response.status == falcon.HTTP_404

    def test_multiple_patterns(self, sink, resource):
        app = falcon.APIBuilder() \
            .add_sink(sink, r'/foo') \
            .add_sink(sink_too, r'/foo') \
            .add_sink(sink, r'/katza') \
            .build()  # Last duplicate wins

        client = testing.TestClient(app)

        response = client.simulate_request(path='/foo/bar')
        assert response.status == falcon.HTTP_781

        response = client.simulate_request(path='/katza')
        assert response.status == falcon.HTTP_503

    def test_with_route(self, sink, resource):
        app = falcon.APIBuilder() \
            .add_get_route('/books', resource.on_get) \
            .add_sink(sink, '/proxy') \
            .build()
        client = testing.TestClient(app)

        response = client.simulate_request(path='/proxy/books')
        assert not resource.called
        assert response.status == falcon.HTTP_503

        response = client.simulate_request(path='/books')
        assert resource.called
        assert response.status == falcon.HTTP_200

    def test_route_precedence(self, sink, resource):
        # NOTE(kgriffs): In case of collision, the route takes precedence.
        app = falcon.APIBuilder() \
            .add_get_route('/books', resource.on_get) \
            .add_sink(sink, '/books') \
            .build()
        client = testing.TestClient(app)

        response = client.simulate_request(path='/books')
        assert resource.called
        assert response.status == falcon.HTTP_200

    def test_route_precedence_with_id(self, sink, resource):
        # NOTE(kgriffs): In case of collision, the route takes precedence.
        app = falcon.APIBuilder() \
            .add_get_route('/books/{id}', resource.on_get) \
            .add_sink(sink, '/books') \
            .build()
        client = testing.TestClient(app)

        response = client.simulate_request(path='/books')
        assert not resource.called
        assert response.status == falcon.HTTP_503

    def test_route_precedence_with_both_id(self, sink, resource):
        # NOTE(kgriffs): In case of collision, the route takes precedence.
        app = falcon.APIBuilder() \
            .add_get_route('/books/{id}', resource.on_get) \
            .add_sink(sink, r'/books/\d+') \
            .build()
        client = testing.TestClient(app)

        response = client.simulate_request(path='/books/123')
        assert resource.called
        assert response.status == falcon.HTTP_200
