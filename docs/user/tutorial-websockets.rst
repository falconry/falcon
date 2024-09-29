.. _tutorial-ws:

Tutorial (WebSockets)
=====================

In this tutorial, we're going to build a WebSocket server using Falcon.
We'll start with a simple server that echoes back any message it receives.

We'll then add more functionality to the server, such as sending JSON data and
logging messages.

.. note::
   This tutorial covers the asynchronous flavor of Falcon using
   the `ASGI <https://asgi.readthedocs.io/en/latest/>`__ protocol.

   A Falcon WebSocket server builds upon the
   `ASGI WebSocket specification <https://asgi.readthedocs.io/en/latest/specs/www.html#websocket>`__.
   Therefore it's not supported in a Falcon WSGI application.

First Steps
___________

We'll start with a clean working directory and create a new virtual environment
using the :mod:`venv` module:

.. code-block:: bash

   $ mkdir ws_tutorial
   $ cd ws_tutorial
   $ python3 -m venv .venv
   $ source .venv/bin/activate

Create the following directory structure::

  ws_tutorial
  ├── .venv
  └── ws_tutorial
      ├── __init__.py
      └── app.py


And next we'll :ref:`install Falcon <install>` and Uvicorn in our freshly
created virtual environment:

.. code-block:: bash

   $ pip install falcon uvicorn

Now, let's create a simple Falcon application to ensure our project is working
as expected.

.. code-block:: python

    import falcon.asgi
    import uvicorn

    app = falcon.asgi.App()

    class HelloWorldResource:
        async def on_get(self, req, resp):
            resp.media = {'hello': 'world'}

    app.add_route('/hello', HelloWorldResource())

    if __name__ == '__main__':
        uvicorn.run(app, host='localhost', port=8000)

Now we can test the application with ``httpie`` (installable with
``pip install httpie``) by running the following command::

   $ http localhost:8000/hello

    HTTP/1.1 200 OK
    content-length: 18
    content-type: application/json
    date: Sat, 13 Jul 2024 09:13:24 GMT
    server: uvicorn

    {
        "hello": "world"
    }

Awesome, it works! Now let's move on to building our WebSocket server.

WebSockets Server
_________________

We will update our server to include a websocket route that will echo back any
message it receives. Later we'll update the server with more logic, but for now,
let's keep it simple.

.. code-block:: python

    import falcon.asgi
    from falcon import WebSocketDisconnected
    from falcon.asgi import Request, WebSocket
    import uvicorn

    app = falcon.asgi.App()


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
                    await ws.send_text(f"Received the following text: {message}")
                except WebSocketDisconnected:
                    return


    app.add_route('/hello', HelloWorldResource())
    app.add_route('/echo', EchoWebSocketResource())

    if __name__ == '__main__':
        uvicorn.run(app, host='localhost', port=8000)

We'll also need to install a websockets library. There are multiple ways to do
this::

    $ pip install websockets
    or
    $ pip install uvicorn[standard]
    or
    $ wsproto

To test the new WebSocket route, we can use the
`websocat <https://github.com/vi/websocat>`__ tool::

    $ websocat ws://localhost:8000/echo
    $ hello
    Received the following text: hello

Cool! We have a working WebSocket server. Now let's add some more functionality
to our server.

To make this easier, we'll create a simple client that will send messages to our
server.

Simple Client
_____________

Create a new file called ``client.py`` in the same directory as ``app.py``.
The client will ask for your input and send it to the server.:

.. literalinclude:: ../../examples/ws_tutorial/ws_tutorial/client.py

Run this client in a separate terminal:

.. code-block:: bash

    $ python client.py
    Enter a message: Hi
    Received the following text: Hi

This will simplify testing our server.

Now let's add some more functionality to our server.

We've been working with text input/output - let's try sending sending some JSON
data.

.. code-block:: python

    from datetime import datetime

    import falcon.asgi
    from falcon import WebSocketDisconnected
    from falcon.asgi import Request, WebSocket
    import uvicorn

    app = falcon.asgi.App()


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
                    await ws.send_media({'message': message, 'date': datetime.now().isoformat()})
                except WebSocketDisconnected:
                    return


    app.add_route('/hello', HelloWorldResource())
    app.add_route('/echo', EchoWebSocketResource())

    if __name__ == '__main__':
        uvicorn.run(app, host='localhost', port=8000)

.. code-block:: bash

    $ python client.py
    $ Enter a message: Hi
      {"message": "Hi", "date": "2024-07-13T12:11:51.758923"}

