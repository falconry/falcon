from contextlib import contextmanager
import os

import pytest

import falcon
import falcon.asgi
import falcon.testing

try:
    import cython  # noqa

    has_cython = True
except ImportError:
    try:
        import falcon.cyutil.reader  # noqa

        has_cython = True
    except ImportError:
        has_cython = False

__all__ = [
    'create_app',
    'create_req',
    'create_resp',
    'to_coroutine',
]


def create_app(asgi, **app_kwargs):
    App = falcon.asgi.App if asgi else falcon.App
    app = App(**app_kwargs)
    return app


def create_req(asgi, options=None, **environ_or_scope_kwargs):
    if asgi:
        req = falcon.testing.create_asgi_req(options=options, **environ_or_scope_kwargs)

    else:
        req = falcon.testing.create_req(options=options, **environ_or_scope_kwargs)

    return req


def create_resp(asgi):
    if asgi:
        return falcon.asgi.Response()

    return falcon.Response()


def to_coroutine(callable):
    async def wrapper(*args, **kwargs):
        return callable(*args, **kwargs)

    return wrapper


@contextmanager
def disable_asgi_non_coroutine_wrapping():
    should_wrap = 'FALCON_ASGI_WRAP_NON_COROUTINES' in os.environ
    if should_wrap:
        del os.environ['FALCON_ASGI_WRAP_NON_COROUTINES']

    yield

    if should_wrap:
        os.environ['FALCON_ASGI_WRAP_NON_COROUTINES'] = 'Y'


def as_params(*values, prefix=None):
    if not prefix:
        prefix = ''
    # NOTE(caselit): each value must be a tuple/list even when using one single argument
    return [
        pytest.param(*value, id=f'{prefix}_{i}' if prefix else f'{i}')
        for i, value in enumerate(values, 1)
    ]
