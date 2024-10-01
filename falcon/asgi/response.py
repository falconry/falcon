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

"""ASGI Response class."""

from __future__ import annotations

from inspect import iscoroutine
from inspect import iscoroutinefunction
from typing import (
    AsyncIterator,
    Awaitable,
    Callable,
    List,
    Literal,
    Optional,
    Tuple,
    Union,
)

from falcon import response
from falcon._typing import _UNSET
from falcon._typing import ResponseCallbacks
from falcon.typing import AsyncReadableIO
from falcon.typing import SSEEmitter
from falcon.util.misc import _encode_items_to_latin1
from falcon.util.misc import is_python_func

__all__ = ('Response',)


class Response(response.Response):
    """Represents an HTTP response to a client request.

    Note:
        ``Response`` is not meant to be instantiated directly by responders.

    Keyword Arguments:
        options (dict): Set of global options passed from the App handler.
    """

    # PERF(kgriffs): These will be shadowed when set on an instance; let's
    #   us avoid having to implement __init__ and incur the overhead of
    #   an additional function call.
    _sse: Optional[SSEEmitter] = None
    _registered_callbacks: Optional[List[ResponseCallbacks]] = None

    stream: Union[AsyncReadableIO, AsyncIterator[bytes], None]  # type: ignore[assignment]
    """An async iterator or generator that yields a series of
    byte strings that will be streamed to the ASGI server as a
    series of "http.response.body" events. Falcon will assume the
    body is complete when the iterable is exhausted or as soon as it
    yields ``None`` rather than an instance of ``bytes``::

        async def producer():
            while True:
                data_chunk = await read_data()
                if not data_chunk:
                    break

                yield data_chunk

        resp.stream = producer

    Alternatively, a file-like object may be used as long as it
    implements an awaitable ``read()`` method::

        resp.stream = await aiofiles.open('resp_data.bin', 'rb')

    If the object assigned to :attr:`~.stream` holds any resources
    (such as a file handle) that must be explicitly released, the
    object must implement a ``close()`` method. The ``close()`` method
    will be called after exhausting the iterable or file-like object.

    Note:
        In order to be compatible with Python 3.7+ and PEP 479,
        async iterators must return ``None`` instead of raising
        :class:`StopIteration`. This requirement does not
        apply to async generators (PEP 525).

    Note:
        If the stream length is known in advance, you may wish to
        also set the Content-Length header on the response.
    """

    @property
    def sse(self) -> Optional[SSEEmitter]:
        """A Server-Sent Event (SSE) emitter, implemented as
        an async iterator or generator that yields a series of
        of :class:`falcon.asgi.SSEvent` instances. Each event will be
        serialized and sent to the client as HTML5 Server-Sent Events::

            async def emitter():
                while True:
                    some_event = await get_next_event()

                    if not some_event:
                        # Send an event consisting of a single "ping"
                        #   comment to keep the connection alive.
                        yield SSEvent()

                        # Alternatively, one can simply yield None and
                        #   a "ping" will also be sent as above.

                        # yield

                        continue

                    yield SSEvent(json=some_event, retry=5000)

                    # ...or

                    yield SSEvent(data=b'something', event_id=some_id)

                    # Alternatively, you may yield anything that implements
                    #   a serialize() method that returns a byte string
                    #   conforming to the SSE event stream format.

                    # yield some_event

            resp.sse = emitter()

        Note:
            When the `sse` property is set, it supersedes both the
            `text` and `data` properties.

        Note:
            When hosting an app that emits Server-Sent Events, the web
            server should be set with a relatively long keep-alive TTL to
            minimize the overhead of connection renegotiations.
        """  # noqa: D400 D205
        return self._sse

    @sse.setter
    def sse(self, value: Optional[SSEEmitter]) -> None:
        self._sse = value

    def set_stream(
        self,
        stream: Union[AsyncReadableIO, AsyncIterator[bytes]],  # type: ignore[override]
        content_length: int,
    ) -> None:
        """Set both `stream` and `content_length`.

        Although the :attr:`~falcon.asgi.Response.stream` and
        :attr:`~falcon.asgi.Response.content_length` properties may be set
        directly, using this method ensures
        :attr:`~falcon.asgi.Response.content_length` is not accidentally
        neglected when the length of the stream is known in advance. Using this
        method is also slightly more performant as compared to setting the
        properties individually.

        Note:
            If the stream length is unknown, you can set
            :attr:`~falcon.asgi.Response.stream` directly, and ignore
            :attr:`~falcon.asgi.Response.content_length`. In this case, the ASGI
            server may choose to use chunked encoding for HTTP/1.1

        Args:
            stream: A readable, awaitable file-like object or async iterable
                that returns byte strings. If the object implements a close()
                method, it will be called after reading all of the data.
            content_length (int): Length of the stream, used for the
                Content-Length header in the response.
        """

        self.stream = stream

        # PERF(kgriffs): Set directly rather than incur the overhead of
        #   the self.content_length property.
        self._headers['content-length'] = str(content_length)

    async def render_body(self) -> Optional[bytes]:  # type: ignore[override]
        """Get the raw bytestring content for the response body.

        This coroutine can be awaited to get the raw data for the
        HTTP response body, taking into account the :attr:`~.text`,
        :attr:`~.data`, and :attr:`~.media` attributes.

        Note:
            This method ignores :attr:`~.stream`; the caller must check
            and handle that attribute directly.

        Returns:
            bytes: The UTF-8 encoded value of the `text` attribute, if
            set. Otherwise, the value of the `data` attribute if set, or
            finally the serialized value of the `media` attribute. If
            none of these attributes are set, ``None`` is returned.
        """

        # NOTE(vytas): The code below is also inlined in asgi.App.__call__.

        data: Optional[bytes]
        text = self.text
        if text is None:
            data = self._data

            if data is None and self._media is not None:
                # NOTE(kgriffs): We use a special _UNSET singleton since
                #   None is ambiguous (the media handler might return None).
                if self._media_rendered is _UNSET:
                    if not self.content_type:
                        self.content_type = self.options.default_media_type

                    handler, serialize_sync, _ = self.options.media_handlers._resolve(
                        self.content_type, self.options.default_media_type
                    )

                    if serialize_sync:
                        self._media_rendered = serialize_sync(self._media)
                    else:
                        self._media_rendered = await handler.serialize_async(
                            self._media, self.content_type
                        )

                data = self._media_rendered
        else:
            try:
                # NOTE(kgriffs): Normally we expect text to be a string
                data = text.encode()
            except AttributeError:
                # NOTE(kgriffs): Assume it was a bytes object already
                data = text  # type: ignore[assignment]

        return data

    def schedule(self, callback: Callable[[], Awaitable[None]]) -> None:
        """Schedule an async callback to run soon after sending the HTTP response.

        This method can be used to execute a background job after the response
        has been returned to the client.

        The callback is assumed to be an async coroutine function. It will be
        scheduled to run on the event loop as soon as possible.

        The callback will be invoked without arguments. Use
        :any:`functools.partial` to pass arguments to the callback as needed.

        Note:
            If an unhandled exception is raised while processing the request,
            the callback will not be scheduled to run.

        Note:
            When an SSE emitter has been set on the response, the callback will
            be scheduled before the first call to the emitter.

        Warning:
            Because coroutines run on the main request thread, care should
            be taken to ensure they are non-blocking. Long-running operations
            must use async libraries or delegate to an
            :class:`~concurrent.futures.Executor` pool to avoid
            blocking the processing of subsequent requests.

        Args:
            callback(object): An async coroutine function. The callback will be
                invoked without arguments.
        """

        if not iscoroutinefunction(callback):
            if iscoroutine(callback):
                raise TypeError(
                    'The callback object appears to '
                    'be a coroutine, rather than a coroutine function. Please '
                    'pass the function itself, rather than the result obtained '
                    'by calling the function. '
                )
            elif is_python_func(callback):  # pragma: nocover
                raise TypeError('The callback must be a coroutine function.')

            # NOTE(kgriffs): The implicit "else" branch is actually covered
            #   by tests running in a Cython environment, but we can't
            #   detect it with the coverage tool.

        rc: Tuple[Callable[[], Awaitable[None]], Literal[True]] = (callback, True)

        if not self._registered_callbacks:
            self._registered_callbacks = [rc]
        else:
            self._registered_callbacks.append(rc)

    def schedule_sync(self, callback: Callable[[], None]) -> None:
        """Schedule a synchronous callback to run soon after sending the HTTP response.

        This method can be used to execute a background job after the
        response has been returned to the client.

        The callback is assumed to be a synchronous (non-coroutine) function.
        It will be scheduled on the event loop's default
        :class:`~concurrent.futures.Executor` (which can be overridden via
        :meth:`asyncio.AbstractEventLoop.set_default_executor`).

        The callback will be invoked without arguments. Use
        :any:`functools.partial` to pass arguments to the callback
        as needed.

        Note:
            If an unhandled exception is raised while processing the request,
            the callback will not be scheduled to run.

        Note:
            When an SSE emitter has been set on the response, the callback will
            be scheduled before the first call to the emitter.

        Warning:
            Synchronous callables run on the event loop's default
            :class:`~concurrent.futures.Executor`, which uses an instance of
            :class:`~concurrent.futures.ThreadPoolExecutor` unless
            :meth:`asyncio.AbstractEventLoop.set_default_executor` is used to
            change it to something else. Due to the GIL, CPU-bound jobs will
            block request processing for the current process unless the default
            :class:`~concurrent.futures.Executor` is changed to one that is
            process-based instead of thread-based (e.g., an instance of
            :class:`concurrent.futures.ProcessPoolExecutor`).

        Args:
            callback(object): An async coroutine function or a synchronous
                callable. The callback will be called without arguments.
        """

        rc: Tuple[Callable[[], None], Literal[False]] = (callback, False)

        if not self._registered_callbacks:
            self._registered_callbacks = [rc]
        else:
            self._registered_callbacks.append(rc)

    # ------------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------------

    def _asgi_headers(
        self, media_type: Optional[str] = None
    ) -> List[Tuple[bytes, bytes]]:
        """Convert headers into the format expected by ASGI servers.

        Header names must be lowercased and both name and value must be
        byte strings.

        See also: https://asgi.readthedocs.io/en/latest/specs/www.html#response-start

        Args:
            media_type: Default media type to use for the Content-Type
                header if the header was not set explicitly (default ``None``).

        """

        headers = self._headers
        # PERF(vytas): uglier inline version of Response._set_media_type
        if media_type is not None and 'content-type' not in headers:
            headers['content-type'] = media_type

        try:
            # NOTE(vytas): Supporting ISO-8859-1 for historical reasons as per
            #   RFC 7230, Section 3.2.4; and to strive for maximum
            #   compatibility with WSGI.

            # PERF(vytas): On CPython, _encode_items_to_latin1 is implemented
            #   in Cython (with a pure Python fallback), where the resulting
            #   C code speeds up the method substantially by directly invoking
            #   CPython's C API functions such as PyUnicode_EncodeLatin1.
            items = _encode_items_to_latin1(headers)
        except UnicodeEncodeError as ex:
            # TODO(vytas): In 3.1.0, update this error message to highlight the
            #   fact that we decided to allow ISO-8859-1?
            raise ValueError(
                'The modern series of HTTP standards require that header '
                f'names and values use only ASCII characters: {ex}'
            )

        if self._extra_headers:
            items += [
                (n.encode('ascii'), v.encode('ascii')) for n, v in self._extra_headers
            ]

        # NOTE(kgriffs): It is important to append these after self._extra_headers
        #   in case the latter contains Set-Cookie headers that should be
        #   overridden by a call to unset_cookie().
        if self._cookies is not None:
            # PERF(tbug):
            # The below implementation is ~23% faster than
            # the alternative:
            #
            #     self._cookies.output().split("\\r\\n")
            #
            # Even without the .split("\\r\\n"), the below
            # is still ~17% faster, so don't use .output()
            items += [
                (b'set-cookie', c.OutputString().encode('ascii'))
                for c in self._cookies.values()
            ]
        return items
