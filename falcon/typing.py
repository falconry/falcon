# Copyright 2021-2023 by Vytautas Liuolia.
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
"""Shorthand definitions for more complex types."""

from __future__ import annotations

from enum import auto
from enum import Enum
import http
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Pattern,
    Protocol,
    Tuple,
    TYPE_CHECKING,
    TypeVar,
    Union,
)

try:
    from wsgiref.types import StartResponse as StartResponse
    from wsgiref.types import WSGIEnvironment as WSGIEnvironment
except ImportError:
    if not TYPE_CHECKING:
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


class _Missing(Enum):
    MISSING = auto()


_T = TypeVar('_T')
MISSING = _Missing.MISSING
MissingOr = Union[Literal[_Missing.MISSING], _T]

Link = Dict[str, str]

# Error handlers
ErrorHandler = Callable[['Request', 'Response', BaseException, Dict[str, Any]], None]


class AsgiErrorHandler(Protocol):
    async def __call__(
        self,
        req: AsgiRequest,
        resp: Optional[AsgiResponse],
        error: BaseException,
        params: Dict[str, Any],
        *,
        ws: Optional[WebSocket] = ...,
    ) -> None: ...


# Error serializers
ErrorSerializer = Callable[['Request', 'Response', 'HTTPError'], None]

JSONSerializable = Union[
    Dict[str, 'JSONSerializable'],
    List['JSONSerializable'],
    Tuple['JSONSerializable', ...],
    bool,
    float,
    int,
    str,
    None,
]

# Sinks
SinkPrefix = Union[str, Pattern[str]]


class SinkCallable(Protocol):
    def __call__(self, req: Request, resp: Response, **kwargs: str) -> None: ...


class AsgiSinkCallable(Protocol):
    async def __call__(
        self, req: AsgiRequest, resp: AsgiResponse, **kwargs: str
    ) -> None: ...


# TODO(vytas): Is it possible to specify a Callable or a Protocol that defines
#   type hints for the two first parameters, but accepts any number of keyword
#   arguments afterwords?
# class SinkCallable(Protocol):
#     def __call__(sef, req: Request, resp: Response, <how to do?>): ...
Headers = Dict[str, str]
HeaderList = Union[Headers, List[Tuple[str, str]]]
ResponseStatus = Union[http.HTTPStatus, str, int]
StoreArgument = Optional[Dict[str, Any]]
Resource = object


class ResponderMethod(Protocol):
    def __call__(
        self,
        resource: Resource,
        req: Request,
        resp: Response,
        **kwargs: Any,
    ) -> None: ...


# WSGI
class ReadableIO(Protocol):
    def read(self, n: Optional[int] = ..., /) -> bytes: ...


ProcessRequestMethod = Callable[['Request', 'Response'], None]
ProcessResourceMethod = Callable[
    ['Request', 'Response', Resource, Dict[str, Any]], None
]
ProcessResponseMethod = Callable[['Request', 'Response', Resource, bool], None]


class ResponderCallable(Protocol):
    def __call__(self, req: Request, resp: Response, **kwargs: Any) -> None: ...


# ASGI
class AsyncReadableIO(Protocol):
    async def read(self, n: Optional[int] = ..., /) -> bytes: ...
    def __aiter__(self) -> AsyncIterator[bytes]: ...


class AsgiResponderMethod(Protocol):
    async def __call__(
        self,
        resource: Resource,
        req: AsgiRequest,
        resp: AsgiResponse,
        **kwargs: Any,
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


class AsgiResponderCallable(Protocol):
    async def __call__(
        self, req: AsgiRequest, resp: AsgiResponse, **kwargs: Any
    ) -> None: ...


class AsgiResponderWsCallable(Protocol):
    async def __call__(
        self, req: AsgiRequest, ws: WebSocket, **kwargs: Any
    ) -> None: ...


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
