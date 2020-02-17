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

"""Multipart form media handler."""

import cgi
import re
from urllib.parse import unquote_to_bytes

from falcon import errors
from falcon import request_helpers
from falcon.media.base import BaseHandler
from falcon.util import BufferedReader, DelimiterError
from falcon.util import misc

# TODO(vytas):
#   * Better support for form-wide charset setting
#   * Clean up, simplify, and optimize BufferedReader
#   * Better documentation

_ALLOWED_CONTENT_HEADERS = frozenset([
    b'content-type',
    b'content-disposition',
    b'content-transfer-encoding',
])

_FILENAME_STAR_RFC5987 = re.compile(r"([\w-]+)'[\w]*'(.+)")

_CRLF = b'\r\n'
_CRLF_CRLF = _CRLF + _CRLF


class MultipartParseError(errors.HTTPBadRequest):
    """Represents a multipart form parsing error.

    This error may refer to a malformed or truncated form, usage of deprecated
    or unsupported features, or form parameters exceeding limits configured in
    :class:`MultipartParseOptions`.

    :class:`MultipartParseError` instances raised in this module always include
    a short human-readable description of the error.
    """

    def __init__(self, description=None, headers=None, **kwargs):
        super().__init__(title='Malformed multipart/form-data request media',
                         description=description, headers=headers, **kwargs)


