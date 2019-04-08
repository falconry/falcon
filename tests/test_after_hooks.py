import functools
import json

import pytest

import falcon
from falcon import testing


# --------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------


@pytest.fixture
def wrapped_resource_aware():
    return ClassResourceWithAwareHooks()


@pytest.fixture
def client():
    app = falcon.API()

    resource = WrappedRespondersResource()
    app.add_route('/', resource)

    return testing.TestClient(app)


# --------------------------------------------------------------------
# Hooks
# --------------------------------------------------------------------


def validate_output(req, resp, resource):
    assert resource
    raise falcon.HTTPError(falcon.HTTP_723, 'Tricky')


def serialize_body(req, resp, resource):
    assert resource

    body = resp.body
    if body is not None:
        resp.body = json.dumps(body)
    else:
        resp.body = 'Nothing to see here. Move along.'


def fluffiness(req, resp, resource, animal=''):
    assert resource

    resp.body = 'fluffy'
    if animal:
        resp.set_header('X-Animal', animal)


class ResourceAwareFluffiness(object):
    def __call__(self, req, resp, resource):
        fluffiness(req, resp, resource)


def cuteness(req, resp, resource, check, postfix=' and cute'):
    assert resource
    if resp.body == check:
        resp.body += postfix


def resource_aware_cuteness(req, resp, resource):
    assert resource
    cuteness(req, resp, resource, 'fluffy')


class Smartness(object):
    def __call__(self, req, resp, resource):
        assert resource
        if resp.body:
            resp.body += ' and smart'
        else:
            resp.body = 'smart'


# NOTE(kgriffs): Use partial methods for these next two in order
# to make sure we handle that correctly.
def things_in_the_head(header, value, req, resp, resource):
    assert resource
    resp.set_header(header, value)


bunnies_in_the_head = functools.partial(things_in_the_head,
                                        'X-Bunnies', 'fluffy')


cuteness_in_the_head = functools.partial(things_in_the_head,
                                         'X-Cuteness', 'cute')


def fluffiness_in_the_head(req, resp, resource, value='fluffy'):
    resp.set_header('X-Fluffiness', value)


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


@falcon.after(cuteness, 'fluffy', postfix=' and innocent')
@falcon.after(fluffiness, 'kitten')
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


class WrappedClassResourceChild(WrappedClassResource):
    def on_head(self, req, resp):
        # Test passing no extra args
        super(WrappedClassResourceChild, self).on_head(req, resp)


class ClassResourceWithURIFields(object):

    @falcon.after(fluffiness_in_the_head, 'fluffy')
    def on_get(self, req, resp, field1, field2):
        self.fields = (field1, field2)


class ClassResourceWithURIFieldsChild(ClassResourceWithURIFields):

    def on_get(self, req, resp, field1, field2):
        # Test passing mixed args and kwargs
        super(ClassResourceWithURIFieldsChild, self).on_get(
            req,
            resp,
            field1,
            field2=field2
        )


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

    @falcon.after(fluffiness)
    def on_get(self, req, resp):
        self._capture(req, resp)

    @falcon.after(fluffiness)
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


@pytest.mark.parametrize(
    'resource',
    [
        ClassResourceWithURIFields(),
        ClassResourceWithURIFieldsChild()
    ]
)
def test_resource_with_uri_fields(client, resource):
    client.app.add_route('/{field1}/{field2}', resource)

    result = client.simulate_get('/82074/58927')

    assert result.status_code == 200
    assert result.headers['X-Fluffiness'] == 'fluffy'
    assert 'X-Cuteness' not in result.headers
    assert resource.fields == ('82074', '58927')


@pytest.mark.parametrize(
    'resource',
    [
        WrappedClassResource(),
        WrappedClassResourceChild()
    ]
)
def test_wrapped_resource(client, resource):
    client.app.add_route('/wrapped', resource)
    result = client.simulate_get('/wrapped')
    assert result.status_code == 200
    assert result.text == 'fluffy and innocent'
    assert result.headers['X-Animal'] == 'kitten'

    result = client.simulate_head('/wrapped')
    assert result.status_code == 200
    assert result.headers['X-Fluffiness'] == 'fluffy'
    assert result.headers['X-Cuteness'] == 'cute'
    assert result.headers['X-Animal'] == 'kitten'

    result = client.simulate_post('/wrapped')
    assert result.status_code == 405

    result = client.simulate_patch('/wrapped')
    assert result.status_code == 405

    # Decorator should not affect the default on_options responder
    result = client.simulate_options('/wrapped')
    assert result.status_code == 200
    assert not result.text
    assert 'X-Animal' not in result.headers


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


class ResourceAwareGameHook(object):

    VALUES = ('rock', 'scissors', 'paper')

    @classmethod
    def __call__(cls, req, resp, resource):
        assert resource
        assert resource.seed in cls.VALUES
        assert resp.text == 'Responder called.'

        header = resp.get_header('X-Hook-Game')
        values = header.split(', ') if header else []
        if values:
            last = cls.VALUES.index(values[-1])
            values.append(cls.VALUES[(last + 1) % len(cls.VALUES)])
        else:
            values.append(resource.seed)
        resp.set_header('X-Hook-Game', ', '.join(values))


_game_hook = ResourceAwareGameHook()


@falcon.after(_game_hook)
@falcon.after(_game_hook)
class HandGame(object):

    def __init__(self):
        self.seed = None

    @falcon.after(_game_hook)
    def on_put(self, req, resp):
        self.seed = req.media
        resp.text = 'Responder called.'

    @falcon.after(_game_hook)
    def on_get_once(self, req, resp):
        resp.text = 'Responder called.'

    @falcon.after(_game_hook)
    @falcon.after(_game_hook)
    def on_get_twice(self, req, resp):
        resp.text = 'Responder called.'

    @falcon.after(_game_hook)
    @falcon.after(_game_hook)
    @falcon.after(_game_hook)
    def on_get_thrice(self, req, resp):
        resp.text = 'Responder called.'


@pytest.fixture
def game_client():
    app = falcon.API()
    resource = HandGame()

    app.add_route('/seed', resource)
    app.add_route('/once', resource, suffix='once')
    app.add_route('/twice', resource, suffix='twice')
    app.add_route('/thrice', resource, suffix='thrice')

    return testing.TestClient(app)


@pytest.mark.parametrize('seed,uri,expected', [
    ('paper', '/once', 'paper, rock, scissors'),
    ('scissors', '/twice', 'scissors, paper, rock, scissors'),
    ('rock', '/thrice', 'rock, scissors, paper, rock, scissors'),
    ('paper', '/thrice', 'paper, rock, scissors, paper, rock'),
])
def test_after_hooks_on_suffixed_resource(game_client, seed, uri, expected):
    game_client.simulate_put('/seed', json=seed)

    resp = game_client.simulate_get(uri)
    assert resp.status_code == 200
    assert resp.headers['X-Hook-Game'] == expected
