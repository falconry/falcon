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
