# Copyright 2019-2021 by Kurt Griffiths
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

from __future__ import annotations

import asyncio
from inspect import isasyncgenfunction
from inspect import iscoroutinefunction
import traceback
from typing import (
    Any,
    Awaitable,
    Callable,
    ClassVar,
    Dict,
    Iterable,
    List,
    Optional,
    overload,
    Tuple,
    Type,
    TYPE_CHECKING,
    TypeVar,
    Union,
)

from falcon import constants
from falcon import responders
from falcon import routing
from falcon._typing import _UNSET
from falcon._typing import AsgiErrorHandler
from falcon._typing import AsgiReceive
from falcon._typing import AsgiResponderCallable
from falcon._typing import AsgiResponderWsCallable
from falcon._typing import AsgiSend
from falcon._typing import AsgiSinkCallable
from falcon._typing import SinkPrefix
import falcon.app
from falcon.app_helpers import AsyncPreparedMiddlewareResult
from falcon.app_helpers import AsyncPreparedMiddlewareWsResult
from falcon.app_helpers import prepare_middleware
from falcon.app_helpers import prepare_middleware_ws
from falcon.asgi_spec import AsgiSendMsg
from falcon.asgi_spec import EventType
from falcon.asgi_spec import WSCloseCode
from falcon.constants import MEDIA_JSON
from falcon.errors import CompatibilityError
from falcon.errors import HTTPBadRequest
from falcon.errors import WebSocketDisconnected
from falcon.http_error import HTTPError
from falcon.http_status import HTTPStatus
from falcon.media.multipart import MultipartFormHandler
from falcon.util import get_argnames
from falcon.util.misc import is_python_func
from falcon.util.sync import _should_wrap_non_coroutines
from falcon.util.sync import _wrap_non_coroutine_unsafe
from falcon.util.sync import wrap_sync_to_async

from ._asgi_helpers import _validate_asgi_scope
from ._asgi_helpers import _wrap_asgi_coroutine_func
from .multipart import MultipartForm
from .request import Request
from .response import Response
from .structures import SSEvent
from .ws import _supports_reason
from .ws import http_status_to_ws_code
from .ws import WebSocket
from .ws import WebSocketOptions

__all__ = ('App',)


# TODO(vytas): Clean up these foul workarounds before the 4.0 release.
MultipartFormHandler._ASGI_MULTIPART_FORM = MultipartForm

_EVT_RESP_EOF: AsgiSendMsg = {'type': EventType.HTTP_RESPONSE_BODY}

_BODILESS_STATUS_CODES = frozenset([100, 101, 204, 304])

_TYPELESS_STATUS_CODES = frozenset([204, 304])

_FALLBACK_WS_ERROR_CODE = 3011
_BE = TypeVar('_BE', bound=BaseException)


