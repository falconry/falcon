# Copyright 2020-2024 by Vytautas Liuolia.
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

from __future__ import annotations

import functools
import inspect
from typing import Any, Callable, Optional, TypeVar

from falcon.errors import UnsupportedError
from falcon.errors import UnsupportedScopeError


@functools.lru_cache(maxsize=16)
def _validate_asgi_scope(
    scope_type: str, spec_version: Optional[str], http_version: str
) -> str:
    if scope_type == 'http':
        spec_version = spec_version or '2.0'
        if not spec_version.startswith('2.'):
            raise UnsupportedScopeError(
                f'The ASGI "http" scope version {spec_version} is not supported.'
            )
        if http_version not in {'1.0', '1.1', '2', '3'}:
            raise UnsupportedError(
                f'The ASGI "http" scope does not support HTTP version {http_version}.'
            )
        return spec_version

    if scope_type == 'websocket':
        spec_version = spec_version or '2.0'
        if not spec_version.startswith('2.'):
            raise UnsupportedScopeError(
                'Only versions 2.x of the ASGI "websocket" scope are supported.'
            )
        if http_version not in {'1.1', '2', '3'}:
            raise UnsupportedError(
                'The ASGI "websocket" scope does not support '
                f'HTTP version {http_version}.'
            )
        return spec_version

    if scope_type == 'lifespan':
        spec_version = spec_version or '1.0'
        if not spec_version.startswith('1.') and not spec_version.startswith('2.'):
            raise UnsupportedScopeError(
                'Only versions 1.x and 2.x of the ASGI "lifespan" scope are supported.'
            )
        return spec_version

    # NOTE(kgriffs): According to the ASGI spec: "Applications should
    #   actively reject any protocol that they do not understand with
    #   an Exception (of any type)."
    raise UnsupportedScopeError(f'The ASGI "{scope_type}" scope type is not supported.')


_C = TypeVar('_C', bound=Callable[..., Any])


def _wrap_asgi_coroutine_func(asgi_impl: _C) -> _C:
    """Wrap an ASGI application in another coroutine.

    This utility is used to wrap the cythonized ``App.__call__`` in order to
    masquerade it as a pure-Python coroutine function.

    Conversely, if the ASGI callable is not detected as a coroutine function,
    the application server might incorrectly assume an ASGI 2.0 application
    (i.e., the double-callable style).

    In case the app class is not cythonized, this function is a simple
    passthrough of the original implementation.

    Args:
        asgi_impl(callable): An ASGI application class method.

    Returns:
        A pure-Python ``__call__`` implementation.
    """

    # NOTE(vytas): We are wrapping unbound class methods, hence the first
    #   "self" parameter.
    # NOTE(vytas): Intentionally not using functools.wraps as it erroneously
    #   inherits the cythonized method's traits.
    async def __call__(self: Any, scope: Any, receive: Any, send: Any) -> None:
        await asgi_impl(self, scope, receive, send)

    if inspect.iscoroutinefunction(asgi_impl):
        return asgi_impl

    return __call__  # type: ignore[return-value]
