import pytest

from falcon import testing
from falcon.asgi import App, SSEvent


def test_no_events():

    class Emitter:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    class SomeResource:
        async def on_get(self, req, resp):
            self._called = True
            resp.sse = Emitter()

    resource = SomeResource()

    app = App()
    app.add_route('/', resource)

    client = testing.TestClient(app)
    client.simulate_get()

    assert resource._called


def test_single_event():
    class SomeResource:
        async def on_get(self, req, resp):
            async def emitter():
                yield

            resp.sse = emitter()

        async def on_post(self, req, resp):
            async def emitter():
                yield SSEvent()

            resp.sse = emitter()

    resource = SomeResource()

    app = App()
    app.add_route('/', resource)

    client = testing.TestClient(app)

    result = client.simulate_get()
    assert result.text == ': ping\n\n'

    result = client.simulate_post()
    assert result.text == ': ping\n\n'


def test_multiple_events():
    class SomeResource:
        async def on_get(self, req, resp):
            async def emitter():
                yield SSEvent(data=b'ketchup')
                yield SSEvent(data=b'mustard', event='condiment')
                yield SSEvent(data=b'mayo', event='condiment', event_id='1234')
                yield SSEvent(data=b'onions', event='topping', event_id='5678', retry=100)
                yield SSEvent(text='guacamole \u1F951', retry=100, comment='Serve with chips.')
                yield SSEvent(json={'condiment': 'salsa'}, retry=100)

            resp.sse = emitter()

    resource = SomeResource()

    app = App()
    app.add_route('/', resource)

    client = testing.TestClient(app)

    result = client.simulate_get()
    assert result.text == (
        'data: ketchup\n'
        '\n'
        'event: condiment\n'
        'data: mustard\n'
        '\n'
        'event: condiment\n'
        'id: 1234\n'
        'data: mayo\n'
        '\n'
        'event: topping\n'
        'id: 5678\n'
        'retry: 100\n'
        'data: onions\n'
        '\n'
        ': Serve with chips.\n'
        'retry: 100\n'
        'data: guacamole \u1F951\n'
        '\n'
        'retry: 100\n'
        'data: {"condiment": "salsa"}\n'
        '\n'
    )


def test_invalid_event_values():
    with pytest.raises(TypeError):
        SSEvent(data='notbytes')

    with pytest.raises(TypeError):
        SSEvent(data=12345)

    with pytest.raises(TypeError):
        SSEvent(data=0)

    with pytest.raises(TypeError):
        SSEvent(text=b'notbytes')

    with pytest.raises(TypeError):
        SSEvent(text=23455)

    with pytest.raises(TypeError):
        SSEvent(text=0)

    with pytest.raises(TypeError):
        SSEvent(json=set()).serialize()

    with pytest.raises(TypeError):
        SSEvent(event=b'name')

    with pytest.raises(TypeError):
        SSEvent(event=1234)

    with pytest.raises(TypeError):
        SSEvent(event=0)

    with pytest.raises(TypeError):
        SSEvent(event_id=b'idbytes')

    with pytest.raises(TypeError):
        SSEvent(event_id=52085)

    with pytest.raises(TypeError):
        SSEvent(event_id=0)

    with pytest.raises(TypeError):
        SSEvent(retry='5808.25')

    with pytest.raises(TypeError):
        SSEvent(retry='')

    with pytest.raises(TypeError):
        SSEvent(retry=5808.25)

    with pytest.raises(TypeError):
        SSEvent(comment=b'somebytes')

    with pytest.raises(TypeError):
        SSEvent(comment=1234)

    with pytest.raises(TypeError):
        SSEvent(comment=0)


def test_non_iterable():
    class SomeResource:
        async def on_get(self, req, resp):
            async def emitter():
                yield

            resp.sse = emitter

    resource = SomeResource()

    app = App()
    app.add_route('/', resource)

    client = testing.TestClient(app)

    with pytest.raises(TypeError):
        client.simulate_get()


# TODO: Test with uvicorn
# TODO: Test in browser with JavaScript
