# Copyright 2019 by Kurt Griffiths
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""ASGI application class."""

from inspect import isasyncgenfunction, iscoroutinefunction
import traceback

import falcon.app
from falcon.app_helpers import prepare_middleware
from falcon.errors import CompatibilityError, UnsupportedScopeError
from falcon.http_error import HTTPError
from falcon.http_status import HTTPStatus
import falcon.routing
from falcon.util.misc import http_status_to_code
from falcon.util.sync import _wrap_non_coroutine_unsafe, get_loop
from .request import Request
from .response import Response
from .structures import SSEvent


__all__ = ['App']


_EVT_RESP_EOF = {'type': 'http.response.body'}

_BODILESS_STATUS_CODES = frozenset([
    100,
    101,
    204,
    304,
])

_TYPELESS_STATUS_CODES = frozenset([
    204,
    304,
])


# TODO(kgriffs): Rename the WSGI class to App with an API alias kept for
#   backwards-compatibility.
class App(falcon.app.App):

    _STATIC_ROUTE_TYPE = falcon.routing.StaticRouteAsync

    # NOTE(kgriffs): This makes it easier to tell what we are dealing with
    #   without having to import falcon.asgi to get at the falcon.asgi.App
    #   type (which we may not be able to do under Python 3.5).
    _ASGI = True

    _default_responder_bad_request = falcon.responders.bad_request_async
    _default_responder_path_not_found = falcon.responders.path_not_found_async

    __slots__ = ['_lifespan_handlers']

    def __init__(self, *args, request_type=Request, response_type=Response, **kwargs):
        super().__init__(*args, request_type=request_type, response_type=response_type, **kwargs)
        self._lifespan_handlers = []

    async def __call__(self, scope, receive, send):  # noqa: C901
        try:
            asgi_info = scope['asgi']

            # NOTE(kgriffs): We only check this here because
            #   uvicorn does not explicitly set the 'asgi' key, which
            #   would normally mean we should assume '2.0', but uvicorn
            #   actually *does* support 3.0. But in that case, we will
            #   end up in the except clause, below, and not raise an
            #   error.
            # PERF(kgriffs): This should usually be present, so use a
            #   try..except
            try:
                version = asgi_info['version']
            except KeyError:
                # NOTE(kgriffs): According to the ASGI spec, "2.0" is
                #   the default version.
                version = '2.0'

            if not version.startswith('3.'):
                raise UnsupportedScopeError(
                    f'Falcon requires ASGI version 3.x. Detected: {asgi_info}'
                )

        except KeyError:
            asgi_info = scope['asgi'] = {'version': '2.0'}

        # NOTE(kgriffs): The ASGI spec requires the 'type' key to be present.
        scope_type = scope['type']
        if scope_type != 'http':
            if scope_type == 'lifespan':
                try:
                    spec_version = asgi_info['spec_version']
                except KeyError:
                    spec_version = '1.0'

                if not spec_version.startswith('1.') and not spec_version.startswith('2.'):
                    raise UnsupportedScopeError(
                        f'Only versions 1.x and 2.x of the ASGI "lifespan" scope are supported.'
                    )

                await self._call_lifespan_handlers(spec_version, scope, receive, send)
                return

            # NOTE(kgriffs): According to the ASGI spec: "Applications should
            #   actively reject any protocol that they do not understand with
            #   an Exception (of any type)."
            raise UnsupportedScopeError(
                f'The ASGI "{scope_type}" scope type is not supported.'
            )

        # PERF(kgriffs): This is slighter faster than using dict.get()
        # TODO(kgriffs): Use this to determine what features are supported by
        #   the servver (e.g., the headers key in the WebSocket Accept
        #   response).
        spec_version = asgi_info['spec_version'] if 'spec_version' in asgi_info else '2.0'

        if not spec_version.startswith('2.'):
            raise UnsupportedScopeError(
                f'The ASGI http scope version {spec_version} is not supported.'
            )

        resp = self._response_type(options=self.resp_options)
        req = self._request_type(scope, receive, options=self.req_options)
        if self.req_options.auto_parse_form_urlencoded:
            await req._parse_form_urlencoded()

        resource = None
        responder = None
        params = {}

        dependent_mw_resp_stack = []
        mw_req_stack, mw_rsrc_stack, mw_resp_stack = self._middleware

        req_succeeded = False

        try:
            # NOTE(ealogar): The execution of request middleware
            # should be before routing. This will allow request mw
            # to modify the path.
            # NOTE: if flag set to use independent middleware, execute
            # request middleware independently. Otherwise, only queue
            # response middleware after request middleware succeeds.
            if self._independent_middleware:
                for process_request in mw_req_stack:
                    await process_request(req, resp)

                    if resp.complete:
                        break
            else:
                for process_request, process_response in mw_req_stack:
                    if process_request and not resp.complete:
                        await process_request(req, resp)

                    if process_response:
                        dependent_mw_resp_stack.insert(0, process_response)

            if not resp.complete:
                # NOTE(warsaw): Moved this to inside the try except
                # because it is possible when using object-based
                # traversal for _get_responder() to fail.  An example is
                # a case where an object does not have the requested
                # next-hop child resource. In that case, the object
                # being asked to dispatch to its child will raise an
                # HTTP exception signalling the problem, e.g. a 404.
                responder, params, resource, req.uri_template = self._get_responder(req)

        except Exception as ex:
            if not await self._handle_exception(req, resp, ex, params):
                raise

        else:
            try:
                # NOTE(kgriffs): If the request did not match any
                # route, a default responder is returned and the
                # resource is None. In that case, we skip the
                # resource middleware methods. Resource will also be
                # None when a middleware method already set
                # resp.complete to True.
                if resource:
                    # Call process_resource middleware methods.
                    for process_resource in mw_rsrc_stack:
                        await process_resource(req, resp, resource, params)

                        if resp.complete:
                            break

                if not resp.complete:
                    await responder(req, resp, **params)

                req_succeeded = True

            except Exception as ex:
                if not await self._handle_exception(req, resp, ex, params):
                    raise

        # Call process_response middleware methods.
        for process_response in mw_resp_stack or dependent_mw_resp_stack:
            try:
                await process_response(req, resp, resource, req_succeeded)

            except Exception as ex:
                if not await self._handle_exception(req, resp, ex, params):
                    raise

                req_succeeded = False

        data = b''

        try:
            data = await resp.render_body()
        except Exception as ex:
            if not await self._handle_exception(req, resp, ex, params):
                raise

            req_succeeded = False

        resp_status = http_status_to_code(resp.status)
        default_media_type = self.resp_options.default_media_type

        if req.method == 'HEAD' or resp_status in _BODILESS_STATUS_CODES:
            #
            # PERF(vytas): move check for the less common and much faster path
            # of resp_status being in {204, 304} here; NB: this builds on the
            # assumption _TYPELESS_STATUS_CODES <= _BODILESS_STATUS_CODES.
            #
            # NOTE(kgriffs): Based on wsgiref.validate's interpretation of
            # RFC 2616, as commented in that module's source code. The
            # presence of the Content-Length header is not similarly
            # enforced.
            #
            # NOTE(kgriffs): Assuming the same for ASGI until proven otherwise.
            #
            if resp_status in _TYPELESS_STATUS_CODES:
                default_media_type = None
            elif (
                req.method == 'HEAD'and
                resp_status not in _BODILESS_STATUS_CODES and
                'content-length' not in resp._headers
            ):
                # NOTE(kgriffs): We really should be returning a Content-Length
                #   in this case according to my reading of the RFCs. By
                #   optionally using len(data) we let a resource simulate HEAD
                #   by turning around and calling it's own on_get().
                resp._headers['content-length'] = str(len(data)) if data else '0'

            await send({
                'type': 'http.response.start',
                'status': resp_status,
                'headers': resp._asgi_headers(default_media_type)
            })

            await send(_EVT_RESP_EOF)
            self._schedule_callbacks(resp)
            return

        sse_emitter = resp.sse
        if sse_emitter:
            if isasyncgenfunction(sse_emitter):
                raise TypeError(
                    'Response.sse must be an async iterable. This can be obtained by '
                    'simply executing the async generator function and then setting '
                    'the result to Response.sse, e.g.: resp.sse = some_asyncgen_function()'
                )

            await send({
                'type': 'http.response.start',
                'status': resp_status,
                'headers': resp._asgi_headers('text/event-stream')
            })

            self._schedule_callbacks(resp)

            # TODO(kgriffs): Do we need to do anything special to handle when
            #   a connection is closed?
            async for event in sse_emitter:
                if not event:
                    event = SSEvent()

                await send({
                    'type': 'http.response.body',
                    'body': event.serialize(),
                    'more_body': True
                })

            await send({'type': 'http.response.body'})
            return

        if data is not None:
            # PERF(kgriffs): Böse mußt sein. Operate directly on resp._headers
            #   to reduce overhead since this is a hot/critical code path.
            # NOTE(kgriffs): We always set content-length to match the
            #   body bytes length, even if content-length is already set. The
            #   reason being that web servers and LBs behave unpredictably
            #   when the header doesn't match the body (sometimes choosing to
            #   drop the HTTP connection prematurely, for example).
            resp._headers['content-length'] = str(len(data))

            await send({
                'type': 'http.response.start',
                'status': resp_status,
                'headers': resp._asgi_headers(default_media_type)
            })

            await send({
                'type': 'http.response.body',
                'body': data
            })

            self._schedule_callbacks(resp)
            return

        stream = resp.stream
        if not stream:
            resp._headers['content-length'] = '0'

        await send({
            'type': 'http.response.start',
            'status': resp_status,
            'headers': resp._asgi_headers(default_media_type)
        })

        if stream:
            # Detect whether this is one of the following:
            #
            #   (a) async file-like object (e.g., aiofiles)
            #   (b) async generator
            #   (c) async iterator
            #

            if hasattr(stream, 'read'):
                while True:
                    data = await stream.read(self._STREAM_BLOCK_SIZE)
                    if data == b'':
                        break
                    else:
                        await send({
                            'type': 'http.response.body',

                            # NOTE(kgriffs): Handle the case in which data == None
                            'body': data or b'',

                            'more_body': True
                        })
            else:
                # NOTE(kgriffs): Works for both async generators and iterators
                try:
                    async for data in stream:
                        await send({
                            'type': 'http.response.body',
                            'body': data,
                            'more_body': True
                        })
                except TypeError:
                    if isasyncgenfunction(stream):
                        raise TypeError(
                            'The object assigned to Response.stream appears to '
                            'be an async generator function. A generator '
                            'object is expected instead. This can be obtained '
                            'simply by calling the generator function, e.g.: '
                            'resp.stream = some_asyncgen_function()'
                        )

                    raise TypeError(
                        'Response.stream must be a generator or implement an '
                        '__aiter__ method.'
                    )

            if hasattr(stream, 'close'):
                await stream.close()

        await send(_EVT_RESP_EOF)
        self._schedule_callbacks(resp)

    def add_lifespan_handler(self, handler):
        """Add a lifespan handler object.

        A lifespan handler performs startup and/or shutdown activities for the
        main event loop. An example of this would be creating a connection
        pool and subsequently closing the connection pool to release the
        connections.

        Note:
            In a multi-process environment, lifespan events will be
            triggered independently for the individual event loop associated
            with each process.

        A lifespan handler is any class that implements the interface below.
        Note that it is only necessary to implement the coroutine functions for
        the events that you wish to handle; Falcon will simply skip over any
        missing coroutines in the lifespan handler::

            class ExampleHandler:
                async def process_startup(self, scope, event):
                    \"\"\"Process the lifespan startup event.

                    Invoked when the server is ready to startup and
                    receive connections, but before it has started to
                    do so.

                    To halt startup processing and signal to the server that it
                    should terminate, simply raise an exception and the
                    framework will convert it to a "lifespan.startup.failed"
                    event for the server.

                    Arguments:
                        scope (dict): The ASGI scope dictionary for the
                            lifespan protocol. The lifespan scope exists
                            for the duration of the event loop.
                        event (dict): The ASGI event dictionary for the
                            startup event.
                    \"\"\"

                async def process_shutdown(self, scope, event):
                    \"\"\"Process the lifespan shutdown event.

                    Invoked when the server has stopped accepting
                    connections and closed all active connections.

                    To halt shutdown processing and signal to the server
                    that it should immediately terminate, simply raise an
                    exception and the framework will convert it to a
                    "lifespan.shutdown.failed" event for the server.

                    Arguments:
                        scope (dict): The ASGI scope dictionary for the
                            lifespan protocol. The lifespan scope exists
                            for the duration of the event loop.
                        event (dict): The ASGI event dictionary for the
                            shutdown event.
                    \"\"\"

        Lifespan handlers are executed hierarchically in a stack, based on
        the order in which they were added. For example, suppose three
        handlers were added as follows::

            some_app.add_lifespan_handler(h1)
            some_app.add_lifespan_handler(h2)
            some_app.add_lifespan_handler(h3)

        In this case, the handlers' methods would be invoked by the
        framework in this order::

            h1.process_startup()

            h2.process_startup()

            h3.process_startup()
            h3.process_shutdown()

            h2.process_shutdown()

            h1.process_shutdown()

        Arguments:
            handler (object): An instantiated lifespan handler object.
        """

        for m in ('process_startup', 'process_shutdown'):
            if hasattr(handler, m):
                break
        else:
            raise TypeError(f'{handler} must implement at least one lifespan event method')

        self._lifespan_handlers.append(handler)

    def add_error_handler(self, exception, handler=None):
        if not handler:
            try:
                handler = exception.handle
            except AttributeError:
                # NOTE(kgriffs): Delegate to the parent method for error handling.
                pass

        handler = _wrap_non_coroutine_unsafe(handler)

        if handler and not iscoroutinefunction(handler):
            raise CompatibilityError(
                'The handler must be an awaitable coroutine function in order '
                'to be used safely with an ASGI app.'
            )

        super().add_error_handler(exception, handler=handler)

    def add_route(self, uri_template, resource, **kwargs):
        # TODO: Check for an _auto_async_wrap kwarg or env var and if there and True,
        #   go through the resource and wrap any non-couroutine objects. Then
        #   set that flag in the test cases.

        # NOTE(kgriffs): Inject an extra kwarg so that the compiled router
        #   will know to validate the reponder methods to make sure they
        #   are async coroutines.
        kwargs['_asgi'] = True
        super().add_route(uri_template, resource, **kwargs)

    # ------------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------------

    def _schedule_callbacks(self, resp):
        callbacks = resp._registered_callbacks
        if not callbacks:
            return

        loop = get_loop()

        for cb in callbacks:
            if iscoroutinefunction(cb):
                loop.create_task(cb())
            else:
                loop.run_in_executor(None, cb)

    async def _call_lifespan_handlers(self, ver, scope, receive, send):
        while True:
            event = await receive()
            if event['type'] == 'lifespan.startup':
                for handler in self._lifespan_handlers:
                    if hasattr(handler, 'process_startup'):
                        try:
                            await handler.process_startup(scope, event)
                        except Exception:
                            await send({
                                'type': 'lifespan.startup.failed',
                                'message': traceback.format_exc(),
                            })
                            return

                await send({'type': 'lifespan.startup.complete'})

            elif event['type'] == 'lifespan.shutdown':
                for handler in reversed(self._lifespan_handlers):
                    if hasattr(handler, 'process_shutdown'):
                        try:
                            await handler.process_shutdown(scope, event)
                        except Exception:
                            await send({
                                'type': 'lifespan.shutdown.failed',
                                'message': traceback.format_exc(),
                            })
                            return

                await send({'type': 'lifespan.shutdown.complete'})
                return

    def _prepare_middleware(self, middleware=None, independent_middleware=False):
        return prepare_middleware(
            middleware=middleware,
            independent_middleware=independent_middleware,
            asgi=True
        )

    async def _http_status_handler(self, req, resp, status, params):
        self._compose_status_response(req, resp, status)

    async def _http_error_handler(self, req, resp, error, params):
        self._compose_error_response(req, resp, error)

    async def _python_error_handler(self, req, resp, error, params):
        falcon._logger.error('Unhandled exception in ASGI app', exc_info=error)
        self._compose_error_response(req, resp, falcon.HTTPInternalServerError())

    async def _handle_exception(self, req, resp, ex, params):
        """Handle an exception raised from mw or a responder.

        Args:
            ex: Exception to handle
            req: Current request object to pass to the handler
                registered for the given exception type
            resp: Current response object to pass to the handler
                registered for the given exception type
            params: Responder params to pass to the handler
                registered for the given exception type

        Returns:
            bool: ``True`` if a handler was found and called for the
            exception, ``False`` otherwise.
        """
        err_handler = self._find_error_handler(ex)

        if err_handler is not None:
            try:
                await err_handler(req, resp, ex, params)
            except HTTPStatus as status:
                self._compose_status_response(req, resp, status)
            except HTTPError as error:
                self._compose_error_response(req, resp, error)

            return True

        # NOTE(kgriffs): No error handlers are defined for ex
        # and it is not one of (HTTPStatus, HTTPError), since it
        # would have matched one of the corresponding default
        # handlers.
        return False
