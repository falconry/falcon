from functools import partial
import io
import os
import re

import falcon
import falcon.stream
from falcon.util.sync import get_running_loop


def _open_range(file_path, req_range):
    """Open a file for a ranged request.

    Args:
        file_path (str): Path to the file to open.
        req_range (Optional[Tuple[int, int]]): Request.range value.
    Returns:
        tuple: Two-member tuple of (stream, content-range). If req_range is
            ``None`` or ignored, content-range will be ``None``; otherwise,
            the stream will be appropriately seeked and possibly bounded,
            and the content-range will be a tuple of (start, end, size).
    """
    fh = io.open(file_path, 'rb')
    if req_range is None:
        return fh, None

    start, end = req_range
    size = os.fstat(fh.fileno()).st_size
    if size == 0:
        # Ignore Range headers for zero-byte files; just serve the empty body
        # since Content-Range can't be used to express a zero-byte body
        return fh, None

    if start < 0 and end == -1:
        # Special case: only want the last N bytes
        start = max(start, -size)
        fh.seek(start, os.SEEK_END)
        return fh, (size + start, size - 1, size)

    if start >= size:
        raise falcon.HTTPRangeNotSatisfiable(size)

    fh.seek(start)
    if end == -1:
        return fh, (start, size - 1, size)

    end = min(end, size - 1)
    return falcon.stream.BoundedStream(fh, end - start + 1), (start, end, size)


class StaticRoute:
    """Represents a static route.

    Args:
        prefix (str): The path prefix to match for this route. If the
            path in the requested URI starts with this string, the remainder
            of the path will be appended to the source directory to
            determine the file to serve. This is done in a secure manner
            to prevent an attacker from requesting a file outside the
            specified directory.

            Note that static routes are matched in LIFO order, and are only
            attempted after checking dynamic routes and sinks.

        directory (str): The source directory from which to serve files. Must
            be an absolute path.
        downloadable (bool): Set to ``True`` to include a
            Content-Disposition header in the response. The "filename"
            directive is simply set to the name of the requested file.
        fallback_filename (str): Fallback filename used when the requested file
            is not found. Can be a relative path inside the prefix folder or
            any valid absolute path.

            Note:
                If the fallback file is served instead of the requested file,
                the response Content-Type header, as well as the
                Content-Disposition header (provided it was requested with the
                `downloadable` parameter described above), are derived from the
                fallback filename, as opposed to the requested filename.
    """

    # NOTE(kgriffs): Don't allow control characters and reserved chars
    _DISALLOWED_CHARS_PATTERN = re.compile('[\x00-\x1f\x80-\x9f\ufffd~?<>:*|\'"]')

    # NOTE(kgriffs): If somehow an executable code exploit is triggerable, this
    # minimizes how much can be included in the payload.
    _MAX_NON_PREFIXED_LEN = 512

    def __init__(self, prefix, directory, downloadable=False, fallback_filename=None):
        if not prefix.startswith('/'):
            raise ValueError("prefix must start with '/'")

        self._directory = os.path.normpath(directory)
        if not os.path.isabs(self._directory):
            raise ValueError('directory must be an absolute path')

        if fallback_filename is None:
            self._fallback_filename = None
        else:
            self._fallback_filename = os.path.normpath(
                os.path.join(self._directory, fallback_filename)
            )
            if not os.path.isfile(self._fallback_filename):
                raise ValueError('fallback_filename is not a file')

        # NOTE(kgriffs): Ensure it ends with a path separator to ensure
        # we only match on the complete segment. Don't raise an error
        # because most people won't expect to have to append a slash.
        if not prefix.endswith('/'):
            prefix += '/'

        self._prefix = prefix
        self._downloadable = downloadable

    def match(self, path):
        """Check whether the given path matches this route."""
        if self._fallback_filename is None:
            return path.startswith(self._prefix)
        return path.startswith(self._prefix) or path == self._prefix[:-1]

    def __call__(self, req, resp):
        """Resource responder for this route."""

        without_prefix = req.path[len(self._prefix) :]

        # NOTE(kgriffs): Check surrounding whitespace and strip trailing
        # periods, which are illegal on windows
        # NOTE(CaselIT): An empty filename is allowed when fallback_filename is provided
        if (
            not (without_prefix or self._fallback_filename is not None)
            or without_prefix.strip().rstrip('.') != without_prefix
            or self._DISALLOWED_CHARS_PATTERN.search(without_prefix)
            or '\\' in without_prefix
            or '//' in without_prefix
            or len(without_prefix) > self._MAX_NON_PREFIXED_LEN
        ):

            raise falcon.HTTPNotFound()

        normalized = os.path.normpath(without_prefix)

        if normalized.startswith('../') or normalized.startswith('/'):
            raise falcon.HTTPNotFound()

        file_path = os.path.join(self._directory, normalized)

        # NOTE(kgriffs): Final sanity-check just to be safe. This check
        # should never succeed, but this should guard against us having
        # overlooked something.
        if '..' in file_path or not file_path.startswith(self._directory):
            raise falcon.HTTPNotFound()

        req_range = req.range
        if req.range_unit != 'bytes':
            req_range = None
        try:
            resp.stream, content_range = _open_range(file_path, req_range)
        except IOError:
            if self._fallback_filename is None:
                raise falcon.HTTPNotFound()
            try:
                resp.stream, content_range = _open_range(self._fallback_filename, req_range)
                file_path = self._fallback_filename
            except IOError:
                raise falcon.HTTPNotFound()

        suffix = os.path.splitext(file_path)[1]
        resp.content_type = resp.options.static_media_types.get(
            suffix, 'application/octet-stream'
        )
        resp.accept_ranges = 'bytes'

        if self._downloadable:
            resp.downloadable_as = os.path.basename(file_path)
        if content_range:
            resp.status = falcon.HTTP_206
            resp.content_range = content_range


class StaticRouteAsync(StaticRoute):
    """Subclass of StaticRoute with modifications to support ASGI apps."""

    async def __call__(self, req, resp):
        super().__call__(req, resp)

        # NOTE(kgriffs): Fixup resp.stream so that it is non-blocking
        resp.stream = _AsyncFileReader(resp.stream)


class _AsyncFileReader:
    """Adapts a standard file I/O object so that reads are non-blocking."""

    def __init__(self, file):
        self._file = file
        self._loop = get_running_loop()

    async def read(self, size=-1):
        return await self._loop.run_in_executor(None, partial(self._file.read, size))
