import contextlib
import functools
import http.client
import importlib.util
import inspect
import json
import os
import pathlib
import urllib.parse

import pytest

import falcon
import falcon.asgi
import falcon.testing
import falcon.util

try:
    import cython  # noqa

    has_cython = True
except ImportError:
    try:
        import falcon.cyutil.reader  # noqa

        has_cython = True
    except ImportError:
        has_cython = False

HERE = pathlib.Path(__file__).resolve().parent
FALCON_ROOT = HERE.parent

_FALCON_TEST_ENV = (
    ('FALCON_ASGI_WRAP_NON_COROUTINES', 'Y'),
    ('FALCON_TESTING_SESSION', 'Y'),
    # NOTE: PYTHONASYNCIODEBUG is optional (set in tox.ini).
    # ('PYTHONASYNCIODEBUG', '1'),
)


@pytest.fixture(params=[True, False], ids=['asgi', 'wsgi'])
def asgi(request):
    return request.param


@pytest.fixture()
def app_kind(asgi):
    # NOTE(vytas): Same as the above asgi fixture but as string.
    return 'asgi' if asgi else 'wsgi'


class _SuiteUtils:
    """Assorted utilities that previously resided in the _util.py module."""

    HAS_CYTHON = has_cython

    @staticmethod
    def create_app(asgi, **app_kwargs):
        App = falcon.asgi.App if asgi else falcon.App
        app = App(**app_kwargs)
        return app

    @staticmethod
    def create_req(asgi, options=None, **environ_or_scope_kwargs):
        if asgi:
            return falcon.testing.create_asgi_req(
                options=options, **environ_or_scope_kwargs
            )

        return falcon.testing.create_req(options=options, **environ_or_scope_kwargs)

    @staticmethod
    def create_resp(asgi):
        if asgi:
            return falcon.asgi.Response()

        return falcon.Response()

    @staticmethod
    def to_coroutine(callable):
        async def wrapper(*args, **kwargs):
            return callable(*args, **kwargs)

        return wrapper

    @staticmethod
    @contextlib.contextmanager
    def disable_asgi_non_coroutine_wrapping():
        should_wrap = 'FALCON_ASGI_WRAP_NON_COROUTINES' in os.environ
        if should_wrap:
            del os.environ['FALCON_ASGI_WRAP_NON_COROUTINES']

        yield

        if should_wrap:
            os.environ['FALCON_ASGI_WRAP_NON_COROUTINES'] = 'Y'

    @staticmethod
    def load_module(filename, parent_dir=None, suffix=None):
        if parent_dir:
            filename = pathlib.Path(parent_dir) / filename
        else:
            filename = pathlib.Path(filename)
        path = FALCON_ROOT / filename
        if suffix is not None:
            path = path.with_name(f'{path.stem}_{suffix}.py')
        prefix = '.'.join(filename.parent.parts)
        module_name = f'{prefix}.{path.stem}'

        spec = importlib.util.spec_from_file_location(module_name, path)
        assert spec is not None, f'could not load module from {path}'
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


@pytest.fixture(scope='session')
def util():
    return _SuiteUtils()


class _RequestsLite:
    """Poor man's requests using nothing but the stdlib+Falcon."""

    DEFAULT_TIMEOUT = 15.0

    class Response:
        def __init__(self, resp):
            self.content = resp.read()
            self.headers = falcon.util.CaseInsensitiveDict(resp.getheaders())
            self.status_code = resp.status

        @property
        def text(self):
            return self.content.decode()

        def json(self):
            content_type, _ = falcon.parse_header(
                self.headers.get('Content-Type') or ''
            )
            if content_type != falcon.MEDIA_JSON:
                raise ValueError(f'Content-Type is not {falcon.MEDIA_JSON}')
            return json.loads(self.content)

    def __init__(self):
        self.delete = functools.partial(self.request, 'DELETE')
        self.get = functools.partial(self.request, 'GET')
        self.head = functools.partial(self.request, 'HEAD')
        self.patch = functools.partial(self.request, 'PATCH')
        self.post = functools.partial(self.request, 'POST')
        self.put = functools.partial(self.request, 'PUT')

    def request(self, method, url, data=None, headers=None, timeout=None):
        parsed = urllib.parse.urlparse(url)
        uri = urllib.parse.urlunparse(('', '', parsed.path, '', parsed.query, ''))
        headers = headers or {}
        timeout = timeout or self.DEFAULT_TIMEOUT

        conn = http.client.HTTPConnection(parsed.netloc)
        conn.request(method, uri, body=data, headers=headers)
        return self.Response(conn.getresponse())


@pytest.fixture(scope='session')
def requests_lite():
    return _RequestsLite()


def pytest_configure(config):
    if config.pluginmanager.getplugin('asyncio'):
        config.option.asyncio_mode = 'strict'

    mypy_plugin = config.pluginmanager.getplugin('mypy')
    if mypy_plugin:
        mypy_plugin.mypy_argv.append('--ignore-missing-imports')


def pytest_sessionstart(session):
    for key, value in _FALCON_TEST_ENV:
        os.environ.setdefault(key, value)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    if hasattr(item, 'cls') and item.cls:
        item.cls._item = item

    yield


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    # NOTE(vytas): We automatically wrap all coroutine functions with
    #   falcon.runs_sync instead of the fragile pytest-asyncio package.
    if isinstance(item, pytest.Function) and inspect.iscoroutinefunction(item.obj):
        item.obj = falcon.runs_sync(item.obj)

    yield
