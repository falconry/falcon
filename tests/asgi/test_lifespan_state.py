import pytest

import falcon
from falcon import testing
from falcon.asgi import App


class StateMiddleware:
    def __init__(self):
        self.lifespan_state = None

    async def process_startup(self, scope, event):
        self.lifespan_state = scope['state']
        scope['state']['message'] = 'Hello, lifespan state!'
        scope['state']['shared'] = []


class StateResource:
    def __init__(self):
        self.states = []

    async def on_get(self, req, resp):
        self.states.append(req.state)

        resp.media = req.state

    async def on_post(self, req, resp):
        self.states.append(req.state)

        req.state['added'] = 'request-specific'
        req.state['message'] = 'Overridden.'
        req.state['shared'].append('mutated')

    async def on_websocket(self, req, ws):
        self.states.append(req.state)

        await ws.accept()
        await ws.send_media(req.state)
        await ws.close()


@pytest.fixture
def resource():
    return StateResource()


@pytest.fixture
def middleware():
    return StateMiddleware()


@pytest.fixture
def app(resource, middleware):
    app = App(middleware=[middleware])
    app.add_route('/', resource)
    return app


def test_simulate_request(app, resource, middleware):
    result = testing.simulate_get(app, '/')

    assert result.status_code == 200
    assert result.json == {'message': 'Hello, lifespan state!', 'shared': []}

    assert len(resource.states) == 1
    assert resource.states[0] == middleware.lifespan_state
    assert resource.states[0] is not middleware.lifespan_state


def test_simulate_request_fresh_lifespan(app, resource):
    client = testing.TestClient(app)

    client.simulate_post('/')
    result = client.simulate_get('/')

    # Each simulate_*() call simulates the whole app lifecycle,
    #   so mutations of the stored objects do not persist either.
    assert result.json == {'message': 'Hello, lifespan state!', 'shared': []}


def test_simulate_request_explicit_state(app, resource):
    result = testing.simulate_get(app, '/', extras={'state': {'custom': 1337}})

    assert result.json == {'custom': 1337}


async def test_conductor_shallow_copy(app, resource, middleware):
    async with testing.ASGIConductor(app) as conductor:
        result = await conductor.simulate_post('/')
        assert result.status_code == 200

        result = await conductor.simulate_get('/')
        assert result.status_code == 200

    # Adding or replacing keys in the request state must not affect
    #   other requests, while mutations of the stored objects are shared.
    assert result.json == {'message': 'Hello, lifespan state!', 'shared': ['mutated']}
    assert middleware.lifespan_state == {
        'message': 'Hello, lifespan state!',
        'shared': ['mutated'],
    }

    post_state, get_state = resource.states
    assert post_state is not get_state
    assert post_state['shared'] is get_state['shared']


async def test_conductor_fresh_state_per_context(app, middleware):
    async with testing.ASGIConductor(app) as conductor:
        await conductor.simulate_post('/')
    first_state = middleware.lifespan_state

    async with testing.ASGIConductor(app) as conductor:
        result = await conductor.simulate_get('/')
    second_state = middleware.lifespan_state

    assert first_state is not second_state
    assert result.json == {'message': 'Hello, lifespan state!', 'shared': []}


async def test_conductor_explicit_state(app):
    async with testing.ASGIConductor(app) as conductor:
        result = await conductor.simulate_get('/', extras={'state': {'custom': 42}})

    assert result.json == {'custom': 42}


async def test_conductor_without_lifespan(app, resource):
    conductor = testing.ASGIConductor(app)

    result = await conductor.simulate_get('/')

    assert result.status_code == 200
    assert result.json is None
    assert resource.states == [None]


async def test_test_client_context(app, resource, middleware):
    async with testing.TestClient(app) as conductor:
        result = await conductor.simulate_get('/')

    assert result.json == {'message': 'Hello, lifespan state!', 'shared': []}


async def test_websocket(app, resource, middleware):
    async with testing.ASGIConductor(app) as conductor:
        async with conductor.simulate_ws('/') as ws:
            state = await ws.receive_json()

    assert state == {'message': 'Hello, lifespan state!', 'shared': []}
    assert resource.states[0] == middleware.lifespan_state
    assert resource.states[0] is not middleware.lifespan_state


async def test_websocket_without_lifespan(app, resource):
    conductor = testing.ASGIConductor(app)

    async with conductor.simulate_ws('/') as ws:
        state = await ws.receive_json()

    assert state is None
    assert resource.states == [None]


@pytest.mark.parametrize('state', [None, {}, {'db': 'connection'}])
def test_request_state_from_scope(state):
    scope = testing.create_scope()
    if state is not None:
        scope['state'] = state

    req = falcon.asgi.Request(scope, testing.ASGIRequestEventEmitter())

    assert req.state is state
