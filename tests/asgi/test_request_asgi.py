import pytest

from falcon import testing


def test_missing_server_in_scope():
    req = testing.create_asgi_req(include_server=False, http_version='1.0')
    assert req.host == 'localhost'
    assert req.port == 80


def test_log_error_not_supported():
    req = testing.create_asgi_req()
    with pytest.raises(NotImplementedError):
        req.log_error('Boink')
