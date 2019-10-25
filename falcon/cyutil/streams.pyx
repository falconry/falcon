from libc.stdint cimport uint32_t

import functools
import io

DEFAULT_CHUNK_SIZE = io.DEFAULT_BUFFER_SIZE * 4


cdef class BufferedStream:

    cdef _read_func
    cdef Py_ssize_t _chunk_size

    cdef bytes _buffer
    cdef Py_ssize_t _buffer_len
    cdef Py_ssize_t _buffer_pos
    cdef Py_ssize_t _max_bytes_remaining

    def __cinit__(self, read, max_stream_len, chunk_size=None):
        self._read_func = read
        self._chunk_size = chunk_size or DEFAULT_CHUNK_SIZE

        self._buffer = b''
        self._buffer_len = 0
        self._buffer_pos = 0
        self._max_bytes_remaining = max_stream_len

    def peek(self, Py_ssize_t amount=-1):
        cdef Py_ssize_t read_amount

        amount = int(amount)
        if amount < 0 or amount > self._chunk_size:
            amount = self._chunk_size

        if self._buffer_len - self._buffer_pos < amount:
            read_amount = (self._chunk_size - self._buffer_len +
                           self._buffer_pos)
            if read_amount >= self._max_bytes_remaining:
                read_amount = self._max_bytes_remaining

            if self._buffer_pos == 0:
                self._buffer += self._read_func(read_amount)
                self._buffer_len = len(self._buffer)
            else:
                self._buffer = (self._buffer[self._buffer_pos:] +
                                self._read_func(read_amount))
                self._buffer_len = len(self._buffer)
                self._buffer_pos = 0
            self._max_bytes_remaining -= read_amount

        return self._buffer[self._buffer_pos:self._buffer_pos + amount]

    cdef Py_ssize_t _normalize_size(self, amount):
        cdef Py_ssize_t result
        cdef Py_ssize_t max_amount = self._max_bytes_remaining + self._buffer_len

        if amount is None or amount == -1:
            result = max_amount
        else:
            result = amount
            if result == -1 or result >= max_amount:
                result = max_amount

        return result

    def read(self, amount=-1):
        return self._read(self._normalize_size(amount))

    cdef _read(self, Py_ssize_t amount):
        cdef Py_ssize_t read_amount

        if self._buffer_len == 0:
            self._max_bytes_remaining -= amount
            return self._read_func(amount)

        if amount == self._buffer_len and self._buffer_pos == 0:
            result = self._buffer
            self._buffer_len = 0
            self._buffer = b''
            return result

        if amount < self._buffer_len - self._buffer_pos:
            self._buffer_pos += amount
            return self._buffer[self._buffer_pos - amount:self._buffer_pos]

        # NOTE(vytas): if amount > self._buffer_len - self._buffer_pos
        read_amount = amount - self._buffer_len + self._buffer_pos
        result = self._buffer[self._buffer_pos:]
        self._buffer_len = 0
        self._buffer_pos = 0
        self._buffer = b''
        self._max_bytes_remaining -= read_amount
        return result + self._read_func(read_amount)

    def read_until(self, bytes delimiter not None, amount=-1,
                   missing_delimiter_error=None):
        return self._read_until(delimiter, self._normalize_size(amount),
                                missing_delimiter_error)

    cdef _finalize_read_until(
        self, Py_ssize_t amount, backlog, Py_ssize_t have_bytes,
        bytes delimiter=None, Py_ssize_t delimiter_pos=-1, bytes
        next_chunk=None, Py_ssize_t next_chunk_len=0,
        missing_delimiter_error=None):

        if delimiter_pos < 0 and delimiter is not None:
            delimiter_pos = self._buffer.find(delimiter, self._buffer_pos)
            if delimiter_pos < 0 and missing_delimiter_error:
                raise missing_delimiter_error(
                    'unexpected EOF without delimiter')

        if delimiter_pos >= 0:
            amount = min(amount, have_bytes + delimiter_pos - self._buffer_pos)

        if have_bytes == 0:
            # PERF(vytas) Do not join bytes unless needed.
            ret_value = self._read(amount)
        else:
            backlog.append(self._read(amount - have_bytes))
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

        return ret_value

    cdef _read_until(self, bytes delimiter, Py_ssize_t amount,
                     missing_delimiter_error=None):
        cdef result = []
        cdef Py_ssize_t have_bytes = 0
        cdef Py_ssize_t delimiter_len_1 = len(delimiter) - 1
        cdef Py_ssize_t delimiter_pos = -1
        cdef Py_ssize_t offset

        if not 0 <= delimiter_len_1 < self._chunk_size:
            raise ValueError('delimiter length must be within [1, chunk_size]')

        # PERF(vytas) Quickly check for the first 4 delimiter bytes
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
                    return self._finalize_read_until(
                        amount, result, have_bytes, None, delimiter_pos)

            if amount < (have_bytes + self._buffer_len - self._buffer_pos -
                         delimiter_len_1):
                # NOTE(vytas) We now have enough data in the buffer to
                # return to the caller.
                return self._finalize_read_until(amount, result, have_bytes)

            read_amount = self._chunk_size
            if read_amount > self._max_bytes_remaining:
                read_amount = self._max_bytes_remaining
            if read_amount == 0:
                return self._finalize_read_until(
                    amount, result, have_bytes, delimiter, delimiter_pos, None,
                    -1, missing_delimiter_error)

            next_chunk = self._read_func(read_amount)
            next_chunk_len = len(next_chunk)
            self._max_bytes_remaining -= read_amount
            if next_chunk_len < self._chunk_size:
                self._buffer_len += next_chunk_len
                self._buffer += next_chunk
                return self._finalize_read_until(
                    amount, result, have_bytes, delimiter, -1, None, -1,
                    missing_delimiter_error)

            # NOTE(vytas) The buffer was empty before, skip straight to the
            #   next chunk.
            if self._buffer_len <= self._buffer_pos:
                self._buffer_len = next_chunk_len
                self._buffer_pos = 0
                self._buffer = next_chunk
                continue

            if delimiter_len_1 > 0:
                offset = max(self._buffer_len - delimiter_len_1,
                             self._buffer_pos)

                # PERF(vytas) Quickly check for the first 4 delimiter bytes.
                #   Here be dragons: Cython-only code!
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

                if quick_found or True:
                    offset = max(self._buffer_len - delimiter_len_1,
                                 self._buffer_pos)
                    fragment = (self._buffer[offset:] +
                                next_chunk[:delimiter_len_1])
                    delimiter_pos = fragment.find(delimiter)
                    if delimiter_pos >= 0:
                        self._buffer_len += next_chunk_len
                        self._buffer += next_chunk
                        return self._finalize_read_until(
                            amount, result, have_bytes, delimiter,
                            delimiter_pos + offset)

            if have_bytes + self._buffer_len - self._buffer_pos >= amount:
                # NOTE(vytas): we have now verified that all bytes currently in
                #   the buffer are delimiter-free, including the border of the
                #   upcoming chunk
                return self._finalize_read_until(
                    amount, result, have_bytes, None, -1, next_chunk,
                    next_chunk_len)

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

    def pipe_until(self, delimiter, destination=None):
        while True:
            chunk = self.read_until(delimiter, self._chunk_size)
            if not chunk:
                break

            if destination is not None:
                destination.write(chunk)

    def exhaust(self):
        self.pipe()

    def delimit(self, delimiter, missing_delimiter_error=None):
        read = functools.partial(
            self.read_until,
            delimiter,
            missing_delimiter_error=missing_delimiter_error)
        return type(self)(read, self._max_bytes_remaining + self._buffer_len,
                          self._chunk_size)

    def readline(self, size=-1):
        return self.read_until(b'\n', size) + self.read(1)

    def readlines(self, hint=-1):
        cdef Py_ssize_t read = 0
        cdef result = []

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