# TODO(vytas): Consider supporting -charset- stuff.
#   Does anyone use that (?)
class BodyPart:
    """Represents a body part in a multipart form.

    Note:
        `BodyPart` is meant to be instantiated directly only by the
        `MultipartForm` parser.

    Attributes:
        content_type (str): Value of the Content-Type header, or the multipart
            form default ``text/plain`` if the header is missing.

        data (bytes): Body part content bytes. The maximum number of bytes that
            could be read is configurable via :class:`MultipartParseOptions`,
            and a :class:`.MultipartParseError` is raised if the body part is
            larger that this size.

            For large bodies, such as attached files, use the input `stream`
            directly.

            .. note::
               Accessing this property the first time would consume the part
               input stream.
               The value is cached for subsequent access.

        name(str): The name parameter of the Content-Disposition header.
            The value of the "name" parameter is the original field name from
            the submitted HTML form.

            .. note::
               According to `RFC 7578, section 4.2
               <https://tools.ietf.org/html/rfc7578#section-4.2>`__, each part
               MUST include a Content-Disposition header field of type
               "form-data", where the name parameter is mandatory.

               However, Falcon will not raise any error if this parameter is
               missing; the propery value will be ``None`` in that case.

        filename (str): File name if the body part is an attached file, and
            ``None`` otherwise.

        secure_filename (str): The sanitized version of `filename` using only
            the most common ASCII characters for maximum portability and safety
            wrt using this name as a filename on a regular file system.

            If `filename` is empty or unset when referencing this property, an
            instance of :class:`MultipartParseError` will be raised.

            See also: :func:`~.secure_filename`

        stream: File-like input object for reading the body part of the
            multipart form request, if any. This object provides direct access
            to the server's data stream and is non-seekable. The stream is
            automatically delimited according to the multipart stream boundary.

        media (object): Returns a deserialized form of the multipart body part.
            When called, it will attempt to deserialize the body part stream
            using the Content-Type header as well as the media-type handlers
            configured via :class:`MultipartParseOptions`.


        text (str): The part decoded as a text string provided the part is
            encoded as ``text/plain``, ``None`` otherwise.

            Text is decoded from `data` using the charset specified in the
            `Content-Type` header, or, if omitted, the
            :data:`default charset <MultipartParseOptions.default_charset>`.
            The charset must be supported by Python's ``bytes.decode()``
            function. The list of standard encodings (charsets) supported by
            the Python 3 standard library can be found `here
            <https://docs.python.org/3/library/codecs.html#standard-encodings>`__.

            If decoding fails due to invalid `data` bytes (for the specified
            encoding), or the specified encoding itself is unsupported, a
            :class:`MultipartParseError` will be raised when referencing this
            property.

            .. note::
               As this property builds upon `data`, it would consume the part
               input stream in the same way.
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

        charset = options.get('charset', self._parse_options.default_charset)
        try:
            return self.data.decode(charset)
        except (ValueError, LookupError):
            raise MultipartParseError(
                'invalid text or charset: {}'.format(charset))

    @property
    def content_type(self):
        # NOTE(vytas): RFC 7578, section 4.4.
        #   Each part MAY have an (optional) "Content-Type" header field, which
        #   defaults to "text/plain".
        value = self._headers.get(b'content-type', b'text/plain')
        return value.decode('ascii')

    @property
    def filename(self):
        if self._filename is None:

            if self._content_disposition is None:
                value = self._headers.get(b'content-disposition', b'')
                self._content_disposition = cgi.parse_header(value.decode())

            _, params = self._content_disposition

            # NOTE(vytas): Supporting filename* as per RFC 5987, as that has
            #   been spotted in the wild, even though RFC 7578 forbids it.
            match = _FILENAME_STAR_RFC5987.match(params.get('filename*', ''))
            if match:
                charset, value = match.groups()
                try:
                    self._filename = unquote_to_bytes(value).decode(charset)
                except (ValueError, LookupError):
                    raise MultipartParseError(
                        'invalid text or charset: {}'.format(charset))
            else:
                value = params.get('filename')
                if value is None:
                    return None
                self._filename = value

        return self._filename

    @property
    def secure_filename(self):
        try:
            return misc.secure_filename(self.filename)
        except ValueError as ex:
            raise MultipartParseError(str(ex))

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
        # NOTE(vytas): More lenient check whether the provided stream is not
        #   already an instance of BufferedReader.
        # This approach makes testing both the Cythonized and pure-Python
        #   streams easier within the same test/benchmark suite.
        if not hasattr(stream, 'read_until'):
            if isinstance(stream, request_helpers.BoundedStream):
                stream = BufferedReader(stream.stream.read, content_length)
            else:
                stream = BufferedReader(stream.read, content_length)

        self._stream = stream
        self._boundary = boundary
        # NOTE(vytas): Here self._dash_boundary is not prepended with CRLF
        #   (yet) for parsing the prologue. The CRLF will be prepended later to
        #   construct the inter-part delimiter as per RFC 7578, section 4.1
        #   (see the note below).
        self._dash_boundary = b'--' + boundary
        self._parse_options = parse_options

    def __iter__(self):
        prologue = True
        delimiter = self._dash_boundary
        stream = self._stream
        max_headers_size = self._parse_options.max_body_part_headers_size
        remaining_parts = self._parse_options.max_body_part_count

        while True:
            # NOTE(vytas): Either exhaust the unused stream part, or skip
            #   the prologue.
            try:
                stream.pipe_until(delimiter, consume_delimiter=True)

                if prologue:
                    # NOTE(vytas): RFC 7578, section 4.1.
                    #   As with other multipart types, the parts are delimited
                    #   with a boundary delimiter, constructed using CRLF,
                    #   "--", and the value of the "boundary" parameter.
                    delimiter = _CRLF + delimiter
                    prologue = False

                separator = stream.read_until(_CRLF, 2, consume_delimiter=True)
                if separator == b'--':
                    # NOTE(vytas): boundary delimiter + '--\r\n' signals the
                    # end of a multipart form.
                    break
                elif separator:
                    raise MultipartParseError('unexpected form structure')

            except DelimiterError:
                raise MultipartParseError('unexpected form structure')

            headers = {}
            try:
                headers_block = stream.read_until(
                    _CRLF_CRLF, max_headers_size, consume_delimiter=True)
            except DelimiterError:
                raise MultipartParseError('incomplete body part headers')

            for line in headers_block.split(_CRLF):
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

            remaining_parts -= 1
            if remaining_parts < 0 < self._parse_options.max_body_part_count:
                raise MultipartParseError(
                    'maximum number of form body parts exceeded')

            yield BodyPart(stream.delimit(delimiter), headers,
                           self._parse_options)


class MultipartFormHandler(BaseHandler):
    """Multipart form (content type ``multipart/form-data``) media handler.

    The ``multipart/form-data`` media type for HTML5 forms is defined in
    `RFC 7578 <https://tools.ietf.org/html/rfc7578>`_.

    The multipart media type itself is defined in
    `RFC 2046 section 5.1 <https://tools.ietf.org/html/rfc2046#section-5.1>`_.

    .. note::
       Unlike many form parsing implementations in other frameworks, this
       handler does not consume the stream immediately. Rather, the stream is
       consumed on-demand and parsed into individual body parts while iterating
       over the media object.
    """

    def __init__(self, parse_options=None):
        self.parse_options = parse_options or MultipartParseOptions()

    def deserialize(self, stream, content_type, content_length):
        _, options = cgi.parse_header(content_type)
        try:
            boundary = options['boundary']
        except KeyError:
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


# PERF(vytas): To avoid typos and improve storage space and speed over a dict.
#   Inspired by RequestOptions.
class MultipartParseOptions:
    """Defines a set of configurable multipart form parser options.

    Attributes:
        default_charset (str): The default character encoding for
            :data:`text fields <BodyPart.text>` (default: ``utf-8``).

        max_body_part_count (int): The maximum number of body parts in the form
            (default: 64). If the form contains more parts than this number,
            an instance of :class:`MultipartParseError` will be raised. If this
            option is set to 0, no limit will be imposed by the parser.

        max_body_part_buffer_size (int): The maximum number of bytes to buffer
            and return when the :data:`BodyPart.data` property is
            referenced (default: 1 MiB). If the body part size exceeds this
            value, an instance of :class:`MultipartParseError` will be raised.

        max_body_part_headers_size (int): The maximum size (in bytes) of the
            body part headers structure (default: 8192). If the body part
            headers size exceeds this value, an instance of
            :class:`MultipartParseError` will be raised.

        media_handlers (Handlers): A dict-like object for configuring the
            media-types to handle. By default, handlers are provided for the
            ``application/json`` and ``application/x-www-form-urlencoded``
            media types.
    """

    _DEFAULT_HANDLERS = None

    __slots__ = (
        'default_charset',
        'max_body_part_buffer_size',
        'max_body_part_count',
        'max_body_part_headers_size',
        'media_handlers',
    )

    def __init__(self):
        self.default_charset = 'utf-8'
        self.max_body_part_buffer_size = 1024 * 1024
        self.max_body_part_count = 64
        self.max_body_part_headers_size = 8192
        self.media_handlers = self._DEFAULT_HANDLERS
