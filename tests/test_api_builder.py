
import pytest

import falcon
from falcon import testing
from falcon.api_builder import APIBuildException


def test_lambda_route():

    def example_route_func(request, response):
        response.status = falcon.HTTP_200
        response.body = 'Falcon'

    app = falcon.APIBuilder() \
        .add_get_route('/', example_route_func) \
        .build()

    client = testing.TestClient(app)
    result = client.simulate_get()
    assert result.status_code == 200
    assert result.text == 'Falcon'


def test_resource_with_named_functions():

    class ResourceWithNamedRoutes:

        def __init__(self):
            self._initial_stuff = None

        def get_stuff(self, request, response):
            if self._initial_stuff:
                response.status = falcon.HTTP_200
                response.body = self._initial_stuff
            else:
                response.status = falcon.HTTP_404

        def create_stuff(self, request, response):
            self._initial_stuff = request.media
            response.status = falcon.HTTP_201

        def update_stuff(self, request, response):
            self._initial_stuff = request.media
            response.status = falcon.HTTP_200

    resource = ResourceWithNamedRoutes()

    app = falcon.APIBuilder() \
        .add_get_route('/stuff', resource.get_stuff) \
        .add_post_route('/stuff', resource.create_stuff) \
        .add_put_route('/stuff', resource.update_stuff) \
        .build()

    client = testing.TestClient(app)

    result = client.simulate_get('/stuff')
    assert result.status_code == 404

    result = client.simulate_post('/stuff', json='STUFF')
    assert result.status_code == 201

    result = client.simulate_get('/stuff')
    assert result.status_code == 200
    assert result.text == 'STUFF'

    result = client.simulate_put('/stuff', json='OTHER_STUFF')
    assert result.status_code == 200

    result = client.simulate_get('/stuff')
    assert result.status_code == 200
    assert result.text == 'OTHER_STUFF'


def test_resource_with_multiple_equal_methods():

    class ResourceWithManyGets:

        def get_foo(self, request, response):
            response.status = falcon.HTTP_200
            response.body = 'Foo'

        def get_foos(self, request, response):
            response.status = falcon.HTTP_200
            response.body = 'Foo, FOO, foo, fOO'

    resource = ResourceWithManyGets()
    app = falcon.APIBuilder() \
        .add_get_route('/foo', resource.get_foo) \
        .add_get_route('/foos', resource.get_foos) \
        .build()

    client = testing.TestClient(app)

    result = client.simulate_get('/foo')
    assert result.status_code == 200
    assert result.text == 'Foo'

    result = client.simulate_get('/foos')
    assert result.status_code == 200
    assert result.text == 'Foo, FOO, foo, fOO'


def test_raises_on_invalid_method_add():
    def example_route_func(request, response):
        response.status = falcon.HTTP_200
        response.body = 'Falcon'

    with pytest.raises(APIBuildException):
        falcon.APIBuilder() \
            .add_method_route('PANTS', '/fizz', example_route_func) \
            .build()


def test_raises_on_overwriting_of_kwarg_for_uri():
    def example_route_func(request, response):
        response.status = falcon.HTTP_200
        response.body = 'Falcon'

    with pytest.raises(APIBuildException):
        falcon.APIBuilder() \
            .add_get_route('/fizz', example_route_func, buzz='buzz') \
            .add_put_route('/fizz', example_route_func, buzz='fizz') \
            .build()


def test_raise_on_using_same_uri_and_method():
    def example_route_func(request, response):
        response.status = falcon.HTTP_200
        response.body = 'Falcon'

    with pytest.raises(APIBuildException):
        falcon.APIBuilder() \
            .add_get_route('/fizz', example_route_func) \
            .add_get_route('/fizz', example_route_func) \
            .build()
