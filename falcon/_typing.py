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

from collections.abc import Awaitable
from collections.abc import Iterable
from collections.abc import Mapping
from enum import auto
from enum import Enum
import http
from http.cookiejar import Cookie
from re import Pattern
import sys
from typing import (
    Any,
    Callable,
    Literal,
    Optional,
    Protocol,
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
    WSGIEnvironment = dict[str, Any]
    StartResponse = Callable[[str, list[tuple[str, str]]], Callable[[bytes], None]]

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

_ReqT = TypeVar('_ReqT', bound='Request', contravariant=True)
_RespT = TypeVar('_RespT', bound='Response', contravariant=True)
_AReqT = TypeVar('_AReqT', bound='AsgiRequest', contravariant=True)
_ARespT = TypeVar('_ARespT', bound='AsgiResponse', contravariant=True)

Link = dict[str, str]
CookieArg = Mapping[str, Union[str, Cookie]]


# Error handlers
class ErrorHandler(Protocol[_ReqT, _RespT]):
    def __call__(
        self,
        req: _ReqT,
        resp: _RespT,
        error: Exception,
        params: dict[str, Any],
    ) -> None: ...


class AsgiErrorHandler(Protocol[_AReqT, _ARespT]):
    async def __call__(
        self,
        req: _AReqT,
        resp: _ARespT | None,
        error: Exception,
        params: dict[str, Any],
        *,
        ws: WebSocket | None = ...,
    ) -> None: ...


# Error serializers
ErrorSerializer = Callable[[_ReqT, _RespT, 'HTTPError'], None]

# Sinks
SinkPrefix = Union[str, Pattern[str]]


class SinkCallable(Protocol[_ReqT, _RespT]):
    def __call__(self, req: _ReqT, resp: _RespT, **kwargs: Any) -> None: ...


class AsgiSinkCallable(Protocol[_AReqT, _ARespT]):
    async def __call__(
        self, req: _AReqT, resp: _ARespT | None, **kwargs: Any
    ) -> None: ...


HeaderMapping = Mapping[str, str]
HeaderIter = Iterable[tuple[str, str]]
HeaderArg = Union[HeaderMapping, HeaderIter]
ResponseStatus = Union[http.HTTPStatus, str, int]
StoreArg = Optional[dict[str, Any]]
Resource = object
RangeSetHeader = Union[tuple[int, int, int], tuple[int, int, int, str]]


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
    ['Request', 'Response', Optional[Resource], dict[str, Any]], None
]
ProcessResponseMethod = Callable[
    ['Request', 'Response', Optional[Resource], bool], None
]


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
    ['AsgiRequest', 'AsgiResponse', Optional[Resource], dict[str, Any]], Awaitable[None]
]
AsgiProcessResponseMethod = Callable[
    ['AsgiRequest', 'AsgiResponse', Optional[Resource], bool], Awaitable[None]
]
AsgiProcessRequestWsMethod = Callable[['AsgiRequest', 'WebSocket'], Awaitable[None]]
AsgiProcessResourceWsMethod = Callable[
    ['AsgiRequest', 'WebSocket', Optional[Resource], dict[str, Any]], Awaitable[None]
]
ResponseCallbacks = Union[
    tuple[Callable[[], None], Literal[False]],
    tuple[Callable[[], Awaitable[None]], Literal[True]],
]


# Routing

MethodDict = Union[
    dict[str, ResponderCallable],
    dict[str, Union[AsgiResponderCallable, AsgiResponderWsCallable]],
]


class FindMethod(Protocol):
    def __call__(
        self, uri: str, req: Request | None
    ) -> tuple[object, MethodDict, dict[str, Any], str | None] | None: ...


# Media
class SerializeSync(Protocol):
    def __call__(self, media: Any, content_type: str | None = ...) -> bytes: ...


DeserializeSync = Callable[[bytes], Any]

Responder = Union[ResponderMethod, AsgiResponderMethod]


# WSGI middleware interface
class WsgiMiddlewareWithProcessRequest(Protocol[_ReqT, _RespT]):
    """WSGI Middleware with request handler."""

    def process_request(self, req: _ReqT, resp: _RespT) -> None: ...


class WsgiMiddlewareWithProcessResource(Protocol[_ReqT, _RespT]):
    """WSGI Middleware with resource handler."""

    def process_resource(
        self,
        req: _ReqT,
        resp: _RespT,
        resource: Resource | None,
        params: dict[str, Any],
    ) -> None: ...


