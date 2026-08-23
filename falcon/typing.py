# Copyright 2024 by Federico Caselli
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
"""Public Falcon type alias definitions."""

from __future__ import annotations

from collections.abc import AsyncIterator
from collections.abc import Iterable
from typing import Any, Literal, Optional, Protocol, TYPE_CHECKING, TypedDict

try:
    from typing import NotRequired
except ImportError:  # pragma: no cover
    from typing_extensions import NotRequired

if TYPE_CHECKING:
    from falcon.asgi import SSEvent

__all__ = (
    'ASGIConnectionScope',
    'ASGIHTTPScope',
    'ASGILifespanScope',
    'ASGIScope',
    'ASGIVersions',
    'ASGIWebSocketScope',
    'Headers',
    'ReadableIO',
    'AsyncReadableIO',
    'SSEEmitter',
)

Headers = dict[str, str]
"""Mutable headers dictionary used by :class:`~falcon.Response` objects.

(Note that the :attr:`req.headers <falcon.Request.headers>` property is
annotated as a read-only mapping instead of this type.)

.. versionadded:: 4.0
"""


# ASGI
class ASGIVersions(TypedDict):
    """ASGI version information exposed in a scope's ``asgi`` field."""

    version: str
    spec_version: NotRequired[str]


class _ASGIConnectionScopeBase(TypedDict):
    asgi: ASGIVersions
    http_version: str
    path: str
    query_string: bytes
    headers: Iterable[tuple[bytes, bytes]]
    raw_path: NotRequired[bytes]
    root_path: NotRequired[str]
    scheme: NotRequired[str]
    client: NotRequired[tuple[str, int] | None]
    server: NotRequired[tuple[str, int | None] | None]
    state: NotRequired[dict[str, Any]]


class ASGIHTTPScope(_ASGIConnectionScopeBase):
    """ASGI HTTP connection scope."""

    type: Literal['http']
    method: str


class ASGIWebSocketScope(_ASGIConnectionScopeBase):
    """ASGI WebSocket connection scope."""

    type: Literal['websocket']
    subprotocols: NotRequired[Iterable[str]]


ASGIConnectionScope = ASGIHTTPScope | ASGIWebSocketScope
"""ASGI connection scope used by :class:`falcon.asgi.Request`.

This alias models the parts of the HTTP and WebSocket connection scope that
Falcon currently reads directly.
"""


class ASGILifespanScope(TypedDict):
    """ASGI lifespan scope."""

    type: Literal['lifespan']
    asgi: NotRequired[ASGIVersions]
    state: NotRequired[dict[str, Any]]


ASGIScope = ASGIConnectionScope | ASGILifespanScope
"""Top-level ASGI scope supported by :class:`falcon.asgi.App`."""


# WSGI
class ReadableIO(Protocol):
    """File-like protocol that defines only a read method.

    .. versionadded:: 4.0
    """

    def read(self, n: int | None = ..., /) -> bytes: ...


# ASGI
class AsyncReadableIO(Protocol):
    """Async file-like protocol that defines only a read method, and is iterable.

    .. versionadded:: 4.0
    """

    async def read(self, n: int | None = ..., /) -> bytes: ...
    def __aiter__(self) -> AsyncIterator[bytes]: ...


SSEEmitter = AsyncIterator[Optional['SSEvent']]
"""Async generator or iterator over Server-Sent Events
(instances of :class:`falcon.asgi.SSEvent`).

.. versionadded:: 4.0
"""
