.. _middleware:

Middleware
==========

Middleware components provide a way to execute logic before the
framework routes each request, after each request is routed but before
the target responder is called, or just before the response is returned
for each request.

.. Note::
    Unlike hooks, middleware methods apply globally to the entire App.

Components are registered with the `middleware` kwarg
when instantiating Falcon's :ref:`App class <app>`. A middleware component
is simply a class that implements one or more of the event handler methods
defined below.

.. tab-set::

    .. tab-item:: WSGI

        Falcon's middleware interface is defined as follows:

        .. code:: python

            from typing import Any
            from falcon import Request, Response

            class ExampleMiddleware:
                def process_request(self, req: Request, resp: Response) -> None:
                    """Process the request before routing it.

                    Note:
                        Because Falcon routes each request based on req.path, a
                        request can be effectively re-routed by setting that
                        attribute to a new value from within process_request().

                    Args:
                        req: Request object that will eventually be
                            routed to an on_* responder method.
                        resp: Response object that will be routed to
                            the on_* responder.
                    """

                def process_resource(
                    self,
                    req: Request,
                    resp: Response,
                    resource: object,
                    params: dict[str, Any],
                ) -> None:
                    """Process the request after routing.

                    Note:
                        This method is only called when the request matches
                        a route to a resource.

                    Args:
                        req: Request object that will be passed to the
                            routed responder.
                        resp: Response object that will be passed to the
                            responder.
                        resource: Resource object to which the request was
                            routed.
                        params: A dict-like object representing any additional
                            params derived from the route's URI template fields,
                            that will be passed to the resource's responder
                            method as keyword arguments.
                    """

                def process_response(
                    self,
                    req: Request,
                    resp: Response,
                    resource: object,
                    req_succeeded: bool
                ) -> None:
                    """Post-processing of the response (after routing).

                    Args:
                        req: Request object.
                        resp: Response object.
                        resource: Resource object to which the request was
                            routed. May be None if no route was found
                            for the request.
                        req_succeeded: True if no exceptions were raised while
                            the framework processed and routed the request;
                            otherwise False.
                    """

            # A middleware instance can then be added to the Falcon app init
            from falcon import App

            app = App(middleware=[ExampleMiddleware()])

    .. tab-item:: ASGI

        The ASGI middleware interface is similar to WSGI, but also supports the
        standard ASGI lifespan events. However, because lifespan events are an
        optional part of the ASGI specification, they may or may not fire depending
        on your ASGI server.

        .. code:: python

            from typing import Any
            from falcon.asgi import Request, Response, WebSocket

            class ExampleMiddleware:
                async def process_startup(
                    self, scope: dict[str, Any], event: dict[str, Any]
                ) -> None:
                    """Process the ASGI lifespan startup event.

                    Invoked when the server is ready to start up and
                    receive connections, but before it has started to
                    do so.

                    To halt startup processing and signal to the server that it
                    should terminate, simply raise an exception and the
                    framework will convert it to a "lifespan.startup.failed"
                    event for the server.

                    Args:
                        scope (dict): The ASGI scope dictionary for the
                            lifespan protocol. The lifespan scope exists
                            for the duration of the event loop.
                        event (dict): The ASGI event dictionary for the
                            startup event.
                    """

                async def process_shutdown(
                    self, scope: dict[str, Any], event: dict[str, Any]
                ) -> None:
                    """Process the ASGI lifespan shutdown event.

                    Invoked when the server has stopped accepting
                    connections and closed all active connections.

                    To halt shutdown processing and signal to the server
                    that it should immediately terminate, simply raise an
                    exception and the framework will convert it to a
                    "lifespan.shutdown.failed" event for the server.

                    Args:
                        scope (dict): The ASGI scope dictionary for the
                            lifespan protocol. The lifespan scope exists
                            for the duration of the event loop.
                        event (dict): The ASGI event dictionary for the
                            shutdown event.
                    """

                async def process_request(self, req: Request, resp: Response) -> None:
                    """Process the request before routing it.

                    Note:
                        Because Falcon routes each request based on req.path, a
                        request can be effectively re-routed by setting that
                        attribute to a new value from within process_request().

                    Args:
                        req: Request object that will eventually be
                            routed to an on_* responder method.
                        resp: Response object that will be routed to
                            the on_* responder.
                    """

                async def process_resource(
                    self,
                    req: Request,
                    resp: Response,
                    resource: object,
                    params: dict[str, Any],
                ) -> None:
                    """Process the request after routing.

                    Note:
                        This method is only called when the request matches
                        a route to a resource.

                    Args:
                        req: Request object that will be passed to the
                            routed responder.
                        resp: Response object that will be passed to the
                            responder.
                        resource: Resource object to which the request was
                            routed.
                        params: A dict-like object representing any additional
                            params derived from the route's URI template fields,
                            that will be passed to the resource's responder
                            method as keyword arguments.
                    """

                async def process_response(
                    self,
                    req: Request,
                    resp: Response,
                    resource: object,
                    req_succeeded: bool
                ) -> None:
                    """Post-processing of the response (after routing).

                    Args:
                        req: Request object.
                        resp: Response object.
                        resource: Resource object to which the request was
                            routed. May be None if no route was found
                            for the request.
                        req_succeeded: True if no exceptions were raised while
                            the framework processed and routed the request;
                            otherwise False.
                    """

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

            # A middleware instance can then be added to the Falcon app init
            from falcon.asgi import App

            app = App(middleware=[ExampleMiddleware()])

