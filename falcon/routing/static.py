import io
import os
import re

import falcon


class StaticRoute(object):
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
    """

    # NOTE(kgriffs): Don't allow control characters and reserved chars
    _DISALLOWED_CHARS_PATTERN = re.compile('[\x00-\x1f\x80-\x9f~?<>:*|\'"]')

    # NOTE(kgriffs): If somehow an executable code exploit is triggerable, this
    # minimizes how much can be included in the payload.
    _MAX_NON_PREFIXED_LEN = 512

    def __init__(self, prefix, directory, downloadable=False):
        if not prefix.startswith('/'):
            raise ValueError("prefix must start with '/'")

        if not os.path.isabs(directory):
            raise ValueError('directory must be an absolute path')

        # NOTE(kgriffs): Ensure it ends with a path separator to ensure
        # we only match on the complete segment. Don't raise an error
        # because most people won't expect to have to append a slash.
        if not prefix.endswith('/'):
            prefix += '/'

        self._prefix = prefix
        self._directory = directory
        self._downloadable = downloadable

    def match(self, path):
        """Check whether the given path matches this route."""
        return path.startswith(self._prefix)

    def __call__(self, req, resp):
        """Resource responder for this route."""

        without_prefix = req.path[len(self._prefix):]

        # NOTE(kgriffs): Check surrounding whitespace and strip trailing
        # periods, which are illegal on windows
        if (not without_prefix or
                without_prefix.strip().rstrip('.') != without_prefix or
                self._DISALLOWED_CHARS_PATTERN.search(without_prefix) or
                '\\' in without_prefix or
                '//' in without_prefix or
                len(without_prefix) > self._MAX_NON_PREFIXED_LEN):

            raise falcon.HTTPNotFound()

        normalized = os.path.normpath(without_prefix)

        if normalized.startswith('../') or normalized.startswith('/'):
            raise falcon.HTTPNotFound()

        file_path = os.path.join(self._directory, normalized)

        # NOTE(kgriffs): Final sanity-check just to be safe. This check
        # should never succeed, but this should guard against us having
        # overlooked something.
        if '..' in file_path or not file_path.startswith(self._directory):
            raise falcon.HTTPNotFound()  # pragma: nocover

        try:
            resp.stream = io.open(file_path, 'rb')
        except IOError:
            raise falcon.HTTPNotFound()

        suffix = os.path.splitext(file_path)[1]
        resp.content_type = resp.options.static_media_types.get(
            suffix,
            'application/octet-stream'
        )

        if self._downloadable:
            resp.downloadable_as = os.path.basename(file_path)