class WsgiMiddlewareWithProcessResponse(Protocol[_ReqT, _RespT]):
    """WSGI Middleware with response handler."""

    def process_response(
        self,
        req: _ReqT,
        resp: _RespT,
        resource: Resource | None,
        req_succeeded: bool,
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
class AsgiMiddlewareWithProcessRequest(Protocol[_AReqT, _ARespT]):
    """ASGI middleware with request handler."""

    async def process_request(self, req: _AReqT, resp: _ARespT) -> None: ...


class AsgiMiddlewareWithProcessResource(Protocol[_AReqT, _ARespT]):
    """ASGI middleware with resource handler."""

    async def process_resource(
        self,
        req: _AReqT,
        resp: _ARespT,
        resource: object,
        params: Mapping[str, Any],
    ) -> None: ...


class AsgiMiddlewareWithProcessResponse(Protocol[_AReqT, _ARespT]):
    """ASGI middleware with response handler."""

    async def process_response(
        self,
        req: _AReqT,
        resp: _ARespT,
        resource: object,
        req_succeeded: bool,
    ) -> None: ...


# ASGI WebSocket middleware
class AsgiMiddlewareWithProcessRequestWs(Protocol[_AReqT]):
    """ASGI middleware with WebSocket request handler."""

    async def process_request_ws(self, req: _AReqT, ws: WebSocket) -> None: ...


class AsgiMiddlewareWithProcessResourceWs(Protocol[_AReqT]):
    """ASGI middleware with WebSocket resource handler."""

    async def process_resource_ws(
        self,
        req: _AReqT,
        ws: WebSocket,
        resource: object,
        params: Mapping[str, Any],
    ) -> None: ...


# Universal middleware that provides async versions via the _async postfix
class UniversalMiddlewareWithProcessRequest(Protocol[_AReqT, _ARespT]):
    """WSGI/ASGI middleware with request handler."""

    async def process_request_async(self, req: _AReqT, resp: _ARespT) -> None: ...


class UniversalMiddlewareWithProcessResource(Protocol[_AReqT, _ARespT]):
    """WSGI/ASGI middleware with resource handler."""

    async def process_resource_async(
        self,
        req: _AReqT,
        resp: _ARespT,
        resource: object,
        params: Mapping[str, Any],
    ) -> None: ...


class UniversalMiddlewareWithProcessResponse(Protocol[_AReqT, _ARespT]):
    """WSGI/ASGI middleware with response handler."""

    async def process_response_async(
        self,
        req: _AReqT,
        resp: _ARespT,
        resource: object,
        req_succeeded: bool,
    ) -> None: ...


# NOTE(jkmnt): This typing is far from perfect due to the Python typing limitations,
# but better than nothing. Middleware conforming to any protocol of the union
# will pass the type check. Other protocols violations are not checked.
SyncMiddleware = Union[
    WsgiMiddlewareWithProcessRequest[_ReqT, _RespT],
    WsgiMiddlewareWithProcessResource[_ReqT, _RespT],
    WsgiMiddlewareWithProcessResponse[_ReqT, _RespT],
]
"""Synchronous (WSGI) application middleware.

This type alias reflects the middleware interface for
components that can be used with a WSGI app.
"""

AsyncMiddleware = Union[
    AsgiMiddlewareWithProcessRequest[_AReqT, _ARespT],
    AsgiMiddlewareWithProcessResource[_AReqT, _ARespT],
    AsgiMiddlewareWithProcessResponse[_AReqT, _ARespT],
    # Lifespan middleware
    AsgiMiddlewareWithProcessStartup,
    AsgiMiddlewareWithProcessShutdown,
    # WebSocket middleware
    AsgiMiddlewareWithProcessRequestWs[_AReqT],
    AsgiMiddlewareWithProcessResourceWs[_AReqT],
    # Universal middleware with process_*_async methods
    UniversalMiddlewareWithProcessRequest[_AReqT, _ARespT],
    UniversalMiddlewareWithProcessResource[_AReqT, _ARespT],
    UniversalMiddlewareWithProcessResponse[_AReqT, _ARespT],
]
"""Asynchronous (ASGI) application middleware.

This type alias reflects the middleware interface for components that can be
used with an ASGI app.
"""