It is also possible to implement a middleware component that is compatible
with both ASGI and WSGI apps. This is done by applying an `*_async` postfix
to distinguish the two different versions of each middleware method, as in
the following example:

.. code:: python

    import falcon as wsgi
    from falcon import asgi

    class ExampleMiddleware:
        def process_request(self, req: wsgi.Request, resp: wsgi.Response) -> None:
            """Process WSGI request using synchronous logic.

            Note that req and resp are instances of falcon.Request and
            falcon.Response, respectively.
            """

        async def process_request_async(self, req: asgi.Request, resp: asgi.Response) -> None:
            """Process ASGI request using asynchronous logic.

            Note that req and resp are instances of falcon.asgi.Request and
            falcon.asgi.Response, respectively.
            """

.. Tip::
    Because *process_request* executes before routing has occurred, if a
    component modifies ``req.path`` in its *process_request* method,
    the framework will use the modified value to route the request.

    For example::

        # Route requests based on the host header.
        req.path = '/' + req.host + req.path

.. Tip::
    The *process_resource* method is only called when the request matches
    a route to a resource. To take action when a route is not found, a
    :meth:`sink <falcon.App.add_sink>` may be used instead.

.. Tip::
    In order to pass data from a middleware function to a resource function
    use the ``req.context`` and ``resp.context`` objects. These context objects
    are intended to hold request and response data specific to your app as it
    passes through the framework.

Each component's *process_request*, *process_resource*, and
*process_response* methods are executed hierarchically, as a stack, following
the ordering of the list passed via the `middleware` kwarg of
:class:`falcon.App` or :class:`falcon.asgi.App`. For example, if a list of middleware objects are
passed as ``[mob1, mob2, mob3]``, the order of execution is as follows::

    mob1.process_request
        mob2.process_request
            mob3.process_request
                mob1.process_resource
                    mob2.process_resource
                        mob3.process_resource
                <route to resource responder method>
            mob3.process_response
        mob2.process_response
    mob1.process_response

Note that each component need not implement all `process_*`
methods; in the case that one of the three methods is missing,
it is treated as a noop in the stack. For example, if ``mob2`` did
not implement *process_request* and ``mob3`` did not implement
*process_response*, the execution order would look
like this::

    mob1.process_request
        _
            mob3.process_request
                mob1.process_resource
                    mob2.process_resource
                        mob3.process_resource
                <route to responder method>
            _
        mob2.process_response
    mob1.process_response

Short-Circuiting
----------------

A *process_request* or *process_resource* middleware method may short-circuit
further request processing by setting :attr:`falcon.Response.complete` to ``True``, e.g.::

      resp.complete = True

After the method returns, setting this flag will cause the framework to skip
any remaining *process_request* and *process_resource* methods, as well as
the responder method that the request would have been routed to. However, any
*process_response* middleware methods will still be called.

In a similar manner, setting :attr:`falcon.Response.complete` to ``True`` from
within a *process_resource* method will short-circuit further request processing
at that point.

In the example below, you can see how request processing will be short-circuited
once :attr:`falcon.Response.complete` has been set to
``True``, i.e., the framework will prevent ``mob3.process_request``, all *process_resource*
methods, as well as the routed responder method from processing the request.
However, all *process_response* methods will still be called::

    mob1.process_request
        mob2.process_request  # resp.complete = True
            <skip mob3.process_request>
            <skip mob1/mob2/mob3.process_resource>
            <skip route to resource responder method>
            mob3.process_response
        mob2.process_response
    mob1.process_response

This feature affords use cases in which the response may be pre-constructed,
such as in the case of caching.

Exception Handling
------------------

If one of the *process_request* middleware methods raises an
exception, it will be processed according to the exception type. If
the type matches a registered error handler, that handler will
be invoked and then the framework will begin to unwind the
stack, skipping any lower layers. The error handler may itself
raise an instance of :class:`~.HTTPError` or :class:`~.HTTPStatus`, in
which case the framework will use the latter exception to update the
*resp* object.

.. Note::

    By default, the framework installs two handlers, one for
    :class:`~.HTTPError` and one for :class:`~.HTTPStatus`. These can
    be overridden via :meth:`~.falcon.App.add_error_handler`.

Regardless, the framework will continue unwinding the middleware
stack. For example, if *mob2.process_request* were to raise an
error, the framework would execute the stack as follows::

    mob1.process_request
        mob2.process_request
            <skip mob1/mob2 process_resource>
            <skip mob3.process_request>
            <skip mob3.process_resource>
            <skip route to resource responder method>
            mob3.process_response
        mob2.process_response
    mob1.process_response

As illustrated above, by default, all *process_response* methods will be
executed, even when a *process_request*, *process_resource*, or *on_\** resource
responder raises an error. This behavior is controlled by the
:ref:`App class's <app>` `independent_middleware` keyword argument.

Finally, if one of the *process_response* methods raises an error,
or the routed ``on_*`` responder method itself raises an error, the
exception will be handled in a similar manner as above. Then,
the framework will execute any remaining middleware on the
stack.
