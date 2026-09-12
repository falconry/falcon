import inspect

from falcon.asgi import _asgi_helpers


class IntricateApp:
    def unorthodox_call(self, scope, receive, send):
        return self._call_factory(scope, receive, send)

    async def _call_factory(self, scope, receive, send):
        await send('Hello!')
        await send('Bye.')

    __call__ = _asgi_helpers._wrap_asgi_coroutine_func(unorthodox_call)


async def test_intricate_app():
    async def receive():
        pass

    async def send(msg):
        messages.append(msg)

    app = IntricateApp()
    messages = []

    assert not inspect.iscoroutinefunction(app.unorthodox_call)
    assert inspect.iscoroutinefunction(app.__call__)

    await app({}, receive, send)

    assert messages == ['Hello!', 'Bye.']
