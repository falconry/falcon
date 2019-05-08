import pytest

import falcon
import falcon.testing

if not falcon.PY35:
    import falcon.asgi


__all__ = [
    'create_app',
    'create_req',
    'create_resp',
    'to_coroutine',
]


def create_app(asgi, **app_kwargs):
    if asgi:
        if falcon.PY35:
            pytest.skip('ASGI requires Python 3.6+')
        else:
            return falcon.asgi.App(**app_kwargs)

    return falcon.API(**app_kwargs)


def create_req(asgi, options=None, **environ_or_scope_kwargs):
    if asgi:
        if falcon.PY35:
            pytest.skip('ASGI requires Python 3.6+')
        else:
            req = falcon.testing.create_asgi_req(
                options=options,
                **environ_or_scope_kwargs
            )
    else:
        req = falcon.testing.create_req(
            options=options,
            **environ_or_scope_kwargs
        )

    return req


def create_resp(asgi):
    if asgi:
        if falcon.PY35:
            pytest.skip('ASGI requires Python 3.6+')
        else:
            return falcon.asgi.Response()

    return falcon.Response()


def to_coroutine(callable):
    async def wrapper(*args, **kwargs):
        return callable(*args, **kwargs)

    return wrapper