class App(falcon.app.App):
    '''The main entry point into a Falcon-based ASGI app.

    Each App instance provides a callable
    `ASGI <https://asgi.readthedocs.io/en/latest/>`_ interface
    and a routing engine  (for WSGI applications, see
    :class:`falcon.App`).

    Keyword Arguments:
        media_type (str): Default media type to use when initializing
            :class:`~.RequestOptions` and
            :class:`~.ResponseOptions`. The ``falcon``
            module provides a number of constants for common media types,
            such as ``falcon.MEDIA_MSGPACK``, ``falcon.MEDIA_YAML``,
            ``falcon.MEDIA_XML``, etc.
        middleware: Either a single middleware component object or an iterable
            of objects (instantiated classes) that implement the
            middleware component interface shown below.

            The interface provides support for handling both ASGI worker
            lifespan events and per-request events. However, because lifespan
            events are an optional part of the ASGI specification, they may or
            may not fire depending on your ASGI server.

            A lifespan event handler can be used to perform startup or shutdown
            activities for the main event loop. An example of this would be
            creating a connection pool and subsequently closing the connection
            pool to release the connections.

            Note:
                In a multi-process environment, lifespan events will be
                triggered independently for the individual event loop associated
                with each process.

            Note:
                The framework requires that all middleware methods be
                implemented as coroutine functions via `async def`. However,
                it is possible to implement middleware classes that support
                both ASGI and WSGI apps by distinguishing the ASGI methods
                with an `*_async` postfix (see also:
                :ref:`Middleware <middleware>`).

            It is only necessary to implement the methods for the events you
            would like to handle; Falcon simply skips over any missing
            middleware methods::

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

                    async def process_request(
                        self, req: Request, resp: Response
                    ) -> None:
                        """Process the request before routing it.

                        Note:
                            Because Falcon routes each request based on
                            req.path, a request can be effectively re-routed
                            by setting that attribute to a new value from
                            within process_request().

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
                        """Process the request and resource *after* routing.

                        Note:
                            This method is only called when the request matches
                            a route to a resource.

                        Args:
                            req: Request object that will be passed to the
                                routed responder.
                            resp: Response object that will be passed to the
                                responder.
                            resource: Resource object to which the request was
                                routed. May be ``None`` if no route was found for
                                the request.
                            params: A dict-like object representing any
                                additional params derived from the route's URI
                                template fields, that will be passed to the
                                resource's responder method as keyword
                                arguments.
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
                                routed. May be ``None`` if no route was found
                                for the request.
                            req_succeeded: True if no exceptions were raised
                                while the framework processed and routed the
                                request; otherwise False.
                        """

                    # WebSocket methods
                    async def process_request_ws(
                        self, req: Request, ws: WebSocket
                    ) -> None:
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

            (See also: :ref:`Middleware <middleware>`)

        request_type: ``Request``-like class to use instead
            of Falcon's default class. Among other things, this feature
            affords inheriting from :class:`falcon.asgi.Request` in order
            to override the ``context_type`` class variable
            (default: :class:`falcon.asgi.Request`)

        response_type: ``Response``-like class to use
            instead of Falcon's default class (default:
            :class:`falcon.asgi.Response`)

        router (object): An instance of a custom router
            to use in lieu of the default engine.
            (See also: :ref:`Custom Routers <routing_custom>`)

        independent_middleware (bool): Set to ``False`` if response
            middleware should not be executed independently of whether or
            not request middleware raises an exception (default
            ``True``). When this option is set to ``False``, a middleware
            component's ``process_response()`` method will NOT be called
            when that same component's ``process_request()`` (or that of
            a component higher up in the stack) raises an exception.

        cors_enable (bool): Set this flag to ``True`` to enable a simple
            CORS policy for all responses, including support for preflighted
            requests. An instance of :class:`..CORSMiddleware` can instead be
            passed to the middleware argument to customize its behaviour.
            (default ``False``).
            (See also: :ref:`CORS <cors>`)

        sink_before_static_route (bool): Indicates if the sinks should be processed
            before (when ``True``) or after (when ``False``) the static routes.
            This has an effect only if no route was matched. (default ``True``)
    '''

    _STATIC_ROUTE_TYPE = routing.StaticRouteAsync

    # NOTE(kgriffs): This makes it easier to tell what we are dealing with
    #   without having to import falcon.asgi.
    _ASGI: ClassVar[bool] = True

    _default_responder_bad_request: ClassVar[AsgiResponderCallable] = (
        responders.bad_request_async  # type: ignore[assignment]
    )
    _default_responder_path_not_found: ClassVar[AsgiResponderCallable] = (
        responders.path_not_found_async  # type: ignore[assignment]
    )

    __slots__ = (
        '_standard_response_type',
        '_middleware_ws',
        'ws_options',
    )

    _error_handlers: Dict[Type[BaseException], AsgiErrorHandler]  # type: ignore[assignment]
    _middleware: AsyncPreparedMiddlewareResult  # type: ignore[assignment]
    _middleware_ws: AsyncPreparedMiddlewareWsResult
    _request_type: Type[Request]
    _response_type: Type[Response]

    ws_options: WebSocketOptions
    """A set of behavioral options related to WebSocket connections.

    See also: :class:`~.WebSocketOptions`.
    """

    def __init__(
        self,
        media_type: str = constants.DEFAULT_MEDIA_TYPE,
        request_type: Optional[Type[Request]] = None,
        response_type: Optional[Type[Response]] = None,
        middleware: Union[object, Iterable[object]] = None,
        router: Optional[routing.CompiledRouter] = None,
        independent_middleware: bool = True,
        cors_enable: bool = False,
        sink_before_static_route: bool = True,
    ) -> None:
        super().__init__(
            media_type,
            request_type or Request,
            response_type or Response,
            middleware,
            router,
            independent_middleware,
            cors_enable,
            sink_before_static_route,
        )

        self.ws_options = WebSocketOptions()
        self._standard_response_type = response_type in (None, Response)

        self.add_error_handler(
            WebSocketDisconnected, self._ws_disconnected_error_handler
        )

    @_wrap_asgi_coroutine_func
    async def __call__(  # type: ignore[override] # noqa: C901
        self,
        scope: Dict[str, Any],
        receive: AsgiReceive,
        send: AsgiSend,
    ) -> None:
        # NOTE(kgriffs): The ASGI spec requires the 'type' key to be present.
        scope_type: str = scope['type']

        # PERF(kgriffs): This should usually be present, so use a
        #   try..except
        try:
            asgi_info: Dict[str, str] = scope['asgi']
        except KeyError:
            # NOTE(kgriffs): According to the ASGI spec, "2.0" is
            #   the default version.
            asgi_info = scope['asgi'] = {'version': '2.0'}

        try:
            spec_version: Optional[str] = asgi_info['spec_version']
        except KeyError:
            spec_version = None

        try:
            http_version: str = scope['http_version']
        except KeyError:
            http_version = '1.1'

        spec_version = _validate_asgi_scope(scope_type, spec_version, http_version)

        if scope_type != 'http':
            # PERF(vytas): Evaluate the potentially recurring WebSocket path
            #   first (in contrast to one-shot lifespan events).
            if scope_type == 'websocket':
                await self._handle_websocket(spec_version, scope, receive, send)
                return

            # NOTE(vytas): Else 'lifespan' -- other scope_type values have been
            #   eliminated by _validate_asgi_scope at this point.
            await self._call_lifespan_handlers(spec_version, scope, receive, send)
            return

        # NOTE(kgriffs): Per the ASGI spec, we should not proceed with request
        #   processing until after we receive an initial 'http.request' event.
        first_event = await receive()
        first_event_type = first_event['type']
        # PERF(vytas): Inline the value of EventType.HTTP_DISCONNECT in this
        #   critical code path.
        if first_event_type == 'http.disconnect':
            # NOTE(kgriffs): Bail out immediately to minimize resource usage
            return

        # NOTE(kgriffs): This is the only other type defined by the ASGI spec,
        #   but we just assert it to make it easier to track down a potential
        #   incompatibility with a future spec version.
        # PERF(vytas): Inline the value of EventType.HTTP_REQUEST in this
        #   critical code path.
        assert first_event_type == 'http.request'

        req = self._request_type(
            scope, receive, first_event=first_event, options=self.req_options
        )
        resp = self._response_type(options=self.resp_options)

        resource: Optional[object] = None
        params: Dict[str, Any] = {}

        dependent_mw_resp_stack: list = []
        mw_req_stack, mw_rsrc_stack, mw_resp_stack = self._middleware

        req_succeeded = False

        try:
            if req.method in self._META_METHODS:
                raise HTTPBadRequest()

            # NOTE(ealogar): The execution of request middleware
            # should be before routing. This will allow request mw
            # to modify the path.
            # NOTE: if flag set to use independent middleware, execute
            # request middleware independently. Otherwise, only queue
            # response middleware after request middleware succeeds.
            if self._independent_middleware:
                for process_request in mw_req_stack:
                    await process_request(req, resp)  # type: ignore[operator]

                    if resp.complete:
                        break
            else:
                for process_request, process_response in mw_req_stack:  # type: ignore[misc, assignment]
                    if process_request and not resp.complete:
                        await process_request(req, resp)  # type: ignore[operator]

                    if process_response:
                        dependent_mw_resp_stack.insert(0, process_response)

            if not resp.complete:
                # NOTE(warsaw): Moved this to inside the try except
                # because it is possible when using object-based
                # traversal for _get_responder() to fail.  An example is
                # a case where an object does not have the requested
                # next-hop child resource. In that case, the object
                # being asked to dispatch to its child will raise an
                # HTTP exception signaling the problem, e.g. a 404.
                responder: AsgiResponderCallable
                responder, params, resource, req.uri_template = self._get_responder(req)  # type: ignore[assignment]

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

        data: Optional[bytes] = b''

        try:
            # NOTE(vytas): It is only safe to inline Response.render_body()
            #   where we can be sure it hasn't been overridden, either directly
            #   or by modifying the behavior of its dependencies.
            if self._standard_response_type:
                # PERF(vytas): inline Response.render_body() in this critical code
                #   path in order to shave off an await.
                text = resp.text
                if text is None:
                    data = resp._data

                    if data is None and resp._media is not None:
                        # NOTE(kgriffs): We use a special _UNSET singleton since
                        #   None is ambiguous (the media handler might return None).
                        if resp._media_rendered is _UNSET:
                            opt = resp.options
                            if not resp.content_type:
                                resp.content_type = opt.default_media_type

                            handler, serialize_sync, _ = opt.media_handlers._resolve(
                                resp.content_type, opt.default_media_type
                            )

                            if serialize_sync:
                                resp._media_rendered = serialize_sync(resp._media)
                            else:
                                resp._media_rendered = await handler.serialize_async(
                                    resp._media, resp.content_type
                                )

                        data = resp._media_rendered
                else:
                    try:
                        # NOTE(kgriffs): Normally we expect text to be a string
                        data = text.encode()
                    except AttributeError:
                        # NOTE(kgriffs): Assume it was a bytes object already
                        data = text  # type: ignore[assignment]

            else:
                # NOTE(vytas): Custom response type.
                data = await resp.render_body()

        except Exception as ex:
            if not await self._handle_exception(req, resp, ex, params):
                raise

            req_succeeded = False

        resp_status: int = resp.status_code
        default_media_type: Optional[str] = self.resp_options.default_media_type

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
                # NOTE(kgriffs): If they are going to stream using an
                #   async generator, we can't know in advance what the
                #   content length will be.
                (data is not None or not resp.stream)
                and req.method == 'HEAD'
                and resp_status not in _BODILESS_STATUS_CODES
                and 'content-length' not in resp._headers
            ):
                # NOTE(kgriffs): We really should be returning a Content-Length
                #   in this case according to my reading of the RFCs. By
                #   optionally using len(data) we let a resource simulate HEAD
                #   by turning around and calling it's own on_get().
                resp._headers['content-length'] = str(len(data)) if data else '0'

            await send(
                {
                    # PERF(vytas): Inline the value of
                    #   EventType.HTTP_RESPONSE_START in this critical code path.
                    'type': 'http.response.start',
                    'status': resp_status,
                    'headers': resp._asgi_headers(default_media_type),
                }
            )

            await send(_EVT_RESP_EOF)

            # PERF(vytas): Check resp._registered_callbacks directly to shave
            #   off a function call since this is a hot/critical code path.
            if resp._registered_callbacks:
                self._schedule_callbacks(resp)
            return

        # PERF(vytas): Operate directly on the resp private interface to reduce
        #   overhead since this is a hot/critical code path.
        if resp._sse:
            sse_emitter = resp._sse
            if isasyncgenfunction(sse_emitter):
                raise TypeError(
                    'Response.sse must be an async iterable. This can be obtained by '
                    'simply executing the async generator function and then setting '
                    'the result to Response.sse, e.g.: '
                    'resp.sse = some_asyncgen_function()'
                )

            # NOTE(kgriffs): This must be done in a separate task because
            #   receive() can block for some time (until the connection is
            #   actually closed).
            async def watch_disconnect() -> None:
                while True:
                    received_event = await receive()
                    if received_event['type'] == EventType.HTTP_DISCONNECT:
                        break

            watcher = asyncio.create_task(watch_disconnect())

            await send(
                {
                    'type': EventType.HTTP_RESPONSE_START,
                    'status': resp_status,
                    'headers': resp._asgi_headers('text/event-stream'),
                }
            )

            # PERF(vytas): Check resp._registered_callbacks directly to shave
            #   off a function call since this is a hot/critical code path.
            if resp._registered_callbacks:
                self._schedule_callbacks(resp)

            sse_handler, _, _ = self.resp_options.media_handlers._resolve(
                MEDIA_JSON, MEDIA_JSON, raise_not_found=False
            )

            # TODO(kgriffs): Do we need to do anything special to handle when
            #   a connection is closed?
            async for event in sse_emitter:
                if not event:
                    event = SSEvent()

                # NOTE(kgriffs): According to the ASGI spec, once the client
                #   disconnects, send() acts as a no-op. We have to check
                #   the connection state using watch_disconnect() above.
                await send(
                    {
                        'type': EventType.HTTP_RESPONSE_BODY,
                        'body': event.serialize(sse_handler),
                        'more_body': True,
                    }
                )

                if watcher.done():  # pragma: no py39,py310 cover
                    break

            watcher.cancel()
            try:
                await watcher
            except asyncio.CancelledError:
                pass

            await send({'type': EventType.HTTP_RESPONSE_BODY})
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

            await send(
                {
                    # PERF(vytas): Inline the value of
                    #   EventType.HTTP_RESPONSE_START in this critical code path.
                    'type': 'http.response.start',
                    'status': resp_status,
                    'headers': resp._asgi_headers(default_media_type),
                }
            )

            await send(
                {
                    # PERF(vytas): Inline the value of
                    #   EventType.HTTP_RESPONSE_BODY in this critical code path.
                    'type': 'http.response.body',
                    'body': data,
                }
            )

            # PERF(vytas): Check resp._registered_callbacks directly to shave
            #   off a function call since this is a hot/critical code path.
            if resp._registered_callbacks:
                self._schedule_callbacks(resp)
            return

        stream = resp.stream
        if not stream:
            resp._headers['content-length'] = '0'

        await send(
            {
                # PERF(vytas): Inline the value of
                #   EventType.HTTP_RESPONSE_START in this critical code path.
                'type': 'http.response.start',
                'status': resp_status,
                'headers': resp._asgi_headers(default_media_type),
            }
        )

        if stream:
            # Detect whether this is one of the following:
            #
            #   (a) async file-like object (e.g., aiofiles)
            #   (b) async generator
            #   (c) async iterator
            #

            if hasattr(stream, 'read'):
                try:
                    while True:
                        data = await stream.read(self._STREAM_BLOCK_SIZE)
                        if data == b'':
                            break
                        else:
                            await send(
                                {
                                    'type': EventType.HTTP_RESPONSE_BODY,
                                    # NOTE(kgriffs): Handle the case in which
                                    #   data is None
                                    'body': data or b'',
                                    'more_body': True,
                                }
                            )
                finally:
                    if hasattr(stream, 'close'):
                        await stream.close()
            else:
                # NOTE(kgriffs): Works for both async generators and iterators
                try:
                    async for data in stream:
                        # NOTE(kgriffs): We can not rely on StopIteration
                        #   because of Pep 479 that is implemented starting
                        #   with Python 3.7. AFAICT this is only an issue
                        #   when using an async iterator instead of an async
                        #   generator.
                        if data is None:
                            break

                        await send(
                            {
                                'type': EventType.HTTP_RESPONSE_BODY,
                                'body': data,
                                'more_body': True,
                            }
                        )
                except TypeError as ex:
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
                        '__aiter__ method. Error raised while iterating over '
                        'Response.stream: ' + str(ex)
                    )
                finally:
                    # NOTE(vytas): This could be DRYed with the above identical
                    #   twoliner in a one large block, but OTOH we would be
                    #   unable to reuse the current try.. except.
                    if hasattr(stream, 'close'):
                        await stream.close()

        await send(_EVT_RESP_EOF)

        # PERF(vytas): Check resp._registered_callbacks directly to shave
        #   off a function call since this is a hot/critical code path.
        if resp._registered_callbacks:
            self._schedule_callbacks(resp)

    def add_route(self, uri_template: str, resource: object, **kwargs: Any) -> None:
        # NOTE(kgriffs): Inject an extra kwarg so that the compiled router
        #   will know to validate the responder methods to make sure they
        #   are async coroutines.
        kwargs['_asgi'] = True
        super().add_route(uri_template, resource, **kwargs)

    add_route.__doc__ = falcon.app.App.add_route.__doc__  # NOTE: not really required

    def add_sink(self, sink: AsgiSinkCallable, prefix: SinkPrefix = r'/') -> None:  # type: ignore[override]
        if not iscoroutinefunction(sink) and is_python_func(sink):
            if _should_wrap_non_coroutines():
                sink = wrap_sync_to_async(sink)
            else:
                raise CompatibilityError(
                    'The sink method must be an awaitable coroutine function '
                    'in order to be used safely with an ASGI app.'
                )

        super().add_sink(sink, prefix=prefix)  # type: ignore[arg-type]

    add_sink.__doc__ = falcon.app.App.add_sink.__doc__  # NOTE: not really required

    @overload  # type: ignore[override]
    def add_error_handler(
        self,
        exception: Type[_BE],
        handler: Callable[[Request, Response, _BE, Dict[str, Any]], Awaitable[None]],
    ) -> None: ...

    @overload
    def add_error_handler(
        self,
        exception: Union[Type[BaseException], Iterable[Type[BaseException]]],
        handler: Optional[AsgiErrorHandler] = None,
    ) -> None: ...

    def add_error_handler(  # type: ignore[misc]
        self,
        exception: Union[Type[BaseException], Iterable[Type[BaseException]]],
        handler: Optional[AsgiErrorHandler] = None,
    ) -> None:
        """Register a handler for one or more exception types.

        Error handlers may be registered for any exception type, including
        :class:`~.HTTPError` or :class:`~.HTTPStatus`. This feature
        provides a central location for logging and otherwise handling
        exceptions raised by responders, hooks, and middleware components.

        A handler can raise an instance of :class:`~.HTTPError` or
        :class:`~.HTTPStatus` to communicate information about the issue to
        the client.  Alternatively, a handler may modify `resp`
        directly.

        An error handler "matches" a raised exception if the exception is an
        instance of the corresponding exception type. If more than one error
        handler matches the raised exception, the framework will choose the
        most specific one, as determined by the method resolution order of the
        raised exception type. If multiple error handlers are registered for the
        *same* exception class, then the most recently-registered handler is
        used.

        For example, suppose we register error handlers as follows::

            app = App()
            app.add_error_handler(falcon.HTTPNotFound, custom_handle_not_found)
            app.add_error_handler(falcon.HTTPError, custom_handle_http_error)
            app.add_error_handler(Exception, custom_handle_uncaught_exception)
            app.add_error_handler(falcon.HTTPNotFound, custom_handle_404)

        If an instance of ``falcon.HTTPForbidden`` is raised, it will be
        handled by ``custom_handle_http_error()``. ``falcon.HTTPError`` is a
        superclass of ``falcon.HTTPForbidden`` and a subclass of ``Exception``,
        so it is the most specific exception type with a registered handler.

        If an instance of ``falcon.HTTPNotFound`` is raised, it will be handled
        by ``custom_handle_404()``, not by ``custom_handle_not_found()``, because
        ``custom_handle_404()`` was registered more recently.

        Note:

            By default, the framework installs three handlers, one for
            :class:`~.HTTPError`, one for :class:`~.HTTPStatus`, and one for
            the standard ``Exception`` type, which prevents passing uncaught
            exceptions to the WSGI server. These can be overridden by adding a
            custom error handler method for the exception type in question.

            When a generic unhandled exception is raised while
            handling a :ref:`WebSocket <ws>` connection, the default handler will
            close the connection with the standard close code ``1011`` (Internal
            Error). If your ASGI server does not support this code, the
            framework will use code ``3011`` instead; or you can customize
            it via the
            :attr:`~falcon.asgi.WebSocketOptions.error_close_code`
            property of :attr:`~.ws_options`.

            On the other hand, if an ``on_websocket()`` responder raises an
            instance of :class:`~falcon.HTTPError`, the default error handler
            will close the :ref:`WebSocket <ws>` connection with a framework
            close code derived by adding ``3000`` to the HTTP status code (e.g.,
            ``3404``)

        Args:
            exception (type or iterable of types): When handling a request,
                whenever an error occurs that is an instance of the specified
                type(s), the associated handler will be called. Either a single
                type or an iterable of types may be specified.

            handler (callable): A coroutine function taking the
                form::

                    async def func(req, resp, ex, params, ws=None):
                        pass

                In the case of a WebSocket connection, the `resp` argument
                will be ``None``, while the `ws` keyword argument
                will receive the :class:`~falcon.asgi.WebSocket` object
                representing the connection.

                If the `handler` keyword argument is not provided to
                :meth:`~.add_error_handler`, the handler will default to
                ``exception.handle``, where ``exception`` is the error type
                specified above, and ``handle`` is a static method (i.e.,
                decorated with ``@staticmethod``) that accepts the params
                just described. For example::

                    class CustomException(CustomBaseException):

                        @staticmethod
                        async def handle(req, resp, ex, params):
                            # TODO: Log the error
                            # Convert to an instance of falcon.HTTPError
                            raise falcon.HTTPError(falcon.HTTP_792)

                Note, however, that if an iterable of exception types is
                specified instead of a single type, the handler must be
                explicitly specified using the `handler` keyword argument.
        """

        if handler is None:
            handler = getattr(exception, 'handle', None)
            if handler is None:
                raise AttributeError(
                    'handler must either be specified explicitly or defined as a '
                    'static method named "handle" that is a member of the given '
                    'exception class.'
                )

        # NOTE(vytas): Do not shoot ourselves in the foot in case error
        #   handlers are our own cythonized code.
        if handler not in (
            self._http_status_handler,
            self._http_error_handler,
            self._python_error_handler,
        ):
            handler = _wrap_non_coroutine_unsafe(handler)  # type: ignore[assignment]

        # NOTE(kgriffs): iscoroutinefunction() always returns False
        #   for cythonized functions.
        #
        #   https://github.com/cython/cython/issues/2273
        #   https://bugs.python.org/issue38225
        #
        if not iscoroutinefunction(handler) and is_python_func(handler):
            raise CompatibilityError(
                'The handler must be an awaitable coroutine function in order '
                'to be used safely with an ASGI app.'
            )
        handler_callable: AsgiErrorHandler = handler

        exception_tuple: Tuple[type[BaseException], ...]
        try:
            exception_tuple = tuple(exception)  # type: ignore[arg-type]
        except TypeError:
            exception_tuple = (exception,)  # type: ignore[assignment]

        for exc in exception_tuple:
            if not issubclass(exc, BaseException):
                raise TypeError('"exception" must be an exception type.')

            self._error_handlers[exc] = handler_callable

    # ------------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------------

    def _schedule_callbacks(self, resp: Response) -> None:
        callbacks = resp._registered_callbacks
        # PERF(vytas): resp._registered_callbacks is already checked directly
        # to shave off a function call since this is a hot/critical code path.
        # if not callbacks:
        #     return

        loop = asyncio.get_running_loop()

        for cb, is_async in callbacks or ():
            if is_async:
                loop.create_task(cb())  # type: ignore[arg-type]
            else:
                loop.run_in_executor(None, cb)

    async def _call_lifespan_handlers(
        self, ver: str, scope: Dict[str, Any], receive: AsgiReceive, send: AsgiSend
    ) -> None:
        while True:
            event = await receive()
            if event['type'] == 'lifespan.startup':
                # PERF(vytas): Perform these sanity checks upon application
                #   startup, as opposed to repeating them every request.

                # NOTE(vytas): If missing, 'asgi' is populated in __call__.
                asgi_info: Dict[str, str] = scope['asgi']
                version = asgi_info.get('version', '2.0 (implicit)')
                if not version.startswith('3.'):
                    await send(
                        {
                            'type': EventType.LIFESPAN_STARTUP_FAILED,
                            'message': (
                                'Falcon requires ASGI version 3.x. '
                                f'Detected: {version}.'
                            ),
                        }
                    )
                    return

                if self.req_options._auto_parse_form_urlencoded:
                    await send(
                        {
                            'type': EventType.LIFESPAN_STARTUP_FAILED,
                            'message': (
                                'The deprecated WSGI RequestOptions.'
                                'auto_parse_form_urlencoded '
                                'option is not supported for Falcon ASGI apps. '
                                'Please use Request.get_media() instead. '
                            ),
                        }
                    )
                    return

                for handler in self._unprepared_middleware:
                    if hasattr(handler, 'process_startup'):
                        try:
                            await handler.process_startup(scope, event)
                        except Exception:
                            await send(
                                {
                                    'type': EventType.LIFESPAN_STARTUP_FAILED,
                                    'message': traceback.format_exc(),
                                }
                            )
                            return

                await send({'type': EventType.LIFESPAN_STARTUP_COMPLETE})

            elif event['type'] == 'lifespan.shutdown':
                for handler in reversed(self._unprepared_middleware):
                    if hasattr(handler, 'process_shutdown'):
                        try:
                            await handler.process_shutdown(scope, event)
                        except Exception:
                            await send(
                                {
                                    'type': EventType.LIFESPAN_SHUTDOWN_FAILED,
                                    'message': traceback.format_exc(),
                                }
                            )
                            return

                await send({'type': EventType.LIFESPAN_SHUTDOWN_COMPLETE})
                return

    async def _handle_websocket(
        self, ver: str, scope: Dict[str, Any], receive: AsgiReceive, send: AsgiSend
    ) -> None:
        first_event = await receive()
        if first_event['type'] != EventType.WS_CONNECT:
            # NOTE(kgriffs): The handshake was abandoned or this is a message
            #   we don't support, so bail out. This also fulfills the ASGI
            #   spec requirement to only process the request after
            #   receiving and verifying the first event.
            response = {'type': EventType.WS_CLOSE, 'code': WSCloseCode.SERVER_ERROR}
            if _supports_reason(ver):
                response['reason'] = 'Internal Server Error'

            await send(response)
            return

        req = self._request_type(scope, receive, options=self.req_options)

        web_socket = WebSocket(
            ver,
            scope,
            receive,
            send,
            self.ws_options.media_handlers,
            self.ws_options.max_receive_queue,
            self.ws_options.default_close_reasons,
        )

        params: Dict[str, Any] = {}

        request_mw, resource_mw = self._middleware_ws

        try:
            for process_request_ws in request_mw:
                await process_request_ws(req, web_socket)

            on_websocket: AsgiResponderWsCallable
            on_websocket, params, resource, req.uri_template = self._get_responder(req)  # type: ignore[assignment]

            # NOTE(kgriffs): If the request did not match any
            # route, a default responder is returned and the
            # resource is None. In that case, we skip the
            # resource middleware methods. Resource will also be
            # None when a middleware method already set
            # resp.complete to True.
            if resource:
                for process_resource_ws in resource_mw:
                    await process_resource_ws(req, web_socket, resource, params)

            await on_websocket(req, web_socket, **params)
            await web_socket.close()

        except Exception as ex:
            if not await self._handle_exception(req, None, ex, params, ws=web_socket):
                raise

    def _prepare_middleware(  # type: ignore[override]
        self, middleware: List[object], independent_middleware: bool = False
    ) -> AsyncPreparedMiddlewareResult:
        self._middleware_ws = prepare_middleware_ws(middleware)

        return prepare_middleware(
            middleware=middleware,
            independent_middleware=independent_middleware,
            asgi=True,
        )

    async def _http_status_handler(  # type: ignore[override]
        self,
        req: Request,
        resp: Optional[Response],
        status: HTTPStatus,
        params: Dict[str, Any],
        ws: Optional[WebSocket] = None,
    ) -> None:
        if resp:
            self._compose_status_response(req, resp, status)
        elif ws:
            code = http_status_to_ws_code(status.status_code)
            falcon._logger.error(
                '[FALCON] HTTPStatus %s raised while handling WebSocket. '
                'Closing with code %s',
                status,
                code,
            )
            await ws.close(code)
        else:
            raise NotImplementedError('resp or ws expected')

    async def _http_error_handler(  # type: ignore[override]
        self,
        req: Request,
        resp: Optional[Response],
        error: HTTPError,
        params: Dict[str, Any],
        ws: Optional[WebSocket] = None,
    ) -> None:
        if resp:
            self._compose_error_response(req, resp, error)
        elif ws:
            code = http_status_to_ws_code(error.status_code)
            falcon._logger.error(
                '[FALCON] HTTPError %s raised while handling WebSocket. '
                'Closing with code %s',
                error,
                code,
            )
            await ws.close(code)
        else:
            raise NotImplementedError('resp or ws expected')

    async def _python_error_handler(  # type: ignore[override]
        self,
        req: Request,
        resp: Optional[Response],
        error: BaseException,
        params: Dict[str, Any],
        ws: Optional[WebSocket] = None,
    ) -> None:
        falcon._logger.error('[FALCON] Unhandled exception in ASGI app', exc_info=error)

        if resp:
            self._compose_error_response(req, resp, falcon.HTTPInternalServerError())
        elif ws:
            await self._ws_cleanup_on_error(ws)
        else:
            raise NotImplementedError('resp or ws expected')

    async def _ws_disconnected_error_handler(
        self,
        req: Request,
        resp: Optional[Response],
        error: WebSocketDisconnected,
        params: Dict[str, Any],
        ws: Optional[WebSocket] = None,
    ) -> None:
        assert resp is None
        assert ws is not None
        falcon._logger.debug(
            '[FALCON] WebSocket client disconnected with code %i', error.code
        )
        await self._ws_cleanup_on_error(ws)

    if TYPE_CHECKING:

        def _find_error_handler(  # type: ignore[override]
            self, ex: BaseException
        ) -> Optional[AsgiErrorHandler]: ...

    async def _handle_exception(  # type: ignore[override]
        self,
        req: Request,
        resp: Optional[Response],
        ex: BaseException,
        params: Dict[str, Any],
        ws: Optional[WebSocket] = None,
    ) -> bool:
        """Handle an exception raised from mw or a responder.

        Args:
            ex: Exception to handle
            req: Current request object to pass to the handler registered for
                the given exception type
            resp: Current response object to pass to the handler registered for
                the given exception type. Will be ``None`` in the case of a
                WebSocket request.
            params: Responder params to pass to the handler
                registered for the given exception type

        Keyword Args:
            ws: WebSocket instance in the case that the error was raised while
                handling a WebSocket connection.

        Returns:
            bool: ``True`` if a handler was found and called for the
            exception, ``False`` otherwise.
        """
        err_handler = self._find_error_handler(ex)

        if resp:
            # NOTE(caselit): Reset body, data and media before calling the handler
            resp.text = resp.data = resp.media = None

        if err_handler is not None:
            try:
                kwargs = {}

                if ws and 'ws' in get_argnames(err_handler):
                    kwargs['ws'] = ws

                await err_handler(req, resp, ex, params, **kwargs)

            except HTTPStatus as status:
                await self._http_status_handler(req, resp, status, params, ws=ws)
            except HTTPError as error:
                await self._http_error_handler(req, resp, error, params, ws=ws)

            return True

        # NOTE(kgriffs): No error handlers are defined for ex
        # and it is not one of (HTTPStatus, HTTPError), since it
        # would have matched one of the corresponding default
        # handlers.
        return False

    async def _ws_cleanup_on_error(self, ws: WebSocket) -> None:
        # NOTE(kgriffs): Attempt to close cleanly on our end
        try:
            await ws.close(self.ws_options.error_close_code)
        except Exception as ex:
            # NOTE(kgriffs): This can be raised by Daphne. We also
            #   may raise it ourselves for errors codes < 1000, but in that
            #   case we just include this string in the exception message
            #   to make it easier to verify test coverage of the following.
            if 'invalid close code' in str(ex).lower():
                await ws.close(_FALLBACK_WS_ERROR_CODE)
            else:
                falcon._logger.warning(
                    (
                        '[FALCON] Attempt to close web connection cleanly '
                        'failed due to raised error.'
                    ),
                    exc_info=True,
                )
                raise
