.. _ws:

WebSocket (ASGI Only)
=====================

Falcon builds upon the
`ASGI WebSocket Specification <https://asgi.readthedocs.io/en/latest/specs/www.html#websocket>`_
to provide a simple, no-nonsense WebSocket server implementation.

With support for both `WebSocket <https://tools.ietf.org/html/rfc6455>`_ and
`Server-Sent Events <https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events>`_
(SSE), Falcon facilitates real-time, event-oriented communication between an
ASGI application and a web browser, mobile app, or other client application.

.. note::

    See also :attr:`falcon.asgi.Response.sse` to learn more about Falcon's
    Server-Sent Event (SSE) support.

Usage
-----

With Falcon you can easily add WebSocket support to any route in your ASGI
app, simply by implementing an ``on_websocket()`` responder in the
resource class for that route. As with regular
HTTP requests, WebSocket flows can be augmented with middleware
components and media handlers.

When a WebSocket handshake arrives (via a standard HTTP request), Falcon will
first route it as usual to a specific resource class instance. Along the way,
the following middleware methods will be invoked, if implemented on any
middleware objects configured for the app:

.. code:: python

    from typing import Any
    from falcon.asgi import Request, WebSocket


    class SomeMiddleware:
        async def process_request_ws(self, req: Request, ws: WebSocket) -> None:
            """Process a WebSocket handshake request before routing it.

            Note:
                Because Falcon routes each request based on req.path, a
                request can be effectively re-routed by setting that
                attribute to a new value from within process_request().

            Args:
                req: Request object that will eventually be
                    passed into an on_websocket() responder method.
                ws: The WebSocket object that will be passed into
                    on_websocket() after routing.
            """

        async def process_resource_ws(
            self,
            req: Request,
            ws: WebSocket,
            resource: object,
            params: dict[str, Any],
        ) -> None:
            """Process a WebSocket handshake request after routing.

            Note:
                This method is only called when the request matches
                a route to a resource.

            Args:
                req: Request object that will be passed to the
                    routed responder.
                ws: WebSocket object that will be passed to the
                    routed responder.
                resource: Resource object to which the request was
                    routed.
                params: A dict-like object representing any additional
                    params derived from the route's URI template fields,
                    that will be passed to the resource's responder
                    method as keyword arguments.
            """

If a route is found for the requested path, the framework will then check for
a responder coroutine named ``on_websocket()`` on the target resource. If the
responder is found, it is invoked in a similar manner to a regular
``on_get()`` responder, except that a :class:`falcon.asgi.WebSocket` object
is passed in, instead of an object of type :class:`falcon.asgi.Response`.

For example, given a route that includes an ``account_id`` path parameter, the
framework would expect an ``on_websocket()`` responder similar to this:

.. code:: python

    async def on_websocket(self, req: Request, ws: WebSocket, account_id: str):
        pass

If no route matches the path requested in the WebSocket handshake, control then
passes to a default responder that simply raises an instance of
:class:`~.HTTPRouteNotFound`. By default, this error will be rendered as a 403
response with a 3404 close code. This behavior can be modified by adding a
custom error handler (see also: :meth:`~falcon.asgi.App.add_error_handler`).

Similarly, if a route exists but the target resource does not implement an
``on_websocket()`` responder, the framework invokes a default responder that
raises an instance of :class:`~.HTTPMethodNotAllowed`. This class will be
rendered by default as a 403 response with a 3405 close code.

.. _ws_lost_connection:

Lost Connections
----------------

When the app attempts to receive a message from the client, the ASGI server
emits a ``disconnect`` event if the connection has been lost for any
reason. Falcon surfaces this event by raising an instance of
:class:`~.WebSocketDisconnected` to the caller.

On the other hand, the ASGI spec previously required the ASGI server to
silently consume messages sent by the app after the connection has been lost
(i.e.,  it should not be considered an error). Therefore, an endpoint that
primarily streams outbound events to the client could continue consuming
resources unnecessarily for some time after the connection is lost.
This aspect has been rectified in the ASGI HTTP spec version ``2.4``,
and calling ``send()``  on a closed connection should now raise an
error. Unfortunately, not all ASGI servers have adopted this new behavior
uniformly yet.

