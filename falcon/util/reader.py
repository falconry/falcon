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

"""Buffered stream reader."""

import functools
import io

from falcon.errors import DelimiterError

DEFAULT_CHUNK_SIZE = 32768
"""Default chunk size for :class:`BufferedReader` (32 KiB)."""

_MAX_JOIN_CHUNKS = 128


class BufferedReader:
    def __init__(self, read, max_stream_len, chunk_size=None):
        self._read_func = read
        self._chunk_size = chunk_size or DEFAULT_CHUNK_SIZE
        self._max_join_size = self._chunk_size * _MAX_JOIN_CHUNKS

        self._buffer = b''
        self._buffer_len = 0
        self._buffer_pos = 0
        self._max_bytes_remaining = max_stream_len

    def _perform_read(self, size):
        # PERF(vytas): In Cython, bind types:
        #   cdef bytes chunk
        #   cdef Py_ssize_t chunk_len
        #   cdef result

        size = min(size, self._max_bytes_remaining)
        if size <= 0:
            return b''

        chunk = self._read_func(size)
        chunk_len = len(chunk)
        self._max_bytes_remaining -= chunk_len
        if chunk_len == size:
            return chunk

        if chunk_len == 0:
            # NOTE(vytas): The EOF.
            self._max_bytes_remaining = 0
            return b''

        result = io.BytesIO(chunk)
        result.seek(chunk_len)

        while True:
            size -= chunk_len
            if size <= 0:
                return result.getvalue()

            chunk = self._read_func(size)
            chunk_len = len(chunk)
            if chunk_len == 0:
                # NOTE(vytas): The EOF.
                self._max_bytes_remaining = 0
                return result.getvalue()

            self._max_bytes_remaining -= chunk_len
            result.write(chunk)

    def _fill_buffer(self):
        # PERF(vytas): In Cython, bind types:
        #   cdef Py_ssize_t read_size

        if self._buffer_len - self._buffer_pos < self._chunk_size:
            read_size = self._chunk_size - (self._buffer_len - self._buffer_pos)

            if self._buffer_pos == 0:
                self._buffer += self._perform_read(read_size)
            else:
                self._buffer = self._buffer[self._buffer_pos :] + self._perform_read(
                    read_size
                )
                self._buffer_pos = 0

            self._buffer_len = len(self._buffer)

    def peek(self, size=-1):
        if size < 0 or size > self._chunk_size:
            size = self._chunk_size

        if self._buffer_len - self._buffer_pos < size:
            self._fill_buffer()

        return self._buffer[self._buffer_pos : self._buffer_pos + size]

    def _normalize_size(self, size):
        # PERF(vytas): In Cython, bind types:
        #   cdef Py_ssize_t result
        #   cdef Py_ssize_t max_size

        max_size = self._max_bytes_remaining + self._buffer_len - self._buffer_pos

        if size is None or size == -1 or size > max_size:
            return max_size
        return size

    def read(self, size=-1):
        return self._read(self._normalize_size(size))

    def _read(self, size):
        # PERF(vytas): In Cython, bind types:
        #   cdef Py_ssize_t read_size
        #   cdef bytes result

        # NOTE(vytas): Dish directly from the buffer, if possible.
        if size <= self._buffer_len - self._buffer_pos:
            if size == self._buffer_len and self._buffer_pos == 0:
                result = self._buffer
                self._buffer_len = 0
                self._buffer = b''
                return result

            self._buffer_pos += size
            return self._buffer[self._buffer_pos - size : self._buffer_pos]

        # NOTE(vytas): Pass through large reads.
        if self._buffer_len == 0 and size >= self._chunk_size:
            return self._perform_read(size)

        # NOTE(vytas): if size > self._buffer_len - self._buffer_pos
        read_size = size - (self._buffer_len - self._buffer_pos)
        result = self._buffer[self._buffer_pos :]

        if read_size >= self._chunk_size:
            self._buffer_len = 0
            self._buffer_pos = 0
            self._buffer = b''
            return result + self._perform_read(read_size)

        self._buffer = self._perform_read(self._chunk_size)
        self._buffer_len = len(self._buffer)
        self._buffer_pos = read_size
        return result + self._buffer[:read_size]

    def read_until(self, delimiter, size=-1, consume_delimiter=False):
        # PERF(vytas): In Cython, bind types:
        #   cdef Py_ssize_t read_size
        #   cdef result

        read_size = self._normalize_size(size)
        if read_size <= self._max_join_size:
            return self._read_until(delimiter, read_size, consume_delimiter)

        # NOTE(vytas): A large size was requested, optimize for memory
        #   consumption by avoiding to momentarily keep both the chunks and the
        #   joint result in memory at the same time.
        result = io.BytesIO()
        self.pipe_until(delimiter, result, consume_delimiter, read_size)
        return result.getvalue()

    def _finalize_read_until(
        self,
        size,
        backlog,
        have_bytes,
        consume_bytes,
        delimiter=None,
        delimiter_pos=-1,
        next_chunk=None,
        next_chunk_len=0,
    ):

        if delimiter_pos < 0 and delimiter is not None:
            delimiter_pos = self._buffer.find(delimiter, self._buffer_pos)

        if delimiter_pos >= 0:
            size = min(size, have_bytes + delimiter_pos - self._buffer_pos)

        if have_bytes == 0:
            # PERF(vytas): Do not join bytes unless needed.
            ret_value = self._read(size)
        else:
            backlog.append(self._read(size - have_bytes))
            ret_value = b''.join(backlog)

        if next_chunk_len > 0:
            if self._buffer_len == 0:
                self._buffer = next_chunk
                self._buffer_len = next_chunk_len
            else:
                self._buffer = self._buffer[self._buffer_pos :] + next_chunk
                self._buffer_len = self._buffer_len - self._buffer_pos + next_chunk_len
                self._buffer_pos = 0

        if consume_bytes:
            if delimiter_pos < 0:
                if self.peek(consume_bytes) != delimiter:
                    raise DelimiterError('expected delimiter missing')
            elif self._buffer_pos != delimiter_pos:
                # NOTE(vytas): If we are going to consume the delimiter the
                #   quick way (i.e., skipping the above peek() check), we must
                #   make sure it is directly succeeding the result.
                raise DelimiterError('expected delimiter missing')

            self._buffer_pos += consume_bytes

        return ret_value

    def _read_until(self, delimiter, size, consume_delimiter):
        # PERF(vytas): In Cython, bind types:
        #   cdef list result = []
        #   cdef Py_ssize_t have_bytes = 0
        #   cdef Py_ssize_t delimiter_len_1 = len(delimiter) - 1
        #   cdef Py_ssize_t delimiter_pos = -1
        #   cdef Py_ssize_t consume_bytes
        #   cdef Py_ssize_t offset

        result = []
        have_bytes = 0
        delimiter_len_1 = len(delimiter) - 1
        delimiter_pos = -1
        consume_bytes = (delimiter_len_1 + 1) if consume_delimiter else 0

        if not 0 <= delimiter_len_1 < self._chunk_size:
            raise ValueError('delimiter length must be within [1, chunk_size]')

        # PERF(vytas): If the requested size is equal to the chunk size (or is
        #   a multiple of it), align the buffer.
        #   This can often nearly *double* the performance if one is reading in
        #   chunks.
        if size % self._chunk_size == 0:
            self._fill_buffer()

        while True:
            if self._buffer_len > self._buffer_pos:
                delimiter_pos = self._buffer.find(delimiter, self._buffer_pos)
                if delimiter_pos >= 0:
                    # NOTE(vytas): Delimiter was found in the current buffer.
                    #   We can now return to the caller.
                    return self._finalize_read_until(
                        size,
                        result,
                        have_bytes,
                        consume_bytes,
                        delimiter_pos=delimiter_pos,
                    )

            if size < (
                have_bytes + self._buffer_len - self._buffer_pos - delimiter_len_1
            ):
                # NOTE(vytas): We now have enough data in the buffer to return
                #   to the caller.
                return self._finalize_read_until(
                    size, result, have_bytes, consume_bytes, delimiter
                )

            next_chunk = self._perform_read(self._chunk_size)
            next_chunk_len = len(next_chunk)
            if self._max_bytes_remaining == 0:
                # NOTE(vytas): We have reached the EOF.
                self._buffer_len += next_chunk_len
                self._buffer += next_chunk
                return self._finalize_read_until(
                    size, result, have_bytes, consume_bytes, delimiter
                )

            # NOTE(vytas): The buffer was empty before, skip straight to the
            #   next chunk.
            if self._buffer_len <= self._buffer_pos:
                self._buffer_len = next_chunk_len
                self._buffer_pos = 0
                self._buffer = next_chunk
                continue

            # NOTE(vytas): We must check there is no delimiter in the chunk
            #   boundary before we can safely splice them.
            if delimiter_len_1 > 0:
                offset = max(self._buffer_len - delimiter_len_1, self._buffer_pos)
                fragment = self._buffer[offset:] + next_chunk[:delimiter_len_1]
                delimiter_pos = fragment.find(delimiter)
                if delimiter_pos >= 0:
                    self._buffer_len += next_chunk_len
                    self._buffer += next_chunk
                    return self._finalize_read_until(
                        size,
                        result,
                        have_bytes,
                        consume_bytes,
                        delimiter,
                        delimiter_pos + offset,
                    )

            if have_bytes + self._buffer_len - self._buffer_pos >= size:
                # NOTE(vytas): we have now verified that all bytes currently in
                #   the buffer are delimiter-free, including the border of the
                #   upcoming chunk
                return self._finalize_read_until(
                    size,
                    result,
                    have_bytes,
                    consume_bytes,
                    delimiter,
                    next_chunk=next_chunk,
                    next_chunk_len=next_chunk_len,
                )

            have_bytes += self._buffer_len - self._buffer_pos
            if self._buffer_pos > 0:
                result.append(self._buffer[self._buffer_pos :])
            else:
                result.append(self._buffer)
            self._buffer_len = next_chunk_len
            self._buffer_pos = 0
            self._buffer = next_chunk

    def pipe(self, destination=None):
        while True:
            chunk = self.read(self._chunk_size)
            if not chunk:
                break

            if destination is not None:
                destination.write(chunk)

    def pipe_until(
        self, delimiter, destination=None, consume_delimiter=False, _size=None
    ):
        # PERF(vytas): In Cython, bind types:
        #   cdef Py_ssize_t remaining

        remaining = self._normalize_size(_size)

        while remaining > 0:
            chunk = self._read_until(delimiter, min(self._chunk_size, remaining), False)
            if not chunk:
                break

            if destination is not None:
                destination.write(chunk)

            remaining -= self._chunk_size

        if consume_delimiter:
            delimiter_len = len(delimiter)
            if self.peek(delimiter_len) != delimiter:
                raise DelimiterError('expected delimiter missing')
            self._buffer_pos += delimiter_len

    def exhaust(self):
        self.pipe()

    def delimit(self, delimiter):
        read = functools.partial(self.read_until, delimiter)
        return type(self)(read, self._normalize_size(None), self._chunk_size)

    def readline(self, size=-1):
        size = self._normalize_size(size)

        result = self.read_until(b'\n', size)
        if len(result) < size:
            return result + self.read(1)
        return result

    def readlines(self, hint=-1):
        # PERF(vytas): In Cython, bind types:
        #   cdef Py_ssize_t read
        #   cdef list result = []
        read = 0
        result = []

        while True:
            line = self.readline()
            if not line:
                break
            result.append(line)

            if hint >= 0:
                read += len(line)
                if read >= hint:
                    break

        return result

    # --- implementing IOBase methods, the duck-typing way ---

    def readable(self):
        """Return ``True`` always."""
        return True

    def seekable(self):
        """Return ``False`` always."""
        return False

    def writeable(self):
        """Return ``False`` always."""
        return False
