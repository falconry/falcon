import pytest

import falcon
from falcon import testing
from falcon.asgi import App


def test_at_least_one_event_method_required():
    class Foo:
        pass

    app = App()

    with pytest.raises(TypeError):
        app.add_middleware(Foo())


def test_startup_only():
    class Foo:
        async def process_startup(self, scope, event):
            self._called = True

    foo = Foo()

    app = App()
    app.add_middleware(foo)
    client = testing.TestClient(app)

    client.simulate_get()

    assert foo._called


def test_startup_raises():
    class Foo:
        def __init__(self):
            self._shutdown_called = False

        async def process_startup(self, scope, event):
            raise Exception('testing 123')

        async def process_shutdown(self, scope, event):
            self._shutdown_called = True

    class Bar:
        def __init__(self):
            self._startup_called = False
            self._shutdown_called = False

        async def process_startup(self, scope, event):
            self._startup_called = True

        async def process_shutdown(self, scope, event):
            self._shutdown_called = True

    foo = Foo()
    bar = Bar()

    app = App()
    app.add_middleware([foo, bar])
    client = testing.TestClient(app)

    with pytest.raises(RuntimeError) as excinfo:
        client.simulate_get()

    message = str(excinfo.value)

    assert message.startswith('ASGI app returned lifespan.startup.failed.')
    assert 'testing 123' in message

    assert not foo._shutdown_called
    assert not bar._startup_called
    assert not bar._shutdown_called


def test_shutdown_raises():
    class HandlerA:
        def __init__(self):
            self._startup_called = False

        async def process_startup(self, scope, event):
            self._startup_called = True

        async def process_shutdown(self, scope, event):
            raise Exception('testing 321')

    class HandlerB:
        def __init__(self):
            self._startup_called = False
            self._shutdown_called = False

        async def process_startup(self, scope, event):
            self._startup_called = True

        async def process_shutdown(self, scope, event):
            self._shutdown_called = True

    a = HandlerA()
    b1 = HandlerB()
    b2 = HandlerB()

    app = App()
    app.add_middleware(b1)
    app.add_middleware([a, b2])
    client = testing.TestClient(app)

    with pytest.raises(RuntimeError) as excinfo:
        client.simulate_get()

    message = str(excinfo.value)

    assert message.startswith('ASGI app returned lifespan.shutdown.failed.')
    assert 'testing 321' in message

    assert a._startup_called
    assert b1._startup_called
    assert not b1._shutdown_called
    assert b2._startup_called
    assert b2._shutdown_called


def test_shutdown_only():
    class Foo:
        async def process_shutdown(self, scope, event):
            self._called = True

    foo = Foo()

    app = App()
    app.add_middleware(foo)
    client = testing.TestClient(app)

    client.simulate_get()

    assert foo._called


def test_multiple_handlers():
    counter = 0

    class HandlerA:
        async def process_startup(self, scope, event):
            nonlocal counter
            self._called_startup = counter
            counter += 1

    class HandlerB:
        async def process_startup(self, scope, event):
            nonlocal counter
            self._called_startup = counter
            counter += 1

        async def process_shutdown(self, scope, event):
            nonlocal counter
            self._called_shutdown = counter
            counter += 1

    class HandlerC:
        async def process_shutdown(self, scope, event):
            nonlocal counter
            self._called_shutdown = counter
            counter += 1

    class HandlerD:
        async def process_startup(self, scope, event):
            nonlocal counter
            self._called_startup = counter
            counter += 1

    class HandlerE:
        async def process_startup(self, scope, event):
            nonlocal counter
            self._called_startup = counter
            counter += 1

        async def process_shutdown(self, scope, event):
            nonlocal counter
            self._called_shutdown = counter
            counter += 1

        async def process_request(self, req, resp):
            self._called_request = True

    app = App()

    a = HandlerA()
    b = HandlerB()
    c = HandlerC()
    d = HandlerD()
    e = HandlerE()

    app.add_middleware([a, b, c, d, e])

    client = testing.TestClient(app)
    client.simulate_get()

    assert a._called_startup == 0
    assert b._called_startup == 1
    assert d._called_startup == 2
    assert e._called_startup == 3

    assert e._called_shutdown == 4
    assert c._called_shutdown == 5
    assert b._called_shutdown == 6

    assert e._called_request


def test_asgi_conductor_raised_error_skips_shutdown():
    class SomeException(Exception):
        pass

    class Foo:
        def __init__(self):
            self.called_startup = False
            self.called_shutdown = False

        async def process_startup(self, scope, event):
            self.called_startup = True

        async def process_shutdown(self, scope, event):
            self.called_shutdown = True

    foo = Foo()

    app = App()
    app.add_middleware(foo)

    async def t():
        with pytest.raises(SomeException):
            async with testing.ASGIConductor(app):
                raise SomeException()

    falcon.async_to_sync(t)
    assert foo.called_startup
    assert not foo.called_shutdown