As a workaround, Falcon implements a small incoming message queue that is used
to detect a lost connection and then raise an instance of
:class:`~.WebSocketDisconnected` to the caller the next time it attempts to
send a message.
If your ASGI server of choice adheres to the spec version ``2.4``, this receive
queue can be safely disabled for a slight performance boost by setting
:attr:`~falcon.asgi.WebSocketOptions.max_receive_queue` to ``0`` via
:attr:`~falcon.asgi.App.ws_options`.
(We may revise this setting, and disable the queue by default in the future if
our testing indicates that all major ASGI servers have caught up with the
spec.)

Furthermore, even on non-compliant or older ASGI servers, this workaround is
only necessary when the app itself does not consume messages from the client
often enough to quickly detect when the connection is lost.
Otherwise, Falcon's receive queue can also be disabled as described above.

.. _ws_error_handling:

Error Handling
--------------

Falcon handles errors raised by an ``on_websocket()`` responder in a
similar way to errors raised by other responders, with the following caveats.

First, when calling a custom error handler, the framework will pass ``None``
for the `resp` argument, while the :class:`~falcon.asgi.WebSocket` object
representing the current connection will be passed as a keyword argument
named `ws`::

    async def my_error_handler(req, resp, ex, params, ws=None):
        # When invoked as a result of an error being raised by an
        #   on_websocket() responder, resp will be None and
        #   ws will be the same falcon.asgi.WebSocket object that
        #   was passed into the responder.
        pass

Second, it's important to note that if no route matches the path in the
WebSocket handshake request, or the matched resource does not implement an
``on_websocket()`` responder, the default HTTP error responders will be invoked,
resulting in the request being denied with an ``HTTP 403`` response and a
WebSocket close code of either ``3404`` (Not Found) or ``3405`` (Method Not
Allowed). Generally speaking, if either a default responder or
``on_websocket()`` raises an instance of :class:`~falcon.HTTPError`, the default
error handler will close the :ref:`WebSocket <ws>` connection with a framework
close code derived by adding ``3000`` to the HTTP status code (e.g., ``3404``).

Finally, in the case of a generic unhandled exception, a default error handler
is invoked that will do its best to clean up the connection, closing it with the
standard WebSocket close code ``1011`` (Internal Error). If your ASGI server
does not support this code, the framework will use code ``3011`` instead; or you
can customize it via the :attr:`~falcon.asgi.WebSocketOptions.error_close_code`
property of :attr:`~.ws_options`.

As with any responder, the default error handlers for the app may be
overridden via :meth:`~falcon.asgi.App.add_error_handler`.

.. _ws_media_handlers:

Media Handlers
--------------

By default, :meth:`~.falcon.asgi.WebSocket.send_media` and
:meth:`~.falcon.asgi.WebSocket.receive_media` will serialize to (and
deserialize from) JSON for a TEXT payload, and to/from MessagePack
for a BINARY payload (see also: :ref:`bimh`).

.. note::

    In order to use the default MessagePack handler, the extra ``msgpack``
    package (version 0.5.2 or higher) must be installed in addition
    to ``falcon`` from PyPI:

    .. code::

        $ pip install msgpack

WebSocket media handling can be customized by using
:attr:`falcon.asgi.App.ws_options` to specify an alternative handler for
one or both payload types, as in the following example.

.. code:: python

    # Let's say we want to use a faster JSON library. You could also use this
    #   pattern to add serialization support for custom types that aren't
    #   normally JSON-serializable out of the box.
    class RapidJSONHandler(falcon.media.TextBaseHandlerWS):
        def serialize(self, media: object) -> str:
            return rapidjson.dumps(media, ensure_ascii=False)

        # The raw TEXT payload will be passed as a Unicode string
        def deserialize(self, payload: str) -> object:
            return rapidjson.loads(payload)


    # And/or for binary mode we want to use CBOR:
    class CBORHandler(media.BinaryBaseHandlerWS):
        def serialize(self, media: object) -> bytes:
            return cbor2.dumps(media)

        # The raw BINARY payload will be passed as a byte string
        def deserialize(self, payload: bytes) -> object:
            return cbor2.loads(payload)

    app = falcon.asgi.App()

    # Expected to (de)serialize from/to str
    json_handler = RapidJSONHandler()
    app.ws_options.media_handlers[falcon.WebSocketPayloadType.TEXT] = json_handler

    # Expected to (de)serialize from/to bytes, bytearray, or memoryview
    cbor_handler = ProtocolBuffersHandler()
    app.ws_options.media_handlers[falcon.WebSocketPayloadType.BINARY] = cbor_handler

