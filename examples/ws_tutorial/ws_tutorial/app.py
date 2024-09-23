from datetime import datetime
import logging
import pathlib

import uvicorn

from falcon import WebSocketDisconnected
import falcon.asgi
from falcon.asgi import Request
from falcon.asgi import WebSocket

logger = logging.getLogger('ws-logger')
logger.setLevel('INFO')
logger.addHandler(logging.StreamHandler())


REPORTS = {
    'report1': {
        'title': 'Report 1',
        'content': 'This is the content of report 1',
    },
    'report2': {
        'title': 'Report 2',
        'content': 'This is the content of report 2',
    },
    'report3': {
        'title': 'Report 3',
        'content': 'This is the content of report 3',
    },
    'report4': {
        'title': 'Report 4',
        'content': 'This is the content of report 4',
    },
}

app = falcon.asgi.App()


class LoggerMiddleware:
    async def process_request_ws(self, req: Request, ws: WebSocket):
        # This will be called for the HTTP request that initiates the
        #   WebSocket handshake before routing.
        pass

    async def process_resource_ws(self, req: Request, ws: WebSocket, resource, params):
        # This will be called for the HTTP request that initiates the
        #   WebSocket handshake after routing (if a route matches the
        #   request).
        logger.info('WebSocket connection established on %r', req.path)


class AuthMiddleware:
    def __init__(self, protected_routes: list[str] | None = None):
        if protected_routes is None:
            protected_routes = []

        self.protected_routes = protected_routes

    async def process_request_ws(self, req: Request, ws: WebSocket):
        # Opening a connection so we can receive the token
        await ws.accept()

        # Check if the route is protected
        if req.path not in self.protected_routes:
            return

        token = await ws.receive_text()

        if token != 'very secure token':
            await ws.close(1008)
            return

        # Never log tokens in production
        logger.info('Client with token %r Authenticated', token)


class HelloWorldResource:
    async def on_get(self, req, resp):
        resp.media = {'hello': 'world'}


class EchoWebSocketResource:
    async def on_websocket(self, req: Request, ws: WebSocket):
        while True:
            try:
                message = await ws.receive_text()
                await ws.send_media(
                    {'message': message, 'date': datetime.now().isoformat()}
                )
            except WebSocketDisconnected:
                return


class ReportsResource:
    async def on_websocket(self, req: Request, ws: WebSocket):
        while True:
            try:
                query = await ws.receive_text()
                report = REPORTS.get(query, None)
                logger.info('selected report: %s', report)

                if report is None:
                    await ws.send_media({'error': 'report not found'})
                    continue

                await ws.send_media({'report': report['title']})
            except WebSocketDisconnected:
                return


app.add_route('/hello', HelloWorldResource())
app.add_route('/echo', EchoWebSocketResource())
app.add_route('/reports', ReportsResource())

app.add_middleware(LoggerMiddleware())
app.add_middleware(AuthMiddleware(['/reports']))

# usually a web server, like Nginx or Caddy, should serve static assets, but
# for the purpose of this example we use falcon.
static_path = pathlib.Path(__file__).parent / 'static'
app.add_static_route('/', static_path, fallback_filename='index.html')

if __name__ == '__main__':
    uvicorn.run(app, host='localhost', port=8000)  # pragma: no cover
