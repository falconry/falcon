from datetime import datetime

import falcon.asgi
import uvicorn
from falcon import WebSocketDisconnected
from falcon.asgi import Request, WebSocket

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
        print(f'WebSocket connection established on {req.path}')


# Added an authentication middleware. This middleware will check if the request is on a protected route.
class AuthMiddleware:
    protected_routes = []

    def __init__(self, protected_routes: list[str] | None = None):
        if protected_routes is None:
            protected_routes = []

        self.protected_routes = protected_routes

    async def process_request_ws(self, req: Request, ws: WebSocket):
        if req.path not in self.protected_routes:
            return

        token = req.get_header('Authorization')
        if token != 'very secure token':
            await ws.close(1008)
            return

        print(f'Client with token {token} Authenticated')


class HelloWorldResource:
    async def on_get(self, req, resp):
        resp.media = {'hello': 'world'}


class EchoWebSocketResource:
    async def on_websocket(self, req: Request, ws: WebSocket):
        try:
            await ws.accept()
        except WebSocketDisconnected:
            return

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
        try:
            await ws.accept()
        except WebSocketDisconnected:
            return

        while True:
            try:
                query = await ws.receive_text()
                report = REPORTS.get(query, None)
                print(report)

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

# Add the AuthMiddleware to the app, and specify the protected routes
app.add_middleware(AuthMiddleware(['/reports']))

if __name__ == '__main__':
    uvicorn.run(app, host='localhost', port=8000)
