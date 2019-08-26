import cgi

from falcon import errors
from falcon import request_helpers
from falcon.media.base import BaseHandler
from falcon.media.handlers import Handlers
from falcon.util import BufferedStream


_ALLOWED_CONTENT_HEADERS = frozenset([
    b'content-type',
    b'content-disposition',
    b'content-transfer-encoding',
])

DEFAULT_SUPPORTED_CHARSETS = (
    'utf-8',
    'ibm866',
    'iso-8859-2',
    'iso-8859-3',
    'iso-8859-4',
    'iso-8859-5',
    'iso-8859-6',
    'iso-8859-7',
    'iso-8859-8',
    'iso-8859-10',
    'iso-8859-13',
    'iso-8859-14',
    'iso-8859-15',
    'iso-8859-16',
    'koi8-r',
    'koi8-u',
    'macintosh',
    'windows-1250',
    'windows-1251',
    'windows-1252',
    'windows-1253',
    'windows-1254',
    'windows-1255',
    'windows-1256',
    'windows-1257',
    'windows-1258',
)


class MultipartParseError(errors.HTTPBadRequest):

    def __init__(self, description=None, headers=None, **kwargs):
        super().__init__('Malformed multipart/form-data request media',
                         description, headers, **kwargs)


# TODO(vytas): Consider supporting -charset- stuff.
#   Does anyone use that (?)
class BodyPart:
    """
    Represents a body part in a multipart form.

    Note:
        `BodyPart` is meant to be instantiated directly only by the
        `MultipartForm` parser.

    Attributes:
        content_type (str): Value of the Content-Type header, or the multipart
            form default ``text/plain`` if the header is missing.
        stream: File-like input object for reading the body part of the
            multipart form request, if any. This object provides direct access
            to the server's data stream and is non-seekable. The stream is
            automatically delimited according to the multipart stream boundary.
        media (object): Returns a deserialized form of the multipart body part.
            When called, it will attempt to deserialize the body part stream
            using the Content-Type header as well as the media-type handlers
            configured via
            :class:`falcon.media.multipart.MultipartParseOptions`.

    """

    _content_disposition = None
    _data = None
    _filename = None
    _media = None
    _name = None

    def __init__(self, stream, headers, parse_options):
        self.stream = stream
        self._headers = headers
        self._parse_options = parse_options

    @property
    def data(self):
        if self._data is None:
            max_size = self._parse_options.max_body_part_buffer_size + 1
            self._data = self.stream.read(max_size)
            if len(self._data) >= max_size:
                raise MultipartParseError('body part is too large')

        return self._data

    @property
    def text(self):
        content_type, options = cgi.parse_header(self.content_type)
        if content_type != 'text/plain':
            return None

        charset = options.get('charset') or self._parse_options.default_charset
        assert charset in self._parse_options.supported_charsets
        return self.data.decode(charset)

    @property
    def content_type(self):
        # NOTE(vytas): RFC 7578, section 4.4.
        #   Each part MAY have an (optional) "Content-Type" header field, which
        #   defaults to "text/plain".
        value = self._headers.get(b'content-type') or b'text/plain'
        return value.decode('ascii')

    @property
    def filename(self):
        if self._filename is None:

            if self._content_disposition is None:
                value = self._headers.get(b'content-disposition', b'')
                self._content_disposition = cgi.parse_header(value.decode())

            _, params = self._content_disposition
            value = params.get('filename')
            # TODO(vytas): Consider supporting filename* as that has been
            #   spotted in the wild, even though RFC 7578 forbids it.
            if value is None:
                return None
            self._filename = value

        return self._filename

    @property
    def name(self):
        if self._name is None:

            if self._content_disposition is None:
                value = self._headers.get(b'content-disposition', b'')
                self._content_disposition = cgi.parse_header(value.decode())

            _, params = self._content_disposition
            self._name = params.get('name')

        return self._name

    @property
    def media(self):
        if self._media is None:
            handler = self._parse_options.media_handlers.find_by_media_type(
                self.content_type, 'text/plain')
            self._media = handler.deserialize(
                self.stream, self.content_type, None)

        return self._media