The ``falcon`` module defines the following :class:`~enum.Enum` values for
specifying the WebSocket payload type:

.. code:: python

    falcon.WebSocketPayloadType.TEXT
    falcon.WebSocketPayloadType.BINARY

Extended Example
----------------

Here is a more comprehensive (albeit rather contrived) example that illustrates
some of the different ways an application can interact with a WebSocket
connection. This example also introduces some common WebSocket errors raised
by the framework.

.. code:: python

    import falcon.asgi
    import falcon.media


    class SomeResource:

        # Get a paginated list of events via a regular HTTP request.
        #
        #   For small-scale, all-in-one apps, it may make sense to support
        #   both a regular HTTP interface and one based on WebSocket
        #   side-by-side in the same deployment. However, these two
        #   interaction models have very different performance characteristics,
        #   and so larger scale-out deployments may wish to specifically
        #   designate instance groups for one type of traffic vs. the
        #   other (although the actual applications may still be capable
        #   of handling both modes).
        #
        async def on_get(self, req: Request, account_id: str):
            pass

        # Push event stream to client. Note that the framework will pass
        #   parameters defined in the URI template as with HTTP method
        #   responders.
        async def on_websocket(self, req: Request, ws: WebSocket, account_id: str):

            # The HTTP request used to initiate the WebSocket handshake can be
            #   examined as needed.
            some_header_value = req.get_header('Some-Header')

            # Reject it?
            if some_condition:
                # If close() is called before accept() the code kwarg is
                #   ignored, if present, and the server returns a 403
                #   HTTP response without upgrading the connection.
                await ws.close()
                return

            # Examine subprotocols advertised by the client. Here let's just
            #   assume we only support wamp, so if the client doesn't advertise
            #   it we reject the connection.
            if 'wamp' not in ws.subprotocols:
                # If close() is not called explicitly, the framework will
                #   take care of it automatically with the default code (1000).
                return

            # If, after examining the connection info, you would like to accept
            #   it, simply call accept() as follows:
            try:
                await ws.accept(subprotocol='wamp')
            except WebSocketDisconnected:
                return

            # Simply start sending messages to the client if this is an event
            #   feed endpoint.
            while True:
                try:
                    event = await my_next_event()

                    # Send an instance of str as a WebSocket TEXT (0x01) payload
                    await ws.send_text(event)

                    # Send an instance of bytes, bytearray, or memoryview as a
                    #   WebSocket BINARY (0x02) payload.
                    await ws.send_data(event)

                    # Or if you want it to be serialized to JSON (by default; can
                    #   be customized via app.ws_options.media_handlers):
                    await ws.send_media(event)  # Defaults to WebSocketPayloadType.TEXT
                except WebSocketDisconnected:
                    # Do any necessary cleanup, then bail out
                    return

            # ...or loop like this to implement a simple request-response protocol
            while True:
                try:
                    # Use this if you expect a WebSocket TEXT (0x01) payload,
                    #   decoded from UTF-8 to a Unicode string.
                    payload_str = await ws.receive_text()

                    # Or if you are expecting a WebSocket BINARY (0x02) payload,
                    #   in which case you will end up with a byte string result:
                    payload_bytes = await ws.receive_data()

                    # Or if you want to get a serialized media object (defaults to
                    #   JSON deserialization of text payloads, and MessagePack
                    #   deserialization for BINARY payloads, but this can be
                    #   customized via app.ws_options.media_handlers).
                    media_object = await ws.receive_media()

                except WebSocketDisconnected:
                    # Do any necessary cleanup, then bail out
                    return
                except TypeError:
                    # The received message payload was not of the expected
                    #   type (e.g., got BINARY when TEXT was expected).
                    pass
                except json.JSONDecodeError:
                    # The default media deserializer uses the json standard
                    #   library, so you might see this error raised as well.
                    pass

                # At any time, you may decide to close the websocket. If the
                #   socket is already closed, this call does nothing (it will
                #   not raise an error.)
                if we_are_so_done_with_this_conversation():
                    # https://developer.mozilla.org/en-US/docs/Web/API/CloseEvent
                    await ws.close(code=1000)
                    return

                try:
                    # Here we are sending as a binary (0x02) payload type, which
                    #   will go find the handler configured for that (defaults to
                    #   MessagePack which assumes you've also installed that
                    #   package, but this can be customized as mentioned above.')
                    await ws.send_media(
                        {'event': 'message'},
                        payload_type=WebSocketPayloadType.BINARY,
                    )

                except WebSocketDisconnected:
                    # Do any necessary cleanup, then bail out. If ws.close() was
                    #   not already called by the app, the framework will take
                    #   care of it.

                    # NOTE: If you do not handle this exception, it will be
                    #   bubbled up to a default error handler that simply
                    #   logs the message as a warning and then closes the
                    #   server side of the connection. This handler can be
                    #   overridden as with any other error handler for the app.

                    return

            # ...or run a couple of different loops in parallel to support
            #  independent bidirectional message streams.

            messages = collections.deque()

            async def sink():
                while True:
                    try:
                        message = await ws.receive_text()
                    except falcon.WebSocketDisconnected:
                        break

                    messages.append(message)

            sink_task = falcon.create_task(sink())

            while not sink_task.done():
                while ws.ready and not messages and not sink_task.done():
                    await asyncio.sleep(0)

                try:
                    await ws.send_text(messages.popleft())
                except falcon.WebSocketDisconnected:
                    break

            sink_task.cancel()
            try:
                await sink_task
            except asyncio.CancelledError:
                pass


    class SomeMiddleware:
        async def process_request_ws(self, req: Request, ws: WebSocket):
            # This will be called for the HTTP request that initiates the
            #   WebSocket handshake before routing.
            pass

        async def process_resource_ws(self, req: Request, ws: WebSocket, resource, params):
            # This will be called for the HTTP request that initiates the
            #   WebSocket handshake after routing (if a route matches the
            #   request).
            pass


    app = falcon.asgi.App(middleware=SomeMiddleware())
    app.add_route('/{account_id}/messages', SomeResource())

