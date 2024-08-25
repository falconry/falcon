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

if TYPE_CHECKING:
    from falcon import asgi
    from falcon.asgi_spec import AsgiEvent
    from falcon.request import Request
    from falcon.response import Response


class _Missing(Enum):
    MISSING = auto()


_T = TypeVar('_T')
MISSING = _Missing.MISSING
MissingOr = Union[Literal[_Missing.MISSING], _T]

Link = Dict[str, str]

# Error handlers
ErrorHandler = Callable[['Request', 'Response', BaseException, dict], Any]

# Error serializers
ErrorSerializer = Callable[['Request', 'Response', BaseException], Any]

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
SinkPrefix = Union[str, Pattern]

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


class ReadableIO(Protocol):
    def read(self, n: Optional[int] = ..., /) -> bytes: ...


# ASGI
class AsyncReadableIO(Protocol):
    async def read(self, n: Optional[int] = ..., /) -> bytes: ...


class AsgiResponderMethod(Protocol):
    async def __call__(
        self,
        resource: Resource,
        req: asgi.Request,
        resp: asgi.Response,
        **kwargs: Any,
    ) -> None: ...


AsgiReceive = Callable[[], Awaitable['AsgiEvent']]

Responder = Union[ResponderMethod, AsgiResponderMethod]
