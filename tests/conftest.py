import contextlib
import importlib.util
import os
import pathlib

import pytest

import falcon
import falcon.asgi

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


# TODO(vytas): Migrate all cases to use this fixture instead of _util.
@pytest.fixture(scope='session')
def util():
    return _SuiteUtils()


# NOTE(kgriffs): Some modules actually run a wsgiref server, so
# to ensure we reset the detection for the other modules, we just
# run this fixture before each one is tested.
@pytest.fixture(autouse=True, scope='module')
def reset_request_stream_detection():
    falcon.Request._wsgi_input_type_known = False
    falcon.Request._always_wrap_wsgi_input = False


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
