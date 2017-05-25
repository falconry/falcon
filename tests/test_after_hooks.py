import functools

import pytest

try:
    import ujson as json
except ImportError:
    import json

import falcon
from falcon import testing


# --------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------


@pytest.fixture
def wrapped_resource_aware():
    return ClassResourceWithAwareHooks()


@pytest.fixture
def wrapped_resource():
    return WrappedClassResource()


@pytest.fixture
def client():
    app = falcon.API()

    resource = WrappedRespondersResource()
    app.add_route('/', resource)

    return testing.TestClient(app)


# --------------------------------------------------------------------
# Hooks
# --------------------------------------------------------------------


def validate_output(req, resp):
    raise falcon.HTTPError(falcon.HTTP_723, 'Tricky')


def serialize_body(req, resp):
    body = resp.body
    if body is not None:
        resp.body = json.dumps(body)
    else:
        resp.body = 'Nothing to see here. Move along.'


def fluffiness(req, resp):
    resp.body = 'fluffy'


def resource_aware_fluffiness(req, resp, resource):
    assert resource
    fluffiness(req, resp)


class ResourceAwareFluffiness(object):
    def __call__(self, req, resp, resource):
        assert resource
        fluffiness(req, resp)


def cuteness(req, resp):
    if resp.body == 'fluffy':
        resp.body += ' and cute'


def resource_aware_cuteness(req, resp, resource):
    assert resource
    cuteness(req, resp)


class Smartness(object):
    def __call__(self, req, resp):
        if resp.body:
            resp.body += ' and smart'
        else:
            resp.body = 'smart'


# NOTE(kgriffs): Use partial methods for these next two in order
# to make sure we handle that correctly.
def things_in_the_head(header, value, req, resp, params):
    resp.set_header(header, value)


bunnies_in_the_head = functools.partial(things_in_the_head,
                                        'X-Bunnies', 'fluffy')

cuteness_in_the_head = functools.partial(things_in_the_head,
                                         'X-Cuteness', 'cute')


def fluffiness_in_the_head(req, resp):
    resp.set_header('X-Fluffiness', 'fluffy')


def cuteness_in_the_head(req, resp):
    resp.set_header('X-Cuteness', 'cute')


# --------------------------------------------------------------------
# Resources
# --------------------------------------------------------------------


class WrappedRespondersResource(object):

    @falcon.after(serialize_body)
    @falcon.after(validate_output)
    def on_get(self, req, resp):
        self.req = req
        self.resp = resp

    @falcon.after(serialize_body)
    def on_put(self, req, resp):
        self.req = req
        self.resp = resp
        resp.body = {'animal': 'falcon'}

    @falcon.after(Smartness())
    def on_post(self, req, resp):
        pass


@falcon.after(cuteness)
@falcon.after(fluffiness)
class WrappedClassResource(object):

    # Test that the decorator skips non-callables
    on_post = False

    def __init__(self):
        # Test that the decorator skips non-callables
        self.on_patch = []

    def on_get(self, req, resp):
        self.req = req
        self.resp = resp

    @falcon.after(fluffiness_in_the_head)
    @falcon.after(cuteness_in_the_head)
    def on_head(self, req, resp):
        self.req = req
        self.resp = resp


# NOTE(swistakm): we use both type of hooks (class and method)
# at once for the sake of simplicity
@falcon.after(resource_aware_cuteness)
class ClassResourceWithAwareHooks(object):

    # Test that the decorator skips non-callables
    on_post = False

    hook_as_class = ResourceAwareFluffiness()

    def __init__(self):
        # Test that the decorator skips non-callables
        self.on_patch = []

    @falcon.after(resource_aware_fluffiness)
    def on_get(self, req, resp):
        self._capture(req, resp)

    @falcon.after(resource_aware_fluffiness)
    def on_head(self, req, resp):
        self._capture(req, resp)

    @falcon.after(hook_as_class)
    def on_put(self, req, resp):
        self._capture(req, resp)

    @falcon.after(hook_as_class.__call__)
    def on_post(self, req, resp):
        self._capture(req, resp)

    def _capture(self, req, resp):
        self.req = req
        self.resp = resp


# --------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------


def test_output_validator(client):
    result = client.simulate_get()
    assert result.status_code == 723
    assert result.text == json.dumps({'title': 'Tricky'})


def test_serializer(client):
    result = client.simulate_put()
    assert result.text == json.dumps({'animal': 'falcon'})


def test_hook_as_callable_class(client):
    result = client.simulate_post()
    assert 'smart' == result.text


def test_wrapped_resource(client, wrapped_resource):
    client.app.add_route('/wrapped', wrapped_resource)
    result = client.simulate_get('/wrapped')
    assert result.status_code == 200
    assert result.text == 'fluffy and cute'

    result = client.simulate_head('/wrapped')
    assert result.status_code == 200
    assert result.headers['X-Fluffiness'] == 'fluffy'
    assert result.headers['X-Cuteness'] == 'cute'

    result = client.simulate_post('/wrapped')
    assert result.status_code == 405

    result = client.simulate_patch('/wrapped')
    assert result.status_code == 405

    # Decorator should not affect the default on_options responder
    result = client.simulate_options('/wrapped')
    assert result.status_code == 200
    assert not result.text


def test_wrapped_resource_with_hooks_aware_of_resource(client, wrapped_resource_aware):
    client.app.add_route('/wrapped_aware', wrapped_resource_aware)
    expected = 'fluffy and cute'

    result = client.simulate_get('/wrapped_aware')
    assert result.status_code == 200
    assert expected == result.text

    for test in (
        client.simulate_head,
        client.simulate_put,
        client.simulate_post,
    ):
        result = test(path='/wrapped_aware')
        assert result.status_code == 200
        assert wrapped_resource_aware.resp.body == expected

    result = client.simulate_patch('/wrapped_aware')
    assert result.status_code == 405

    # Decorator should not affect the default on_options responder
    result = client.simulate_options('/wrapped_aware')
    assert result.status_code == 200
    assert not result.text
