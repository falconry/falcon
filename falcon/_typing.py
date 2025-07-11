# Copyright 2021-2025 by Vytautas Liuolia.
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
"""Private type aliases used internally by Falcon.."""

from __future__ import annotations

from enum import auto
from enum import Enum
import http
from http.cookiejar import Cookie
import sys
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Iterable,
    List,
    Literal,
    Mapping,
    Optional,
    Pattern,
    Protocol,
    Tuple,
    TYPE_CHECKING,
    TypeVar,
    Union,
)

# NOTE(vytas): Mypy still struggles to handle a conditional import in the EAFP
#   fashion, so we branch on Py version instead (which it does understand).
if sys.version_info >= (3, 11):
    from wsgiref.types import StartResponse as StartResponse
    from wsgiref.types import WSGIEnvironment as WSGIEnvironment
else:
    WSGIEnvironment = Dict[str, Any]
    StartResponse = Callable[[str, List[Tuple[str, str]]], Callable[[bytes], None]]

if TYPE_CHECKING:
    from falcon.asgi import Request as AsgiRequest
    from falcon.asgi import Response as AsgiResponse
    from falcon.asgi import WebSocket
    from falcon.asgi_spec import AsgiEvent
    from falcon.asgi_spec import AsgiSendMsg
    from falcon.http_error import HTTPError
    from falcon.request import Request
    from falcon.response import Response


class _Unset(Enum):
    UNSET = auto()


_T = TypeVar('_T')
_UNSET = _Unset.UNSET
UnsetOr = Union[Literal[_Unset.UNSET], _T]

Link = Dict[str, str]
CookieArg = Mapping[str, Union[str, Cookie]]
# Error handlers
ErrorHandler = Callable[['Request', 'Response', Exception, Dict[str, Any]], None]


class AsgiErrorHandler(Protocol):
    async def __call__(
        self,
        req: AsgiRequest,
        resp: Optional[AsgiResponse],
        error: Exception,
        params: Dict[str, Any],
        *,
        ws: Optional[WebSocket] = ...,
    ) -> None: ...


# Error serializers
ErrorSerializer = Callable[['Request', 'Response', 'HTTPError'], None]

# Sinks
SinkPrefix = Union[str, Pattern[str]]


class SinkCallable(Protocol):
    def __call__(
        self, req: Request, resp: Response, **kwargs: Optional[str]
    ) -> None: ...


class AsgiSinkCallable(Protocol):
    async def __call__(
        self, req: AsgiRequest, resp: AsgiResponse, **kwargs: Optional[str]
    ) -> None: ...


HeaderMapping = Mapping[str, str]
HeaderIter = Iterable[Tuple[str, str]]
HeaderArg = Union[HeaderMapping, HeaderIter]
ResponseStatus = Union[http.HTTPStatus, str, int]
StoreArg = Optional[Dict[str, Any]]
Resource = object
RangeSetHeader = Union[Tuple[int, int, int], Tuple[int, int, int, str]]


# WSGI
class ResponderMethod(Protocol):
    def __call__(
        self,
        resource: Resource,
        req: Request,
        resp: Response,
        **kwargs: Any,
    ) -> None: ...


class ResponderCallable(Protocol):
    def __call__(self, req: Request, resp: Response, **kwargs: Any) -> None: ...


ProcessRequestMethod = Callable[['Request', 'Response'], None]
ProcessResourceMethod = Callable[
    ['Request', 'Response', Resource, Dict[str, Any]], None
]
ProcessResponseMethod = Callable[['Request', 'Response', Resource, bool], None]


# ASGI
class AsgiResponderMethod(Protocol):
    async def __call__(
        self,
        resource: Resource,
        req: AsgiRequest,
        resp: AsgiResponse,
        **kwargs: Any,
    ) -> None: ...


class AsgiResponderCallable(Protocol):
    async def __call__(
        self, req: AsgiRequest, resp: AsgiResponse, **kwargs: Any
    ) -> None: ...


class AsgiResponderWsCallable(Protocol):
    async def __call__(
        self, req: AsgiRequest, ws: WebSocket, **kwargs: Any
    ) -> None: ...


AsgiReceive = Callable[[], Awaitable['AsgiEvent']]
AsgiSend = Callable[['AsgiSendMsg'], Awaitable[None]]
AsgiProcessRequestMethod = Callable[['AsgiRequest', 'AsgiResponse'], Awaitable[None]]
AsgiProcessResourceMethod = Callable[
    ['AsgiRequest', 'AsgiResponse', Resource, Dict[str, Any]], Awaitable[None]
]
AsgiProcessResponseMethod = Callable[
    ['AsgiRequest', 'AsgiResponse', Resource, bool], Awaitable[None]
]
AsgiProcessRequestWsMethod = Callable[['AsgiRequest', 'WebSocket'], Awaitable[None]]
AsgiProcessResourceWsMethod = Callable[
    ['AsgiRequest', 'WebSocket', Resource, Dict[str, Any]], Awaitable[None]
]
ResponseCallbacks = Union[
    Tuple[Callable[[], None], Literal[False]],
    Tuple[Callable[[], Awaitable[None]], Literal[True]],
]


# Routing

MethodDict = Union[
    Dict[str, ResponderCallable],
    Dict[str, Union[AsgiResponderCallable, AsgiResponderWsCallable]],
]


