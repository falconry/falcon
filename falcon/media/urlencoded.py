from urllib.parse import urlencode

from falcon import errors
from falcon.media.base import BaseHandler
from falcon.util.uri import parse_query_string


class URLEncodedFormHandler(BaseHandler):
    """URL-encoded form data handler.

    This handler parses ``application/x-www-form-urlencoded`` HTML forms to a
    ``dict``, similar to how URL query parameters are parsed. An empty body
    will be parsed as an empty dict.

    When deserializing, this handler will raise :class:`falcon.MediaMalformedError`
    if the request payload cannot be parsed as ASCII or if any of the URL-encoded
    strings in the payload are not valid UTF-8.

    As documented for :any:`urllib.parse.urlencode`, when serializing, the
    media object must either be a ``dict`` or a sequence of two-element
    ``tuple``'s. If any values in the media object are sequences, each
    sequence element is converted to a separate parameter.

    Keyword Arguments:
        keep_blank (bool): Whether to keep empty-string values from the form
            when deserializing.
        csv (bool): Whether to split comma-separated form values into list
            when deserializing.
    """

    def __init__(self, keep_blank=True, csv=False):
        self._keep_blank = keep_blank
        self._csv = csv

        # NOTE(kgriffs): To be safe, only enable the optimized protocol when
        #   not subclassed.
        if type(self) is URLEncodedFormHandler:
            self._serialize_sync = self.serialize
            self._deserialize_sync = self._deserialize

    # NOTE(kgriffs): Make content_type a kwarg to support the
    #   Request.render_body() shortcut optimization.
    def serialize(self, media, content_type=None) -> bytes:
        # NOTE(vytas): Setting doseq to True to mirror the parse_query_string
        # behaviour.
        return urlencode(media, doseq=True).encode()

    def _deserialize(self, body):
        try:
            # NOTE(kgriffs): According to http://goo.gl/6rlcux the
            # body should be US-ASCII. Enforcing this also helps
            # catch malicious input.
            body = body.decode('ascii')
            return parse_query_string(body, keep_blank=self._keep_blank, csv=self._csv)
        except Exception as err:
            raise errors.MediaMalformedError('URL-encoded') from err

    def deserialize(self, stream, content_type, content_length):
        return self._deserialize(stream.read())

    async def deserialize_async(self, stream, content_type, content_length):
        return self._deserialize(await stream.read())
