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

"""ASGI BoundedStream class."""

from __future__ import annotations

from typing import AsyncIterator, NoReturn, Optional

from falcon._typing import AsgiReceive
from falcon.asgi_spec import AsgiEvent
from falcon.errors import OperationNotAllowed

__all__ = ('BoundedStream',)


class BoundedStream:
    """File-like input object for reading the body of the request, if any.

    This class implements coroutine functions for asynchronous reading or
    iteration, but otherwise provides an interface similar to that defined by
    :class:`io.IOBase`.

    If the request includes a Content-Length header, the number of bytes in the
    stream will be truncated to the length specified by the header. Otherwise,
    the stream will yield data until the ASGI server indicates that no more
    bytes are available.

    For large request bodies, the preferred method of using the stream object is
    as an asynchronous iterator. In this mode, each body chunk is simply yielded
    in its entirety, as it is received from the ASGI server. Because no data is
    buffered by the framework, this is the most memory-efficient way of reading
    the request body::

        # If the request body is empty or has already be consumed, the iteration
        #   will immediately stop without yielding any data chunks. Otherwise, a
        #   series of byte #   strings will be yielded until the entire request
        #   body has been yielded or the client disconnects.
        async for data_chunk in req.stream
            pass

    The stream object also supports asynchronous ``read()`` and
    ``readall()`` methods::

        # Read all of the data at once; use only when you are confident
        #   that the request body is small enough to not eat up all of
        #   your memory. For small bodies, this is the most performant
        #   option.
        data = await req.stream.readall()

        # ...or call read() without arguments
        data = await req.stream.read()

        # ...or read the data in chunks. You may choose to read more
        #   or less than 32 KiB as shown in this example. But note that
        #   this approach will generally be less efficient as compared
        #   to async iteration, resulting in more usage and
        #   copying of memory.
        while True:
            data_chunk = await req.stream.read(32 * 1024)
            if not data_chunk:
                break

    Warning:
        Apps may not use both ``read()`` and the asynchronous iterator
        interface to consume the same request body; the only time that
        it is safe to do so is when one or the other method is used to
        completely read the entire body *before* the other method is
        even attempted. Therefore, it is important to always call
        :meth:`~.exhaust` or :meth:`~.close` if a body has only been
        partially read and the remaining data is to be ignored.

    Note:
        The stream object provides a convenient abstraction over the series of
        body chunks contained in any ASGI "http.request" events received by the
        app. As such, some request body data may be temporarily buffered in
        memory during and between calls to read from the stream. The framework
        has been designed to minimize the amount of data that must be buffered
        in this manner.

    Args:
        receive (awaitable): ASGI awaitable callable that will yield a new
            request event dictionary when one is available.

    Keyword Args:
        first_event (dict): First ASGI event received from the client,
            if one was preloaded (default ``None``).
        content_length (int): Expected content length of the stream, derived
            from the Content-Length header in the request (if available).
    """

    __slots__ = (
        '_buffer',
        '_bytes_remaining',
        '_closed',
        '_iteration_started',
        '_pos',
        '_receive',
    )

    _buffer: bytes
    _bytes_remaining: int
    _closed: bool
    _iteration_started: bool
    _pos: int
    _receive: AsgiReceive

    def __init__(
        self,
        receive: AsgiReceive,
        first_event: Optional[AsgiEvent] = None,
        content_length: Optional[int] = None,
    ) -> None:
        self._closed = False
        self._iteration_started = False

        self._receive = receive

        # NOTE(kgriffs): Outside of testing, first_event will always be set
        #   and we also assume a body is expected, otherwise why bother
        #   creating a stream object to read it? But just in case this
        #   object is created in other cases, use "in" here rather than
        #   EAFP.
        if first_event and 'body' in first_event:
            first_chunk: bytes = first_event['body']
        else:
            first_chunk = b''

        if content_length is None:
            self._buffer = first_chunk

            # NOTE(kgriffs): If length is unknown we just set remaining bytes
            #   to a ridiculously high number so that we will keep reading
            #   until we get an event with more_body == False. We do not
            #   use sys.maxsize because 2**31 on 32-bit systems is not
            #   a large enough number (someone may have an API that accepts
            #   multi-GB payloads).
            self._bytes_remaining = 2**63
        else:
            if len(first_chunk) > content_length:
                self._buffer = first_chunk[:content_length]
            else:
                self._buffer = first_chunk

            self._bytes_remaining = content_length - len(self._buffer)

        self._pos = len(self._buffer)

        if first_event and self._bytes_remaining:
            # NOTE(kgriffs): Override if the event says there's no more data
            if not ('more_body' in first_event and first_event['more_body']):
                self._bytes_remaining = 0

    def __aiter__(self) -> AsyncIterator[bytes]:
        # NOTE(kgriffs): This returns an async generator, but that's OK because
        #   it also implements the iterator protocol defined in PEP 492, albeit
        #   in a more efficient way than a regular async iterator.
        return self._iter_content()

    # -------------------------------------------------------------------------
    # These methods are included to improve compatibility with Python's
    #   standard "file-like" IO interface.
    # -------------------------------------------------------------------------

    # NOTE(kgriffs): According to the Python docs, NotImplementedError is not
    #   meant to be used to mean "not supported"; rather, the method should
    #   just be left undefined; hence we do not implement readline(),
    #   readlines(), __iter__(), __next__(), flush(), seek(),
    #   truncate(), __del__().

    def fileno(self) -> NoReturn:
        """Raise an instance of OSError since a file descriptor is not used."""
        raise OSError('This IO object does not use a file descriptor')

    def isatty(self) -> bool:
        """Return ``False`` always."""
        return False

    def readable(self) -> bool:
        """Return ``True`` always."""
        return True

    def seekable(self) -> bool:
        """Return ``False`` always."""
        return False

    def writable(self) -> bool:
        """Return ``False`` always."""
        return False

    def tell(self) -> int:
        """Return the number of bytes read from the stream so far."""
        return self._pos

    @property
    def closed(self) -> bool:
        return self._closed

    # -------------------------------------------------------------------------

    @property
    def eof(self) -> bool:
        return not self._buffer and self._bytes_remaining == 0

    def close(self) -> None:
        """Clear any buffered data and close this stream.

        Once the stream is closed, any operation on it will
        raise an instance of :class:`ValueError`.

        As a convenience, it is allowed to call this method more than
        once; only the first call, however, will have an effect.
        """

        if not self._closed:
            self._buffer = b''
            self._bytes_remaining = 0

            self._closed = True

    async def exhaust(self) -> None:
        """Consume and immediately discard any remaining data in the stream."""

        if self._closed:
            raise ValueError(
                'This stream is closed; no further operations on it are permitted.'
            )

        self._buffer = b''

        while self._bytes_remaining > 0:
            event = await self._receive()

            if event['type'] == 'http.disconnect':
                self._bytes_remaining = 0
            else:
                try:
                    num_bytes = len(event['body'])
                except KeyError:
                    # NOTE(kgriffs): The ASGI spec states that 'body' is optional.
                    num_bytes = 0

                self._bytes_remaining -= num_bytes
                self._pos += num_bytes

                if not ('more_body' in event and event['more_body']):
                    self._bytes_remaining = 0

            # Immediately dereference the data so it can be discarded ASAP
            event = None  # type: ignore[assignment]

        # NOTE(kgriffs): Ensure that if we read more than expected, this
        #   value is normalized to zero.
        self._bytes_remaining = 0

    async def readall(self) -> bytes:
        """Read and return all remaining data in the request body.

        Warning:
            Only use this method when you can be certain that you have
            enough free memory for the entire request body, and that you
            have configured your web server to limit request bodies to a
            reasonable size (to guard against malicious requests).

        Returns:
            bytes: The request body data, or ``b''`` if the body is empty or
            has already been consumed.
        """

        if self._closed:
            raise OperationNotAllowed(
                'This stream is closed; no further operations on it are permitted.'
            )

        if self.eof:
            return b''

        if self._buffer:
            next_chunk = self._buffer
            self._buffer = b''
            chunks = [next_chunk]
        else:
            chunks = []

        while self._bytes_remaining > 0:
            event = await self._receive()

            # PERF(kgriffs): Use try..except because we normally expect the
            #   'body' key to be present.
            try:
                next_chunk = event['body']
            except KeyError:
                pass
            else:
                next_chunk_len = len(next_chunk)

                if next_chunk_len <= self._bytes_remaining:
                    chunks.append(next_chunk)
                    self._bytes_remaining -= next_chunk_len
                else:
                    # NOTE(kgriffs): Do not read more data than we are
                    #   expecting. This *should* never happen if the
                    #   server enforces the content-length header, but
                    #   it is better to be safe than sorry.
                    chunks.append(next_chunk[: self._bytes_remaining])
                    self._bytes_remaining = 0

            # NOTE(kgriffs): This also handles the case of receiving
            #   the event: {'type': 'http.disconnect'}
            if not ('more_body' in event and event['more_body']):
                self._bytes_remaining = 0

        data = chunks[0] if len(chunks) == 1 else b''.join(chunks)
        self._pos += len(data)

        return data

    async def read(self, size: Optional[int] = None) -> bytes:
        """Read some or all of the remaining bytes in the request body.

        Warning:
            A size should always be specified, unless you can be certain that
            you have enough free memory for the entire request body, and that
            you have configured your web server to limit request bodies to a
            reasonable size (to guard against malicious requests).

        Warning:
            Apps may not use both ``read()`` and the asynchronous iterator
            interface to consume the same request body; the only time that
            it is safe to do so is when one or the other method is used to
            completely read the entire body *before* the other method is
            even attempted. Therefore, it is important to always call
            :meth:`~.exhaust` or :meth:`~.close` if a body has only been
            partially read and the remaining data is to be ignored.

        Keyword Args:
            size (int): The maximum number of bytes to read. The actual
                amount of data that can be read will depend on how much is
                available, and may be smaller than the amount requested. If the
                size is -1 or not specified, all remaining data is read and
                returned.

        Returns:
            bytes: The request body data, or ``b''`` if the body is empty or
            has already been consumed.
        """

        if self._closed:
            raise OperationNotAllowed(
                'This stream is closed; no further operations on it are permitted.'
            )

        if self.eof:
            return b''

        if size is None or size == -1:
            return await self.readall()

        if size <= 0:
            return b''

        if self._buffer:
            num_bytes_available = len(self._buffer)
            chunks = [self._buffer]
        else:
            num_bytes_available = 0
            chunks = []

        while self._bytes_remaining > 0 and num_bytes_available < size:
            event = await self._receive()

            # PERF(kgriffs): Use try..except because we normally expect the
            #   'body' key to be present.
            try:
                next_chunk = event['body']
            except KeyError:
                pass
            else:
                next_chunk_len = len(next_chunk)

                if next_chunk_len <= self._bytes_remaining:
                    chunks.append(next_chunk)
                    self._bytes_remaining -= next_chunk_len
                    num_bytes_available += next_chunk_len
                else:
                    # NOTE(kgriffs): Do not read more data than we are
                    #   expecting. This *should* never happen, but better
                    #   safe than sorry.
                    chunks.append(next_chunk[: self._bytes_remaining])
                    self._bytes_remaining = 0
                    num_bytes_available += self._bytes_remaining

            # NOTE(kgriffs): This also handles the case of receiving
            #   the event: {'type': 'http.disconnect'}
            if not ('more_body' in event and event['more_body']):
                self._bytes_remaining = 0

        self._buffer = chunks[0] if len(chunks) == 1 else b''.join(chunks)

        if num_bytes_available <= size:
            data = self._buffer
            self._buffer = b''
        else:
            data = self._buffer[:size]
            self._buffer = self._buffer[size:]

        self._pos += len(data)

        return data

    async def _iter_content(self) -> AsyncIterator[bytes]:
        if self._closed:
            raise OperationNotAllowed(
                'This stream is closed; no further operations on it are permitted.'
            )

        if self.eof:
            return

        if self._iteration_started:
            raise OperationNotAllowed('This stream is already being iterated over.')

        self._iteration_started = True

        if self._buffer:
            next_chunk = self._buffer
            self._buffer = b''

            self._pos += len(next_chunk)
            yield next_chunk

        while self._bytes_remaining > 0:
            event = await self._receive()

            # PERF(kgriffs): Use try...except because we normally expect the
            #   'body' key to be present.
            try:
                next_chunk = event['body']
            except KeyError:
                pass
            else:
                # NOTE(kgriffs): No need to yield empty body chunks.
                if next_chunk:
                    next_chunk_len = len(next_chunk)

                    if next_chunk_len <= self._bytes_remaining:
                        self._bytes_remaining -= next_chunk_len
                        self._pos += next_chunk_len
                    else:
                        # NOTE(kgriffs): We received more data than expected,
                        #   so truncate to the expected length.
                        next_chunk = next_chunk[: self._bytes_remaining]
                        self._pos += self._bytes_remaining
                        self._bytes_remaining = 0

                    yield next_chunk

            # NOTE(kgriffs): Per the ASGI spec, more_body is optional
            #   and should be considered False if not present.
            # NOTE(kgriffs): This also handles the case of receiving
            #   the event: {'type': 'http.disconnect'}
            # PERF(kgriffs): event.get() is more elegant, but uses a
            #   few more CPU cycles.
            if not ('more_body' in event and event['more_body']):
                self._bytes_remaining = 0
