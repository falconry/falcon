from libc.stdint cimport uint32_t

import functools
import io

DEFAULT_CHUNK_SIZE = io.DEFAULT_BUFFER_SIZE * 4


cdef class BufferedStream:

    cdef _read
    cdef Py_ssize_t _chunk_size

    cdef bytes _buffer
    cdef Py_ssize_t _buffer_len
    cdef Py_ssize_t _max_bytes_remaining

    def __cinit__(self, read, max_stream_len, chunk_size=None):
        self._read = read
        self._chunk_size = chunk_size or DEFAULT_CHUNK_SIZE

        self._buffer = b''
        self._buffer_len = 0
        self._max_bytes_remaining = max_stream_len

    def peek(self, Py_ssize_t amount=-1):
        cdef Py_ssize_t read_amount

        if amount < 0 or amount > self._chunk_size:
            amount = self._chunk_size

        if self._buffer_len < amount:
            read_amount = self._chunk_size - self._buffer_len
            if read_amount >= self._max_bytes_remaining:
                read_amount = self._max_bytes_remaining

            self._max_bytes_remaining -= read_amount
            self._buffer += self._read(read_amount)
            self._buffer_len = len(self._buffer)

        return self._buffer[:amount]

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
        return self._cy_read(self._normalize_size(amount))

    cdef _cy_read(self, Py_ssize_t amount):
        cdef Py_ssize_t read_amount

        if self._buffer_len == 0:
            self._max_bytes_remaining -= amount
            return self._read(amount)

        if amount == self._buffer_len:
            result = self._buffer
            self._buffer_len = 0
            self._buffer = b''
            return result

        if amount < self._buffer_len:
            result = self._buffer[:amount]
            self._buffer_len -= amount
            self._buffer = self._buffer[amount:]
            return result

        # NOTE(vytas): if amount > self._buffer_len
        read_amount = amount - self._buffer_len
        result = self._buffer
        self._buffer_len = 0
        self._buffer = b''
        self._max_bytes_remaining -= read_amount
        return result + self._read(read_amount)

    def read_until(self, bytes delimiter not None, amount=-1,
                   missing_delimiter_error=None):
        return self._read_until(delimiter, self._normalize_size(amount),
                                missing_delimiter_error)

    cdef _read_until(self, bytes delimiter, Py_ssize_t amount,
                     missing_delimiter_error=None):
        cdef result = []
        cdef bint result_is_empty = True
        cdef Py_ssize_t have_bytes = 0
        cdef Py_ssize_t buffer_cutoff
        cdef Py_ssize_t delimiter_len_1 = len(delimiter) - 1

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
            if delimiter in self._buffer:
                break

            read_amount = self._chunk_size
            if read_amount > self._max_bytes_remaining:
                read_amount = self._max_bytes_remaining
            if read_amount == 0:
                break
            self._max_bytes_remaining -= read_amount
            next_chunk = self._read(read_amount)
            next_chunk_len = len(next_chunk)
            if self._buffer_len == 0:
                self._buffer_len = next_chunk_len
                self._buffer = next_chunk
                continue
            if next_chunk_len < self._chunk_size:
                self._buffer_len += next_chunk_len
                self._buffer += next_chunk
                break

            if delimiter_len_1 > 0:
                # PERF(vytas) Quickly check for the first 4 delimiter bytes
                if 3 <= delimiter_len_1 < 128:
                    quick_found = False
                    ptr = self._buffer
                    current = 0
                    for index in range(self._buffer_len - delimiter_len_1,
                                       self._buffer_len):
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
                    if delimiter in (self._buffer[-delimiter_len_1:] +
                                     next_chunk[:delimiter_len_1]):
                        self._buffer_len += next_chunk_len
                        self._buffer += next_chunk
                        break

            have_bytes += self._buffer_len

            if have_bytes >= amount:
                if result_is_empty:
                    if have_bytes == amount:
                        self._buffer_len = next_chunk_len
                        self._buffer = next_chunk
                        return self._buffer

                    ret_value = self._buffer[:amount]
                    self._buffer_len = have_bytes - amount + next_chunk_len
                    self._buffer = self._buffer[amount:] + next_chunk
                    return ret_value

                buffer_cutoff = self._buffer_len - have_bytes + amount
                result.append(self._buffer[:buffer_cutoff])
                self._buffer_len = have_bytes - amount + next_chunk_len
                self._buffer = self._buffer[buffer_cutoff:] + next_chunk
                return b''.join(result)

            result.append(self._buffer)
            result_is_empty = False
            self._buffer_len = next_chunk_len
            self._buffer = next_chunk

        data, found_delimiter, remainder = self._buffer.partition(delimiter)
        if not found_delimiter:
            if missing_delimiter_error:
                raise missing_delimiter_error(
                    'unexpected EOF without delimiter')

        result.append(data[:amount - have_bytes])
        self._buffer = data[amount - have_bytes:] + found_delimiter + remainder
        self._buffer_len = len(self._buffer)
        return b''.join(result)

    def pipe(self, destination=None):
        cdef bint destination_is_not_none = (destination is not None)

        while True:
            chunk = self.read(self._chunk_size)
            if not chunk:
                break

            if destination_is_not_none:
                destination.write(chunk)

    def pipe_until(self, delimiter, destination=None):
        cdef bint destination_is_not_none = (destination is not None)

        while True:
            chunk = self.read_until(delimiter, self._chunk_size)
            if not chunk:
                break

            if destination_is_not_none:
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
