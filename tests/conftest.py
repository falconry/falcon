import importlib.util
import os
import pathlib

import pytest

import falcon
import falcon.asgi

HERE = pathlib.Path(__file__).resolve().parent
EXAMPLES = HERE.parent / 'examples'

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
def create_app(asgi):
    def app_factory(**kwargs):
        app_cls = falcon.asgi.App if asgi else falcon.App
        return app_cls(**kwargs)

    return app_factory


@pytest.fixture()
def example_module():
    def load(filename, prefix='examples'):
        path = EXAMPLES / filename
        module_name = f'{prefix}.{path.stem}'
        spec = importlib.util.spec_from_file_location(module_name, path)
        assert spec is not None, f'could not load module from {path}'
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    return load


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