.. tip::
   If you prefer to learn by doing, feel free to continue experimenting along
   the lines of our :ref:`WebSocket tutorial <tutorial-ws>`!

Testing
-------

Falcon's testing framework includes support for simulating WebSocket connections
with the :class:`falcon.testing.ASGIConductor` class, as demonstrated in the
following example.

.. code:: python

    # This context manages the ASGI app lifecycle, including lifespan events
    async with testing.ASGIConductor(some_app) as c:
        async def post_events():
            for i in range(100):
                await c.simulate_post('/events', json={'id': i}):
                await asyncio.sleep(0.01)

        async def get_events_ws():
            # Simulate a WebSocket connection
            async with c.simulate_ws('/events') as ws:
                while some_condition:
                    message = await ws.receive_text()

        asyncio.gather(post_events(), get_events_ws())

See also: :meth:`~falcon.testing.ASGIConductor.simulate_ws`.

Reference
---------

WebSocket Class
~~~~~~~~~~~~~~~

The framework passes an instance of the following class into
the ``on_websocket()`` responder. Conceptually, this class takes the place of the
:class:`falcon.asgi.Response` class for WebSocket connections.

.. autoclass:: falcon.asgi.WebSocket
    :members:

.. _bimh:

Built-in Media Handlers
~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: falcon.media.TextBaseHandlerWS
    :members:

.. autoclass:: falcon.media.BinaryBaseHandlerWS
    :members:

.. autoclass:: falcon.media.JSONHandlerWS
    :no-members:

.. autoclass:: falcon.media.MessagePackHandlerWS
    :no-members:

Error Types
~~~~~~~~~~~

.. autoclass:: falcon.WebSocketDisconnected
    :members:

.. autoclass:: falcon.WebSocketPathNotFound
    :no-members:

.. autoclass:: falcon.WebSocketHandlerNotFound
    :no-members:

.. autoclass:: falcon.WebSocketServerError
    :no-members:

.. autoclass:: falcon.PayloadTypeError
    :no-members:

Options
~~~~~~~

.. autoclass:: falcon.asgi.WebSocketOptions
    :members:
