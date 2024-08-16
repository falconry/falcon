from copy import copy

import pytest
from ws_tutorial.app import app
from ws_tutorial.app import AuthMiddleware

from falcon import errors
from falcon import testing


@pytest.mark.asyncio
async def test_websocket_echo():
    async with testing.ASGIConductor(app) as conn:
        async with conn.simulate_ws('/echo') as ws:
            await ws.send_text('Hello, World!')
            response = await ws.receive_json()

            assert response['message'] == 'Hello, World!'


@pytest.mark.asyncio
async def test_resetting_auth_middleware():
    local_app = copy(app)
    local_app._middleware = None
    local_app.add_middleware(AuthMiddleware())

    async with testing.ASGIConductor(local_app) as conn:
        async with conn.simulate_ws('/reports') as ws:
            with pytest.raises(errors.WebSocketDisconnected):
                await ws.send_text('report1')
                await ws.receive_json()


@pytest.mark.asyncio
async def test_websocket_reports():
    async with testing.ASGIConductor(app) as conn:
        async with conn.simulate_ws('/reports') as ws:
            await ws.send_text('very secure token')
            await ws.send_text('report1')
            response = await ws.receive_json()

            assert response['report'] == 'Report 1'


@pytest.mark.asyncio
async def test_websocket_report_not_found():
    async with testing.ASGIConductor(app) as conn:
        async with conn.simulate_ws('/reports') as ws:
            await ws.send_text('very secure token')
            await ws.send_text('report10')
            response = await ws.receive_json()

            assert response['error'] == 'report not found'


@pytest.mark.asyncio
async def test_websocket_not_authenticated():
    async with testing.ASGIConductor(app) as conn:
        async with conn.simulate_ws('/reports') as ws:
            with pytest.raises(errors.WebSocketDisconnected):
                await ws.send_text('report1')
                await ws.receive_json()
