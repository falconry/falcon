# misc test for 100% coverage

from unittest.mock import MagicMock

import pytest

from falcon.asgi import App
from falcon.http_error import HTTPError
from falcon.http_status import HTTPStatus


@pytest.mark.asyncio
async def test_http_status_not_impl():
    app = App()
    with pytest.raises(NotImplementedError):
        await app._http_status_handler(MagicMock(), None, HTTPStatus(200), {}, None)


@pytest.mark.asyncio
async def test_http_error_not_impl():
    app = App()
    with pytest.raises(NotImplementedError):
        await app._http_error_handler(MagicMock(), None, HTTPError(400), {}, None)


@pytest.mark.asyncio
async def test_python_error_not_impl():
    app = App()
    with pytest.raises(NotImplementedError):
        await app._python_error_handler(
            MagicMock(), None, ValueError('error'), {}, None
        )
