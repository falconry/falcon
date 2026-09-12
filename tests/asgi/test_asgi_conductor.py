import pytest

import falcon
from falcon import testing
from falcon.asgi import App


async def test_default_headers():
    class Resource:
        async def on_get(self, req, resp):
            resp.set_header('the-answer', req.get_header('the-answer'))

    app = App()
    app.add_route('/', Resource())
    client = testing.TestClient(app, headers={'the-answer': '42'})

    async with client as conductor:
        result = await conductor.simulate_get()
        assert result.headers['the-answer'] == '42'


@pytest.mark.parametrize('simulate_method', ['request', 'simulate_request'])
async def test_generic_request(simulate_method):
    class Resource:
        async def on_lock(self, req, resp):
            raise falcon.HTTPUnprocessableEntity

    app = App()
    app.add_route('/file', Resource())
    client = testing.TestClient(app)

    async with client as conductor:
        simulate_request = getattr(conductor, simulate_method)
        result = await simulate_request('LOCK', '/file')
        assert result.status_code == 422


async def test_wsgi_not_supported():
    with pytest.raises(falcon.CompatibilityError):
        async with testing.TestClient(falcon.App()):
            pass

    with pytest.raises(falcon.CompatibilityError):
        async with testing.ASGIConductor(falcon.App()):
            pass


@pytest.mark.parametrize(
    'method', ['get', 'head', 'post', 'put', 'options', 'patch', 'delete']
)
@pytest.mark.parametrize('use_alias', ['alias', 'simulate'])
async def test_responders(method, use_alias):
    class Resource:
        async def on_get(self, req, resp):
            resp.set_header('method', 'get')

        async def on_head(self, req, resp):
            resp.set_header('method', 'head')

        async def on_post(self, req, resp):
            resp.set_header('method', 'post')

        async def on_put(self, req, resp):
            resp.set_header('method', 'put')

        async def on_options(self, req, resp):
            resp.set_header('method', 'options')

        async def on_patch(self, req, resp):
            resp.set_header('method', 'patch')

        async def on_delete(self, req, resp):
            resp.set_header('method', 'delete')

    resource = Resource()

    app = App()
    app.add_route('/', resource)

    async with testing.ASGIConductor(app) as conductor:
        name = method if use_alias == 'alias' else 'simulate_' + method
        simulate = getattr(conductor, name)
        result = await simulate('/')
        assert result.headers['method'] == method
