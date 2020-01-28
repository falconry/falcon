import pytest

import falcon


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


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    if hasattr(item, 'cls') and item.cls:
        item.cls._item = item

    yield
