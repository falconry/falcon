# Copyright 2020 by Vytautas Liuolia.
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

import inspect


def _wrap_asgi_coroutine_func(asgi_impl):
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
    async def wrapper(self, scope, receive, send):
        await asgi_impl(self, scope, receive, send)

    if inspect.iscoroutinefunction(asgi_impl):
        return asgi_impl

    return wrapper
