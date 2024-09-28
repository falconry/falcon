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
"""Module that defines public Falcon type definitions."""

from __future__ import annotations

from typing import AsyncIterator, Dict, Optional, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from falcon.asgi import SSEvent

Headers = Dict[str, str]
"""Headers dictionary returned by the framework."""


# WSGI
class ReadableIO(Protocol):
    """File like protocol that defines only a read method."""

    def read(self, n: Optional[int] = ..., /) -> bytes: ...


# ASGI
class AsyncReadableIO(Protocol):
    """Async file-like protocol that defines only a read method, and is iterable."""

    async def read(self, n: Optional[int] = ..., /) -> bytes: ...
    def __aiter__(self) -> AsyncIterator[bytes]: ...


SSEEmitter = AsyncIterator[Optional['SSEvent']]
"""Async generator or iterator over Server-Sent Events
(instances of :class:`falcon.asgi.SSEvent`).
"""