class FindMethod(Protocol):
    def __call__(
        self, uri: str, req: Optional[Request]
    ) -> Optional[Tuple[object, MethodDict, Dict[str, Any], Optional[str]]]: ...


# Media
class SerializeSync(Protocol):
    def __call__(self, media: Any, content_type: Optional[str] = ...) -> bytes: ...


DeserializeSync = Callable[[bytes], Any]

Responder = Union[ResponderMethod, AsgiResponderMethod]


# WSGI middleware interface
class WsgiMiddlewareWithProcessRequest(Protocol):
    """WSGI Middleware with request handler."""

    def process_request(self, req: Request, resp: Response) -> None: ...


class WsgiMiddlewareWithProcessResource(Protocol):
    """WSGI Middleware with resource handler."""

    def process_resource(
        self,
        req: Request,
        resp: Response,
        resource: object,
        params: Dict[str, Any],
    ) -> None: ...


class WsgiMiddlewareWithProcessResponse(Protocol):
    """WSGI Middleware with response handler."""

    def process_response(
        self, req: Request, resp: Response, resource: object, req_succeeded: bool
    ) -> None: ...


# ASGI lifespan middleware interface
class AsgiMiddlewareWithProcessStartup(Protocol):
    """ASGI middleware with startup handler."""

    async def process_startup(
        self, scope: Mapping[str, Any], event: Mapping[str, Any]
    ) -> None: ...


class AsgiMiddlewareWithProcessShutdown(Protocol):
    """ASGI middleware with shutdown handler."""

    async def process_shutdown(
        self, scope: Mapping[str, Any], event: Mapping[str, Any]
    ) -> None: ...


# ASGI middleware interface
class AsgiMiddlewareWithProcessRequest(Protocol):
    """ASGI middleware with request handler."""

    async def process_request(self, req: AsgiRequest, resp: AsgiResponse) -> None: ...


class AsgiMiddlewareWithProcessResource(Protocol):
    """ASGI middleware with resource handler."""

    async def process_resource(
        self,
        req: AsgiRequest,
        resp: AsgiResponse,
        resource: object,
        params: Mapping[str, Any],
    ) -> None: ...


class AsgiMiddlewareWithProcessResponse(Protocol):
    """ASGI middleware with response handler."""

    async def process_response(
        self,
        req: AsgiRequest,
        resp: AsgiResponse,
        resource: object,
        req_succeeded: bool,
    ) -> None: ...


# ASGI WebSocket middleware
class AsgiMiddlewareWithProcessRequestWs(Protocol):
    """ASGI middleware with WebSocket request handler."""

    async def process_request_ws(self, req: AsgiRequest, ws: WebSocket) -> None: ...


class AsgiMiddlewareWithProcessResourceWs(Protocol):
    """ASGI middleware with WebSocket resource handler."""

    async def process_resource_ws(
        self,
        req: AsgiRequest,
        ws: WebSocket,
        resource: object,
        params: Mapping[str, Any],
    ) -> None: ...


# Universal middleware that provides async versions via the _async postfix
class UniversalMiddlewareWithProcessRequest(WsgiMiddlewareWithProcessRequest, Protocol):
    """WSGI/ASGI middleware with request handler."""

    async def process_request_async(
        self, req: AsgiRequest, resp: AsgiResponse
    ) -> None: ...


class UniversalMiddlewareWithProcessResource(
    WsgiMiddlewareWithProcessResource, Protocol
):
    """WSGI/ASGI middleware with resource handler."""

    async def process_resource_async(
        self,
        req: AsgiRequest,
        resp: AsgiResponse,
        resource: object,
        params: Mapping[str, Any],
    ) -> None: ...


class UniversalMiddlewareWithProcessResponse(
    WsgiMiddlewareWithProcessResponse, Protocol
):
    """WSGI/ASGI middleware with response handler."""

    async def process_response_async(
        self,
        req: AsgiRequest,
        resp: AsgiResponse,
        resource: object,
        req_succeeded: bool,
    ) -> None: ...


# NOTE(jkmnt): This typing is far from perfect due to the Python typing limitations,
# but better than nothing. Middleware conforming to any protocol of the union
# will pass the type check. Other protocols violations are not checked.
SyncMiddleware = Union[
    WsgiMiddlewareWithProcessRequest,
    WsgiMiddlewareWithProcessResource,
    WsgiMiddlewareWithProcessResponse,
]
"""Synchronous (WSGI) application middleware.

This type alias reflects the middleware interface for
components that can be used with a WSGI app.
"""

AsyncMiddleware = Union[
    AsgiMiddlewareWithProcessRequest,
    AsgiMiddlewareWithProcessResource,
    AsgiMiddlewareWithProcessResponse,
    # Lifespan middleware
    AsgiMiddlewareWithProcessStartup,
    AsgiMiddlewareWithProcessShutdown,
    # WebSocket middleware
    AsgiMiddlewareWithProcessRequestWs,
    AsgiMiddlewareWithProcessResourceWs,
    # Universal middleware with process_*_async methods
    UniversalMiddlewareWithProcessRequest,
    UniversalMiddlewareWithProcessResource,
    UniversalMiddlewareWithProcessResponse,
]
"""Asynchronous (ASGI) application middleware.

This type alias reflects the middleware interface for components that can be
used with an ASGI app.
"""
