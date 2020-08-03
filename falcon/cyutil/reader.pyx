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

"""Buffered stream reader (cythonized variant)."""

from libc.stdint cimport uint32_t

import functools
import io

from falcon.errors import DelimiterError
from falcon.util.reader import DEFAULT_CHUNK_SIZE, _MAX_JOIN_CHUNKS


cdef class BufferedReader:

    cdef _read_func
    cdef Py_ssize_t _chunk_size
    cdef Py_ssize_t _max_join_size

    cdef bytes _buffer
    cdef Py_ssize_t _buffer_len
    cdef Py_ssize_t _buffer_pos
    cdef Py_ssize_t _max_bytes_remaining

    def __cinit__(self, read, max_stream_len, chunk_size=None):
        self._read_func = read
        self._chunk_size = chunk_size or DEFAULT_CHUNK_SIZE
        self._max_join_size = self._chunk_size * _MAX_JOIN_CHUNKS

        self._buffer = b''
        self._buffer_len = 0
        self._buffer_pos = 0
        self._max_bytes_remaining = max_stream_len

    cdef bytes _perform_read(self, Py_ssize_t size):
        cdef bytes chunk
        cdef Py_ssize_t chunk_len
        cdef result

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

    cdef _fill_buffer(self):
        cdef Py_ssize_t read_size

        if self._buffer_len - self._buffer_pos < self._chunk_size:
            read_size = self._chunk_size - (self._buffer_len - self._buffer_pos)

            if self._buffer_pos == 0:
                self._buffer += self._perform_read(read_size)
            else:
                self._buffer = (self._buffer[self._buffer_pos:] +
                                self._perform_read(read_size))
                self._buffer_pos = 0

            self._buffer_len = len(self._buffer)

    def peek(self, Py_ssize_t size=-1):
        if size < 0 or size > self._chunk_size:
            size = self._chunk_size

        if self._buffer_len - self._buffer_pos < size:
            self._fill_buffer()

        return self._buffer[self._buffer_pos:self._buffer_pos + size]

    cdef Py_ssize_t _normalize_size(self, size):
        cdef Py_ssize_t result
        cdef Py_ssize_t max_size = (self._max_bytes_remaining + self._buffer_len -
                                    self._buffer_pos)

        if size is None:
            return max_size

        # PERF(vytas): Start operating on a Py_ssize_t as soon as the None case
        #   is ruled out.
        result = size

        if result == -1 or result > max_size:
            return max_size
        return result

    def read(self, size=-1):
        return self._read(self._normalize_size(size))

    cdef _read(self, Py_ssize_t size):
        cdef Py_ssize_t read_size
        cdef bytes result

        # NOTE(vytas): Dish directly from the buffer, if possible.
        if size <= self._buffer_len - self._buffer_pos:
            if size == self._buffer_len and self._buffer_pos == 0:
                result = self._buffer
                self._buffer_len = 0
                self._buffer = b''
                return result

            self._buffer_pos += size
            return self._buffer[self._buffer_pos - size:self._buffer_pos]

        # NOTE(vytas): Pass through large reads.
        if self._buffer_len == 0 and size >= self._chunk_size:
            return self._perform_read(size)

        # NOTE(vytas): if size > self._buffer_len - self._buffer_pos
        read_size = size - (self._buffer_len - self._buffer_pos)
        result = self._buffer[self._buffer_pos:]

        if read_size >= self._chunk_size:
            self._buffer_len = 0
            self._buffer_pos = 0
            self._buffer = b''
            return result + self._perform_read(read_size)

        self._buffer = self._perform_read(self._chunk_size)
        self._buffer_len = len(self._buffer)
        self._buffer_pos = read_size
        return result + self._buffer[:read_size]

    def read_until(self, bytes delimiter not None, size=-1,
                   consume_delimiter=False):
        cdef Py_ssize_t read_size = self._normalize_size(size)
        cdef result

        read_size = self._normalize_size(size)
        if read_size <= self._max_join_size:
            return self._read_until(delimiter, read_size, consume_delimiter)

        # NOTE(vytas): A large size was requested, optimize for memory
        #   consumption by avoiding to momentarily keep both the chunks and the
        #   joint result in memory at the same time.
        result = io.BytesIO()
        self.pipe_until(delimiter, result, consume_delimiter, read_size)
        return result.getvalue()

    cdef _finalize_read_until(
        self, Py_ssize_t size, backlog, Py_ssize_t have_bytes,
        Py_ssize_t consume_bytes, bytes delimiter=None,
        Py_ssize_t delimiter_pos=-1,
        bytes next_chunk=None, Py_ssize_t next_chunk_len=0):

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
                self._buffer = self._buffer[self._buffer_pos:] + next_chunk
                self._buffer_len = (self._buffer_len - self._buffer_pos +
                                    next_chunk_len)
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

    cdef _read_until(self, bytes delimiter, Py_ssize_t size,
                     bint consume_delimiter):
        cdef list result = []
        cdef Py_ssize_t have_bytes = 0
        cdef Py_ssize_t delimiter_len_1 = len(delimiter) - 1
        cdef Py_ssize_t delimiter_pos = -1
        cdef Py_ssize_t consume_bytes = (delimiter_len_1 + 1) if consume_delimiter else 0
        cdef Py_ssize_t offset

        if not 0 <= delimiter_len_1 < self._chunk_size:
            raise ValueError('delimiter length must be within [1, chunk_size]')

        # PERF(vytas): If the requested size is equal to the chunk size (or is
        #   a multiple of it), align the buffer.
        #   This can often nearly *double* the performance if one is reading in
        #   chunks.
        if size % self._chunk_size == 0:
            self._fill_buffer()

        # PERF(vytas): Quickly check for the first 4 delimiter bytes.
        cdef bint quick_found = True
        cdef uint32_t delimiter_head = 0
        cdef uint32_t current
        cdef Py_ssize_t index
        cdef const unsigned char* ptr
        if 3 <= delimiter_len_1 < 128:
            ptr = delimiter
            delimiter_head = (
                (ptr[0] << 24) | (ptr[1] << 16) | (ptr[2] << 8) | ptr[3])

        while True:
            if self._buffer_len > self._buffer_pos:
                delimiter_pos = self._buffer.find(delimiter, self._buffer_pos)
                if delimiter_pos >= 0:
                    # NOTE(vytas): Delimiter was found in the current buffer.
                    #   We can now return to the caller.
                    return self._finalize_read_until(
                        size, result, have_bytes, consume_bytes, None,
                        delimiter_pos)

            if size < (have_bytes + self._buffer_len - self._buffer_pos -
                       delimiter_len_1):
                # NOTE(vytas): We now have enough data in the buffer to return
                #   to the caller.
                return self._finalize_read_until(
                    size, result, have_bytes, consume_bytes, delimiter)

            next_chunk = self._perform_read(self._chunk_size)
            next_chunk_len = len(next_chunk)
            if self._max_bytes_remaining == 0:
                # NOTE(vytas): We have reached the EOF.
                self._buffer_len += next_chunk_len
                self._buffer += next_chunk
                return self._finalize_read_until(
                    size, result, have_bytes, consume_bytes, delimiter)

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
                offset = max(self._buffer_len - delimiter_len_1,
                             self._buffer_pos)

                # PERF(vytas): Quickly check for the first 4 delimiter bytes.
                #   This is pure Cython code with no counterpart in streams.py.
                if 3 <= delimiter_len_1 < 128:
                    quick_found = False
                    ptr = self._buffer
                    current = 0
                    for index in range(offset, self._buffer_len):
                        current <<= 8
                        current |= ptr[index]
                        if current == delimiter_head:
                            quick_found = True
                            break

                    if not quick_found:
                        ptr = next_chunk
                        for index in range(3):
                            current <<= 8
                            current |= ptr[index]
                            if current == delimiter_head:
                                quick_found = True
                                break

                if quick_found:
                    offset = max(self._buffer_len - delimiter_len_1,
                                 self._buffer_pos)
                    fragment = (self._buffer[offset:] +
                                next_chunk[:delimiter_len_1])
                    delimiter_pos = fragment.find(delimiter)
                    if delimiter_pos >= 0:
                        self._buffer_len += next_chunk_len
                        self._buffer += next_chunk
                        return self._finalize_read_until(
                            size, result, have_bytes, consume_bytes, delimiter,
                            delimiter_pos + offset)

            if have_bytes + self._buffer_len - self._buffer_pos >= size:
                # NOTE(vytas): we have now verified that all bytes currently in
                #   the buffer are delimiter-free, including the border of the
                #   upcoming chunk
                return self._finalize_read_until(
                    size, result, have_bytes, consume_bytes, delimiter, -1,
                    next_chunk, next_chunk_len)

            have_bytes += self._buffer_len - self._buffer_pos
            if self._buffer_pos > 0:
                result.append(self._buffer[self._buffer_pos:])
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

    def pipe_until(self, delimiter, destination=None, consume_delimiter=False,
                   _size=None):
        cdef Py_ssize_t remaining = self._normalize_size(_size)

        while remaining > 0:
            chunk = self._read_until(
                delimiter, min(self._chunk_size, remaining), False)
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
        cdef Py_ssize_t read = 0
        cdef list result = []

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
        """Always returns ``True``."""
        return True

    def seekable(self):
        """Always returns ``False``."""
        return False

    def writeable(self):
        """Always returns ``False``."""
        return False