class MultipartForm:

    def __init__(self, stream, boundary, content_length, parse_options):
        # if not isinstance(stream, BufferedStream):
        if not hasattr(stream, 'read_until'):
            if isinstance(stream, request_helpers.BoundedStream):
                stream = BufferedStream(stream.stream.read, content_length)
            else:
                stream = BufferedStream(stream.read, content_length)

        self._stream = stream
        self._boundary = boundary
        self._dash_boundary = b'--' + boundary
        self._parse_options = parse_options

    def __iter__(self):
        delimiter = self._dash_boundary
        stream = self._stream
        max_headers_size = self._parse_options.max_body_part_headers_size
        remaining_part_count = self._parse_options.max_body_part_count

        while True:
            # NOTE(vytas): Either exhaust the unused stream part, or skip
            #   the prologue.
            stream.pipe_until(delimiter)
            stream.read(len(delimiter))

            if not delimiter.startswith(b'\r\n'):
                delimiter = b'\r\n' + delimiter

            separator = stream.read_until(b'\r\n', 2, MultipartParseError)
            if separator == b'--':
                if stream.peek(2) != b'\r\n':
                    raise MultipartParseError('unexpected form epilogue')
                break
            elif separator:
                raise MultipartParseError('unexpected form structure')

            headers = {}
            headers_block = stream.read_until(b'\r\n\r\n', max_headers_size,
                                              MultipartParseError)
            stream.read(4)

            for line in headers_block.split(b'\r\n'):
                name, sep, value = line.partition(b': ')
                if sep:
                    name = name.lower()

                    # NOTE(vytas): RFC 7578, section 4.5.
                    #   This use is deprecated for use in contexts that support
                    #   binary data such as HTTP. Senders SHOULD NOT generate
                    #   any parts with a Content-Transfer-Encoding header
                    #   field.
                    #
                    #   Currently, no deployed implementations that send such
                    #   bodies have been discovered.
                    if name == b'content-transfer-encoding':
                        raise MultipartParseError(
                            'the deprecated Content-Transfer-Encoding header '
                            'field is unsupported')
                    # NOTE(vytas): RFC 7578, section 4.8.
                    #   Other header fields MUST NOT be included and MUST be
                    #   ignored.
                    elif name in _ALLOWED_CONTENT_HEADERS:
                        headers[name] = value

            remaining_part_count -= 1
            if remaining_part_count == 0:
                raise MultipartParseError(
                    'maximum number of form body parts exceeded')

            yield BodyPart(stream.delimit(delimiter, MultipartParseError),
                           headers, self._parse_options)

        stream.exhaust()


class MultipartFormHandler(BaseHandler):
    """
    Multipart form (content type ``multipart/form-data``) media handler.

    The ``multipart/form-data`` media type for HTML5 forms is defined in the
    `RFC 7578 <https://tools.ietf.org/html/rfc7578>`_.

    The multipart media type itself is defined in the
    `RFC 2046 section 5.1 <https://tools.ietf.org/html/rfc2046#section-5.1>`_.

    .. note::
       Note that unlike many others, this handler does not consume the stream
       immediately. Rather, the serialized media object shall be iterated to
       parse the body parts.
    """

    def __init__(self, parse_options=None):
        self.parse_options = parse_options or MultipartParseOptions()

    def deserialize(self, stream, content_type, content_length):
        _, options = cgi.parse_header(content_type)
        boundary = options.get('boundary')
        if boundary is None:
            raise errors.HTTPInvalidHeader(
                'No boundary specifier found in {!r}'.format(content_type),
                'Content-Type')

        # NOTE(vytas): RFC 2046, section 5.1.
        #   If a boundary delimiter line appears to end with white space, the
        #   white space must be presumed to have been added by a gateway, and
        #   must be deleted.
        boundary = boundary.rstrip()

        # NOTE(vytas): RFC 2046, section 5.1.
        #   The boundary parameter consists of 1 to 70 characters from a set of
        #   characters known to be very robust through mail gateways, and NOT
        #   ending with white space.
        if not 1 <= len(boundary) <= 70:
            raise errors.HTTPInvalidHeader(
                'The boundary parameter must consist of 1 to 70 characters',
                'Content-Type')

        return MultipartForm(stream, boundary.encode(), content_length,
                             self.parse_options)

    def serialize(self, media, content_type):
        raise NotImplementedError('multipart form serialization unsupported')


# PERF: To avoid typos and improve storage space and speed over a dict.
class MultipartParseOptions:
    """
    Defines a set of configurable multipart form parse options.

    Attributes:
        max_body_part_count (int): The maximum amount of body part counts.
        media_handlers (Handlers): A dict-like object that allows you to
            configure the media-types that you would like to handle.
            By default, a handler is provided for the ``application/json``
            media type.
    """

    __slots__ = (
        'default_charset',
        'max_body_part_buffer_size',
        'max_body_part_count',
        'max_body_part_headers_size',
        'media_handlers',
        'supported_charsets',
    )

    def __init__(self):
        self.default_charset = 'utf-8'
        self.max_body_part_buffer_size = 1024 * 1024
        self.max_body_part_count = 64
        self.max_body_part_headers_size = 8192
        self.media_handlers = Handlers()
        self.supported_charsets = frozenset(DEFAULT_SUPPORTED_CHARSETS)
