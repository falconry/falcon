import sys
import time

import pytest

import falcon
from falcon import testing
import falcon.asgi
from falcon.util import is_python_func

try:
    import pyximport

    pyximport.install()
except ImportError:
    pyximport = None

# NOTE(kgriffs): We do this here rather than inside the try block above,
#   so that we don't mask errors importing _cythonized itself.
if pyximport:
    from . import _cythonized  # type: ignore

    _CYTHON_FUNC_TEST_TYPES = [
        _cythonized.nop_method,
        _cythonized.nop_method_async,
        _cythonized.NOPClass.nop_method,
        _cythonized.NOPClass.nop_method_async,
        _cythonized.NOPClass().nop_method,
        _cythonized.NOPClass().nop_method_async,
    ]
else:
    _CYTHON_FUNC_TEST_TYPES = []

from _util import disable_asgi_non_coroutine_wrapping  # NOQA


# NOTE(vytas): Cython 3.0+ now correctly marks cythonized coroutines as such,
#   however, the relevant protocol is only available in Python 3.10+.
#   See also: https://github.com/cython/cython/pull/3427
CYTHON_COROUTINE_HINT = sys.version_info >= (3, 10)


@pytest.fixture
def client():
    return testing.TestClient(falcon.asgi.App())


def nop_method(self):
    pass


async def nop_method_async(self):
    pass


class NOPClass:
    def nop_method(self):
        pass

    async def nop_method_async(self):
        pass


@pytest.mark.skipif(not pyximport, reason='Cython not installed')
@pytest.mark.parametrize('func', _CYTHON_FUNC_TEST_TYPES)
def test_is_cython_func(func):
    assert not is_python_func(func)


@pytest.mark.parametrize(
    'func',
    [
        nop_method,
        nop_method_async,
        NOPClass.nop_method,
        NOPClass.nop_method_async,
        NOPClass().nop_method,
        NOPClass().nop_method_async,
    ],
)
def test_not_cython_func(func):
    assert is_python_func(func)


@pytest.mark.skipif(not pyximport, reason='Cython not installed')
def test_jsonchema_validator(client):
    with disable_asgi_non_coroutine_wrapping():
        if CYTHON_COROUTINE_HINT:
            client.app.add_route('/', _cythonized.TestResourceWithValidationNoHint())
        else:
            with pytest.raises(TypeError):
                client.app.add_route(
                    '/wowsuchfail', _cythonized.TestResourceWithValidationNoHint()
                )

            client.app.add_route('/', _cythonized.TestResourceWithValidation())

    client.simulate_get()


@pytest.mark.skipif(not pyximport, reason='Cython not installed')
def test_scheduled_jobs(client):
    resource = _cythonized.TestResourceWithScheduledJobs()
    client.app.add_route('/', resource)

    client.simulate_get()
    time.sleep(0.5)
    assert resource.counter['backround:on_get:async'] == 2
    assert resource.counter['backround:on_get:sync'] == 40


@pytest.mark.skipif(not pyximport, reason='Cython not installed')
def test_scheduled_jobs_type_error(client):
    client.app.add_route(
        '/wowsuchfail', _cythonized.TestResourceWithScheduledJobsAsyncRequired()
    )

    # NOTE(kgriffs): Normally an unhandled exception is translated to a
    #   500 response, but since jobs aren't supposed to be scheduled until
    #   we are done sending the response, we treat this as a special case
    #   and allow the error to propagate out of the server. Masking this kind
    #   of error would make it especially hard to debug in any case (it will
    #   be hard enough as it is for the app developer).
    with pytest.raises(TypeError):
        client.simulate_get('/wowsuchfail')


@pytest.mark.skipif(not pyximport, reason='Cython not installed')
def test_hooks(client):
    with disable_asgi_non_coroutine_wrapping():
        if CYTHON_COROUTINE_HINT:
            client.app.add_route('/', _cythonized.TestResourceWithHooksNoHint())
        else:
            with pytest.raises(TypeError):
                client.app.add_route('/', _cythonized.TestResourceWithHooksNoHint())

            client.app.add_route('/', _cythonized.TestResourceWithHooks())

    result = client.simulate_get()
    assert result.headers['x-answer'] == '42'
    assert result.json == {'answer': 42}
