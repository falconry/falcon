import pytest

from falcon import testing
from falcon.asgi import Request


def test_missing_server_in_scope():
    req = testing.create_asgi_req(include_server=False, http_version='1.0')
    assert req.host == 'localhost'
    assert req.port == 80


def test_client_none_in_scope():
    # Regression test for #2583

    async def recv():
        pass

    scope = testing.create_scope()
    scope['client'] = None
    req = Request(scope, recv)
    assert req.remote_addr == '127.0.0.1'


def test_log_error_not_supported():
    req = testing.create_asgi_req()
    with pytest.raises(NotImplementedError):
        req.log_error('Boink')


def test_env_not_supported():
    req = testing.create_asgi_req()
    with pytest.raises(AttributeError):
        req.env
