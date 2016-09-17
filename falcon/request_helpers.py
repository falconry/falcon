# Copyright 2013 by Rackspace Hosting, Inc.
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

"""Utilities for the Request class."""

import io


def header_property(wsgi_name):
    """Creates a read-only header property.

    Args:
        wsgi_name (str): Case-sensitive name of the header as it would
            appear in the WSGI environ ``dict`` (i.e., 'HTTP_*')

    Returns:
        A property instance than can be assigned to a class variable.

    """

    def fget(self):
        try:
            return self.env[wsgi_name] or None
        except KeyError:
            return None

    return property(fget)


class BoundedStream(io.IOBase):
    """Wrap *wsgi.input* streams to make them more robust.

    ``socket._fileobject`` and ``io.BufferedReader`` are sometimes used
    to implement *wsgi.input*. However, app developers are often burned
    by the fact that the `read()` method for these objects block
    indefinitely if either no size is passed, or a size greater than
    the request's content length is passed to the method.

    This class normalizes *wsgi.input* behavior between WSGI servers
    by implementing non-blocking behavior for the cases mentioned
    above.

    Args:
        stream: Instance of ``socket._fileobject`` from
            ``environ['wsgi.input']``
        stream_len: Expected content length of the stream.

    """

    def __init__(self, stream, stream_len):
        self.stream = stream
        self.stream_len = stream_len

        self._bytes_remaining = self.stream_len

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.stream)

    next = __next__

    def _read(self, size, target):
        """Helper function for proxing reads to the underlying stream.

        Args:
            size (int): Maximum number of bytes to read. Will be
                coerced, if None or -1, to the number of remaining bytes
                in the stream. Will likewise be coerced if greater than
                the number of remaining bytes, to avoid making a
                blocking call to the wrapped stream.
            target (callable): Once `size` has been fixed up, this function
                will be called to actually do the work.

        Returns:
            bytes: Data read from the stream, as returned by `target`.

        """

        # NOTE(kgriffs): Default to reading all remaining bytes if the
        # size is not specified or is out of bounds. This behaves
        # similarly to the IO streams passed in by non-wsgiref servers.
        if (size is None or size == -1 or size > self._bytes_remaining):
            size = self._bytes_remaining

        self._bytes_remaining -= size
        return target(size)

    def readable(self):
        """Always returns ``True``."""
        return True

    def seekable(self):
        """Always returns ``False``."""
        return False

    def writeable(self):
        """Always returns ``False``."""
        return False

    def read(self, size=None):
        """Read from the stream.

        Args:
            size (int): Maximum number of bytes/characters to read.
                Defaults to reading until EOF.

        Returns:
            bytes: Data read from the stream.

        """

        return self._read(size, self.stream.read)

    def readline(self, limit=None):
        """Read a line from the stream.

        Args:
            limit (int): Maximum number of bytes/characters to read.
                Defaults to reading until EOF.

        Returns:
            bytes: Data read from the stream.

        """

        return self._read(limit, self.stream.readline)

    def readlines(self, hint=None):
        """Read lines from the stream.

        Args:
            hint (int): Maximum number of bytes/characters to read.
                Defaults to reading until EOF.

        Returns:
            bytes: Data read from the stream.

        """

        return self._read(hint, self.stream.readlines)

    def write(self, data):
        """Always raises IOError; writing is not supported."""

        raise IOError('Stream is not writeable')


# NOTE(kgriffs): Alias for backwards-compat
Body = BoundedStream
