import collections
import os
import sys

import pytest

if os.environ.get('FALCON_TESTING_MOCK_PY35'):
    version_info = collections.namedtuple('version_info', ('major', 'minor', 'micro'))
    # NOTE(vytas): Ignore type as it is not trivial to fake the built-in one.
    sys.version_info = version_info(3, 5, 0)  # type: ignore

import falcon

_FALCON_TEST_ENV = (
    ('FALCON_ASGI_WRAP_NON_COROUTINES', 'Y'),
    ('FALCON_TESTING_SESSION', 'Y'),
    # NOTE: PYTHONASYNCIODEBUG is optional (set in tox.ini).
    # ('PYTHONASYNCIODEBUG', '1'),
)


@pytest.fixture(params=[True, False], ids=['asgi', 'wsgi'])
def asgi(request):
    is_asgi = request.param

    if is_asgi and not falcon.ASGI_SUPPORTED:
        pytest.skip('ASGI requires Python 3.6+')

    return is_asgi


# NOTE(kgriffs): Some modules actually run a wsgiref server, so
# to ensure we reset the detection for the other modules, we just
# run this fixture before each one is tested.
@pytest.fixture(autouse=True, scope='module')
def reset_request_stream_detection():
    falcon.Request._wsgi_input_type_known = False
    falcon.Request._always_wrap_wsgi_input = False


def pytest_configure(config):
    plugin = config.pluginmanager.getplugin('mypy')
    if plugin:
        plugin.mypy_argv.append('--ignore-missing-imports')


def pytest_sessionstart(session):
    for key, value in _FALCON_TEST_ENV:
        os.environ.setdefault(key, value)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    if hasattr(item, 'cls') and item.cls:
        item.cls._item = item

    yield