.. note::
    By default, `send_media() <https://falcon.readthedocs.io/en/latest/api/websocket.html#falcon.asgi.WebSocket.send_media>`__ and `receive_media() <https://falcon.readthedocs.io/en/latest/api/websocket.html#falcon.asgi.WebSocket.receive_media>`__ will serialize to (and deserialize from) JSON for a TEXT payload, and to/from MessagePack for a BINARY payload (see also: `Built-in Media Handlers <https://falcon.readthedocs.io/en/latest/api/websocket.html#bimh>`__).

Lets try to query for data from the server. We'll create a new resource that
will return a report based on the query.

Server side:

.. code-block:: python

    from datetime import datetime

    import falcon.asgi
    from falcon import WebSocketDisconnected
    from falcon.asgi import Request, WebSocket
    import uvicorn

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
                    await ws.send_media({'message': message, 'date': datetime.now().isoformat()})
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

                    await ws.send_media({'report': report["title"]})
                except WebSocketDisconnected:
                    return


    app.add_route('/hello', HelloWorldResource())
    app.add_route('/echo', EchoWebSocketResource())
    app.add_route('/reports', ReportsResource())


    if __name__ == '__main__':
        uvicorn.run(app, host='localhost', port=8000)

We'll also create new client app (`reports_client.py`), that will connect to
the reports endpoint. :

.. code-block:: python

    import asyncio
    import websockets


    async def send_message():
        uri = "ws://localhost:8000/reports"
        async with websockets.connect(uri) as websocket:
            while True:
                message = input("Name of the log: ")
                await websocket.send(message)
                response = await websocket.recv()
                print(response)


    if __name__ == "__main__":
        asyncio.run(send_message())

We've added a new resource that will return a report based on the query.
The client will send a query to the server, and the server will respond with the
report.
If it can't find the report, it will respond with an error message.

This is a simple example, but you can easily extend it to include more complex
logic like fetching data from a database.

Middleware
__________

Falcon supports middleware, which can be used to add functionality to the application.
For example, we can add a middleware that prints when a connection is established.

.. code-block:: python

    from datetime import datetime

    import falcon.asgi
    from falcon import WebSocketDisconnected
    from falcon.asgi import Request, WebSocket
    import uvicorn

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
                    await ws.send_media({'message': message, 'date': datetime.now().isoformat()})
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

                    await ws.send_media({'report': report["title"]})
                except WebSocketDisconnected:
                    return


    app.add_route('/hello', HelloWorldResource())
    app.add_route('/echo', EchoWebSocketResource())
    app.add_route('/reports', ReportsResource())

    app.add_middleware(LoggerMiddleware())


    if __name__ == '__main__':
        uvicorn.run(app, host='localhost', port=8000)

Now, when you run the server, you should see a message in the console when a
WebSocket connection is established.


Authentication
______________

Adding authentication can be done with the help of middleware as well.
Authentication can be done a few ways. In this example we'll use the
**First message** method, as described on the
`websockets documentation <https://websockets.readthedocs.io/en/stable/topics/authentication.html>`__.

There are some
`considerations <https://websockets.readthedocs.io/en/stable/topics/authentication.html>`__
to take into account when implementing authentication in a WebSocket server.

Updated server code:

.. literalinclude:: ../../examples/ws_tutorial/ws_tutorial/app.py

Updated client code for the reports client:

.. literalinclude:: ../../examples/ws_tutorial/ws_tutorial/reports_client.py

Things we've changed:

- Added a new middleware class `AuthMiddleware` that will check the token on the first message.
- Opening a WebSocket connection is now handled by the middleware.
- The client now sends a token as the first message, if required for that route.
- Falcon was configured to serve a simple HTML page to use the echo WebSocket client for a browser.

If you try to query the reports endpoint now, everything works as expected on an
authenticated route.
But as soon as you remove/modify the token, the connection will be closed
(after sending the first query - a
`downside <https://websockets.readthedocs.io/en/stable/topics/authentication.html#sending-credentials>`__
of first-message authentication).

.. code-block:: bash

    $ python reports_client.py
    [...]
    websockets.exceptions.ConnectionClosedError: received 1008 (policy violation); then sent 1008 (policy violation)

.. note::

    This is a simple example of how to add authentication to a WebSocket server.
    In a real-world application, you would want to use a more secure method of
    authentication, such as JWT tokens.

What Now
________

This tutorial is just the beginning. You can extend the server with more
complex logic. For example, you could add a database to store/retrieve the
reports, or add more routes to the server.

For more information on websockets in Falcon, check out the
`WebSocket API <https://falcon.readthedocs.io/en/latest/api/websocket.html>`__.
