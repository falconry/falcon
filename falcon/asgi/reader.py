# WORK IN PROGRESS!!!

# Copyright 2019-2020 by Vytautas Liuolia.
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

"""Buffered ASGI stream reader."""

import io

from falcon.util.reader import DelimiterError

DEFAULT_CHUNK_SIZE = 8192
"""Default minimum chunk size for :class:`BufferedReader` (8 KiB)."""

_MAX_JOIN_CHUNKS = 1024


class BufferedReader:

    def __init__(self, source, chunk_size=None):
        self._source = self._iter_normalized(source)
        self._chunk_size = chunk_size or DEFAULT_CHUNK_SIZE
        self._max_join_size = self._chunk_size * _MAX_JOIN_CHUNKS

        self._buffer = b''
        self._consumed = 0
        self._exhausted = False

    async def _iter_normalized(self, source):
        chunk = b''
        chunk_size = self._chunk_size

        async for item in source:
            chunk_len = len(chunk)
            if chunk_len >= chunk_size:
                self._consumed += chunk_len
                yield chunk
                chunk = item
                continue

            chunk += item

        self._exhausted = True

        if chunk:
            self._consumed += len(chunk)
            yield chunk

    async def _iter_with_buffer(self):
        if self._buffer:
            output = self._buffer
            self._buffer = b''
            yield output

        async for chunk in self._source:
            yield chunk

    async def _iter_delimited(self, delimiter, source=None):
        delimiter_len_1 = len(delimiter) - 1
        if not 0 <= delimiter_len_1 < self._chunk_size:
            raise ValueError('delimiter length must be within [1, chunk_size]')

        if self._buffer:
            pos = self._buffer.find(delimiter)
            if pos >= 0:
                output = self._buffer[:pos]
                self._buffer = self._buffer[pos:]
                yield output
                return

        async for chunk in (source or self._source):
            offset = len(self._buffer) - delimiter_len_1
            if offset > 0:
                fragment = self._buffer[offset:] + chunk[:delimiter_len_1]
                pos = fragment.find(delimiter)
                if pos < 0:
                    output = self._buffer
                    self._buffer = chunk
                    yield output
                else:
                    output = self._buffer[:offset + pos]
                    self._buffer = self._buffer[offset + pos:] + chunk
                    yield output
                    return
            else:
                self._buffer += chunk

            pos = self._buffer.find(delimiter)
            if pos >= 0:
                output = self._buffer[:pos]
                self._buffer = self._buffer[pos:]
                yield output
                return

        yield self._buffer

    async def _consume_delimiter(self, delimiter):
        delimiter_len = len(delimiter)
        if await self.peek(delimiter_len) != delimiter:
            raise DelimiterError('expected delimiter missing')
        self._buffer = self._buffer[delimiter_len:]

    async def _read_from(self, source, size=-1):
        if size == -1 or size is None:
            result = io.BytesIO()
            async for chunk in source:
                result.write(chunk)
            return result.getvalue()

        if size <= 0:
            return b''

        remaining = size

        if size <= self._max_join_size:
            result = []
            async for chunk in source:
                chunk_len = len(chunk)
                if remaining < chunk_len:
                    result.append(chunk[:remaining])

                    current_buffer = self._buffer
                    self._buffer = chunk[remaining:]
                    if current_buffer:
                        self._buffer += current_buffer
                    break

                result.append(chunk)
                remaining -= chunk_len
                if remaining == 0:
                    break

            return b''.join(result)

        # NOTE(vytas): size > self._max_join_size
        result = io.BytesIO()
        async for chunk in source:
            chunk_len = len(chunk)
            if remaining < chunk_len:
                result.write(chunk[:remaining])

                current_buffer = self._buffer
                self._buffer = chunk[remaining:]
                if current_buffer:
                    self._buffer += current_buffer
                break

            result.write(chunk)
            remaining -= chunk_len
            if remaining == 0:
                break

        return result.getvalue()

    def delimit(self, delimiter):
        return type(self)(self._iter_delimited(delimiter),
                          chunk_size=self._chunk_size)

    # -------------------------------------------------------------------------
    # Asynchronous IO interface.
    # -------------------------------------------------------------------------

    def __aiter__(self):
        return self._source

    async def exhaust(self):
        await self.pipe()

    async def peek(self, size=-1):
        if size < 0 or size > self._chunk_size:
            size = self._chunk_size

        if len(self._buffer) < size:
            async for chunk in self._source:
                self._buffer += chunk
                if len(self._buffer) >= size:
                    break

        return self._buffer[:size]

    async def pipe(self, destination=None):
        async for chunk in self._iter_with_buffer():
            if destination is not None:
                await destination.write(chunk)

    async def pipe_until(self, delimiter, destination=None,
                         consume_delimiter=False):
        async for chunk in self._iter_delimited(delimiter):
            if destination is not None:
                await destination.write(chunk)

        if consume_delimiter:
            await self._consume_delimiter(delimiter)

    async def read(self, size=-1):
        return await self._read_from(self._iter_with_buffer(), size)

    async def readall(self):
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
        return await self._read_from(self._iter_with_buffer())

    async def read_until(self, delimiter, size=-1, consume_delimiter=False):
        result = await self._read_from(self._iter_delimited(delimiter), size)

        if consume_delimiter:
            await self._consume_delimiter(delimiter)

        return result

    # -------------------------------------------------------------------------
    # These methods are included to improve compatibility with Python's
    #   standard "file-like" IO interface.
    # -------------------------------------------------------------------------

    @property
    def eof(self):
        """Whether the stream is at EOF."""
        return self._exhausted and not self._buffer

    def fileno(self):
        """Raise an instance of OSError since a file descriptor is not used."""
        raise OSError('This IO object does not use a file descriptor')

    def isatty(self):
        """Always returns ``False``."""
        return False

    def readable(self):
        """Always returns ``True``."""
        return True

    def seekable(self):
        """Always returns ``False``."""
        return False

    def writable(self):
        """Always returns ``False``."""
        return False

    def tell(self):
        """Returns the number of bytes read from the stream so far."""
        return self._consumed - len(self._buffer)
