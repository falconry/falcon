import os

import pytest

import falcon


@pytest.fixture(params=[True, False])
def asgi(request):
    is_asgi = request.param

    if is_asgi and falcon.PY35:
        pytest.skip('ASGI requires Python 3.6+')

    return is_asgi


@pytest.fixture(autouse=True, scope='session')
def set_env_variables():
    os.environ['FALCON_TESTING_SESSION'] = 'Y'
    os.environ['FALCON_ASGI_WRAP_RESPONDERS'] = 'Y'


# NOTE(kgriffs): Some modules actually run a wsgiref server, so
# to ensure we reset the detection for the other modules, we just
# run this fixture before each one is tested.
@pytest.fixture(autouse=True, scope='module')
def reset_request_stream_detection():
    falcon.Request._wsgi_input_type_known = False
    falcon.Request._always_wrap_wsgi_input = False


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    if item.cls:
        item.cls._item = item

    yield
