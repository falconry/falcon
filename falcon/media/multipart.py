# Copyright 2019-2024 by Vytautas Liuolia.
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

from __future__ import annotations

import re
from typing import (
    Any,
    ClassVar,
    Dict,
    Iterator,
    NoReturn,
    Optional,
    overload,
    Tuple,
    Type,
    TYPE_CHECKING,
    Union,
)
from urllib.parse import unquote_to_bytes

from falcon import errors
from falcon._typing import _UNSET
from falcon._typing import UnsetOr
from falcon.errors import MultipartParseError
from falcon.media.base import BaseHandler
from falcon.stream import BoundedStream
from falcon.typing import AsyncReadableIO
from falcon.typing import ReadableIO
from falcon.util import BufferedReader
from falcon.util import misc
from falcon.util.mediatypes import parse_header

if TYPE_CHECKING:
    from falcon.asgi.multipart import MultipartForm as AsgiMultipartForm
    from falcon.media import Handlers
    from falcon.util.reader import BufferedReader as PyBufferedReader

# TODO(vytas):
#   * Better support for form-wide charset setting
#   * Clean up, simplify, and optimize BufferedReader
#   * Better documentation

_ALLOWED_CONTENT_HEADERS = frozenset(
    [
        b'content-type',
        b'content-disposition',
        b'content-transfer-encoding',
    ]
)

_FILENAME_STAR_RFC5987 = re.compile(r"([\w-]+)'[\w]*'(.+)")

_CRLF = b'\r\n'
_CRLF_CRLF = _CRLF + _CRLF


# TODO(vytas): Consider supporting -charset- stuff.
#   Does anyone use that (?)
class BodyPart:
    """Represents a body part in a multipart form in an ASGI application.

    Note:
        :class:`BodyPart` is meant to be instantiated directly only by the
        :class:`MultipartFormHandler` parser.
    """

    _content_disposition: Optional[Tuple[str, Dict[str, str]]] = None
    _data: Optional[bytes] = None
    _filename: UnsetOr[Optional[str]] = _UNSET
    _media: UnsetOr[Any] = _UNSET
    _name: UnsetOr[Optional[str]] = _UNSET

    stream: PyBufferedReader
    """File-like input object for reading the body part of the
    multipart form request, if any. This object provides direct access
    to the server's data stream and is non-seekable. The stream is
    automatically delimited according to the multipart stream boundary.

    With the exception of being buffered to keep track of the boundary,
    the wrapped body part stream interface and behavior mimic
    :attr:`Request.bounded_stream <falcon.Request.bounded_stream>`.

    Reading the whole part content:

    .. code:: python

        data = part.stream.read()

    This is also safe:

    .. code:: python

        doc = yaml.safe_load(part.stream)
    """

    def __init__(
        self,
        stream: PyBufferedReader,
        headers: Dict[bytes, bytes],
        parse_options: MultipartParseOptions,
    ):
        self.stream = stream
        self._headers = headers
        self._parse_options = parse_options

    def get_data(self) -> bytes:
        """Return the body part content bytes.

        The maximum number of bytes that may be read is configurable via
        :class:`.MultipartParseOptions`, and a :class:`.MultipartParseError` is
        raised if the body part is larger that this size.

        The size limit guards against reading unexpectedly large amount of data
        into memory by referencing :attr:`data` and :attr:`text` properties
        that build upon this method.
        For large bodies, such as attached files, use the input :attr:`stream`
        directly.

        Note:
            Calling this method the first time will consume the part's input
            stream. The result is cached for subsequent access, and follow-up
            calls will just retrieve the cached content.

        Returns:
            bytes: The body part content.
        """
        if self._data is None:
            max_size = self._parse_options.max_body_part_buffer_size + 1
            self._data = self.stream.read(max_size)
            if len(self._data) >= max_size:
                raise MultipartParseError(description='body part is too large')

        return self._data

    def get_text(self) -> Optional[str]:
        """Return the body part content decoded as a text string.

        Text is decoded from the part content (as returned by
        :meth:`~.get_data`) using the charset specified in the `Content-Type`
        header, or, if omitted, the
        :data:`default charset <MultipartParseOptions.default_charset>`.
        The charset must be supported by Python's ``bytes.decode()``
        function. The list of standard encodings (charsets) supported by the
        Python 3 standard library can be found `here
        <https://docs.python.org/3/library/codecs.html#standard-encodings>`__.

        If decoding fails due to invalid `data` bytes (for the specified
        encoding), or the specified encoding itself is unsupported, a
        :class:`.MultipartParseError` will be raised when referencing this
        property.

        Note:
            As this method builds upon :meth:`~.get_data`, it will consume the
            part's input stream in the same way.

        Returns:
            str: The part decoded as a text string provided the part is
            encoded as ``text/plain``, ``None`` otherwise.
        """
        content_type, options = parse_header(self.content_type)
        if content_type != 'text/plain':
            return None

        charset = options.get('charset', self._parse_options.default_charset)
        try:
            return self.data.decode(charset)
        except (ValueError, LookupError) as err:
            raise MultipartParseError(
                description='invalid text or charset: {}'.format(charset)
            ) from err

    @property
    def content_type(self) -> str:
        """Value of the Content-Type header.

        When the header is missing returns the multipart form default ``text/plain``.
        """
        # NOTE(vytas): RFC 7578, section 4.4.
        #   Each part MAY have an (optional) "Content-Type" header field, which
        #   defaults to "text/plain".
        value = self._headers.get(b'content-type', b'text/plain')
        return value.decode('ascii')

    @property
    def filename(self) -> Optional[str]:
        """File name if the body part is an attached file, and ``None`` otherwise."""
        if self._filename is _UNSET:
            if self._content_disposition is None:
                value = self._headers.get(b'content-disposition', b'')
                self._content_disposition = parse_header(value.decode())

            _, params = self._content_disposition

            # NOTE(vytas): Supporting filename* as per RFC 5987, as that has
            #   been spotted in the wild, even though RFC 7578 forbids it.
            match = _FILENAME_STAR_RFC5987.match(params.get('filename*', ''))
            if match:
                charset, filename_raw = match.groups()
                try:
                    self._filename = unquote_to_bytes(filename_raw).decode(charset)
                except (ValueError, LookupError) as err:
                    raise MultipartParseError(
                        description='invalid text or charset: {}'.format(charset)
                    ) from err
            else:
                self._filename = params.get('filename')

        return self._filename

    @property
    def secure_filename(self) -> str:
        """The sanitized version of `filename` using only the most common ASCII
        characters for maximum portability and safety wrt using this name as a
        filename on a regular file system.

        If `filename` is empty or unset when referencing this property, an
        instance of :class:`.MultipartParseError` will be raised.

        See also: :func:`~.secure_filename`
        """  # noqa: D205
        try:
            return misc.secure_filename(self.filename or '')
        except ValueError as ex:
            raise MultipartParseError(description=str(ex)) from ex

    @property
    def name(self) -> Optional[str]:
        """The name parameter of the Content-Disposition header.

        The value of the "name" parameter is the original field name from
        the submitted HTML form.

        .. note::
            According to `RFC 7578, section 4.2
            <https://tools.ietf.org/html/rfc7578#section-4.2>`__, each part
            MUST include a Content-Disposition header field of type
            "form-data", where the name parameter is mandatory.

            However, Falcon will not raise any error if this parameter is
            missing; the property value will be ``None`` in that case.
        """
        if self._name is _UNSET:
            if self._content_disposition is None:
                value = self._headers.get(b'content-disposition', b'')
                self._content_disposition = parse_header(value.decode())

            _, params = self._content_disposition
            self._name = params.get('name')

        return self._name

    def get_media(self) -> Any:
        """Return a deserialized form of the multipart body part.

        When called, this method will attempt to deserialize the body part
        stream using the Content-Type header as well as the media-type handlers
        configured via :class:`MultipartParseOptions`.

        The result will be cached and returned in subsequent calls::

            deserialized_media = part.get_media()

        Returns:
            object: The deserialized media representation.
        """
        if self._media is _UNSET:
            handler, _, _ = self._parse_options.media_handlers._resolve(
                self.content_type, 'text/plain'
            )

            try:
                self._media = handler.deserialize(self.stream, self.content_type, None)
            finally:
                if handler.exhaust_stream:
                    self.stream.exhaust()

        return self._media

    data: bytes = property(get_data)  # type: ignore[assignment]
    """Property that acts as a convenience alias for :meth:`~.get_data`.

    .. code:: python

        # Equivalent to: content = part.get_data()
        content = part.data
    """
    media: Any = property(get_media)
    """Property that acts as a convenience alias for :meth:`~.get_media`.

    .. code:: python

        # Equivalent to: deserialized_media = part.get_media()
        deserialized_media = req.media
    """
    text: str = property(get_text)  # type: ignore[assignment]
    """Property that acts as a convenience alias for :meth:`~.get_text`.

    .. code:: python

        # Equivalent to: decoded_text = part.get_text()
        decoded_text = part.text
    """


class MultipartForm:
    """Iterable object that returns each form part as :class:`BodyPart` instances.

    Typical usage illustrated below::

        def on_post(self, req: Request, resp: Response) -> None:
            form: MultipartForm = req.get_media()

            for part in form:
                if part.name == 'foo':
                    ...
                else:
                    ...

    Note:
        :class:`MultipartForm` is meant to be instantiated directly only by the
        :class:`MultipartFormHandler` parser.
    """

    def __init__(
        self,
        stream: ReadableIO,
        boundary: bytes,
        content_length: Optional[int],
        parse_options: MultipartParseOptions,
    ) -> None:
        # NOTE(vytas): More lenient check whether the provided stream is not
        #   already an instance of BufferedReader.
        # This approach makes testing both the Cythonized and pure-Python
        #   streams easier within the same test/benchmark suite.
        if not hasattr(stream, 'read_until'):
            assert content_length is not None
            if isinstance(stream, BoundedStream):
                stream = BufferedReader(stream.stream.read, content_length)
            else:
                stream = BufferedReader(stream.read, content_length)

        self._stream: PyBufferedReader = stream  # type: ignore[assignment]
        self._boundary = boundary
        # NOTE(vytas): Here self._dash_boundary is not prepended with CRLF
        #   (yet) for parsing the prologue. The CRLF will be prepended later to
        #   construct the inter-part delimiter as per RFC 7578, section 4.1
        #   (see the note below).
        self._dash_boundary = b'--' + boundary
        self._parse_options = parse_options

    def __iter__(self) -> Iterator[BodyPart]:
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

                # NOTE(vytas): Interpretations of RFC 2046, Appendix A, vary
                #   as to whether the closing `--` must be followed by CRLF.
                #   While the absolute majority of HTTP clients and browsers
                #   do append it as a common convention, it seems that this is
                #   not mandated by the RFC, so we do not require it either.
                # NOTE(vytas): Certain versions of the Undici client
                #   (Node's fetch implementation) do not follow the convention.
                if stream.peek(2) == b'--':
                    # NOTE(vytas): boundary delimiter + '--' signals the end of
                    #   a multipart form.
                    stream.read(2)
                    break

                stream.read_until(_CRLF, 0, consume_delimiter=True)

            except errors.DelimiterError as err:
                raise MultipartParseError(
                    description='unexpected form structure'
                ) from err

            headers: Dict[bytes, bytes] = {}
            try:
                headers_block = stream.read_until(
                    _CRLF_CRLF, max_headers_size, consume_delimiter=True
                )
            except errors.DelimiterError as err:
                raise MultipartParseError(
                    description='incomplete body part headers'
                ) from err

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
                    if name == b'content-transfer-encoding' and value != b'binary':
                        raise MultipartParseError(
                            description=(
                                'the deprecated Content-Transfer-Encoding '
                                'header field is unsupported'
                            )
                        )
                    # NOTE(vytas): RFC 7578, section 4.8.
                    #   Other header fields MUST NOT be included and MUST be
                    #   ignored.
                    elif name in _ALLOWED_CONTENT_HEADERS:
                        headers[name] = value

            remaining_parts -= 1
            if remaining_parts < 0 < self._parse_options.max_body_part_count:
                raise MultipartParseError(
                    description='maximum number of form body parts exceeded'
                )

            yield BodyPart(stream.delimit(delimiter), headers, self._parse_options)


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

    For examples on parsing the request form, see also: :ref:`multipart`.
    """

    _ASGI_MULTIPART_FORM: ClassVar[Type[AsgiMultipartForm]]

    parse_options: MultipartParseOptions
    """Configuration options for the multipart form parser and instances of
    :class:`~falcon.media.multipart.BodyPart` it yields.

    See also: :ref:`multipart_parser_conf`.
    """

    def __init__(self, parse_options: Optional[MultipartParseOptions] = None) -> None:
        self.parse_options = parse_options or MultipartParseOptions()

    @overload
    def _deserialize_form(
        self,
        stream: ReadableIO,
        content_type: Optional[str],
        content_length: Optional[int],
        form_cls: Type[MultipartForm] = ...,
    ) -> MultipartForm: ...

    @overload
    def _deserialize_form(
        self,
        stream: AsyncReadableIO,
        content_type: Optional[str],
        content_length: Optional[int],
        form_cls: Type[AsgiMultipartForm] = ...,
    ) -> AsgiMultipartForm: ...

    def _deserialize_form(
        self,
        stream: Union[ReadableIO, AsyncReadableIO],
        content_type: Optional[str],
        content_length: Optional[int],
        form_cls: Type[Union[MultipartForm, AsgiMultipartForm]] = MultipartForm,
    ) -> Union[MultipartForm, AsgiMultipartForm]:
        assert content_type is not None
        _, options = parse_header(content_type)
        try:
            boundary = options['boundary']
        except KeyError:
            raise errors.HTTPInvalidHeader(
                'No boundary specifier found in {!r}'.format(content_type),
                'Content-Type',
            )

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
                'Content-Type',
            )

        return form_cls(stream, boundary.encode(), content_length, self.parse_options)  # type: ignore[arg-type]

    def deserialize(
        self,
        stream: ReadableIO,
        content_type: Optional[str],
        content_length: Optional[int],
    ) -> MultipartForm:
        return self._deserialize_form(stream, content_type, content_length)

    async def deserialize_async(
        self,
        stream: AsyncReadableIO,
        content_type: Optional[str],
        content_length: Optional[int],
    ) -> AsgiMultipartForm:
        return self._deserialize_form(
            stream, content_type, content_length, form_cls=self._ASGI_MULTIPART_FORM
        )

    def serialize(self, media: object, content_type: str) -> NoReturn:
        raise NotImplementedError('multipart form serialization unsupported')


# PERF(vytas): To avoid typos and improve storage space and speed over a dict.
#   Inspired by RequestOptions.
class MultipartParseOptions:
    """Defines a set of configurable multipart form parser options.

    An instance of this class is exposed via the
    :attr:`MultipartFormHandler.parse_options
    <falcon.media.MultipartFormHandler.parse_options>` attribute.
    The handler's options are also passed down to every :class:`BodyPart`
    it instantiates.

    See also: :ref:`multipart_parser_conf`.
    """

    default_charset: str
    """The default character encoding for
    :meth:`text fields <BodyPart.get_text>` (default ``utf-8``).
    """
    max_body_part_count: int
    """The maximum number of body parts in the form (default ``64``).

    If the form contains more parts than this number, an instance of
    :class:`.MultipartParseError` will be raised. If this option is set to 0,
    no limit will be imposed by the parser.
    """
    max_body_part_buffer_size: int
    """The maximum number of bytes to buffer and return when the
    :meth:`BodyPart.get_data` method is called (default ``1 MiB``).

    If the body part size exceeds this value, an instance of
    :class:`.MultipartParseError` will be raised.
    """
    max_body_part_headers_size: int
    """The maximum size (in bytes) of the body part headers structure
    (default ``8192``).

    If the body part headers size exceeds this value, an instance of
    :class:`.MultipartParseError` will be raised.
    """
    media_handlers: Handlers
    """A dict-like object for configuring the media-types to handle.

    By default, handlers are provided for the ``application/json`` and
    ``application/x-www-form-urlencoded`` media types.
    """

    if TYPE_CHECKING:
        _DEFAULT_HANDLERS: ClassVar[Handlers]
    else:
        _DEFAULT_HANDLERS = None

    __slots__ = (
        'default_charset',
        'max_body_part_buffer_size',
        'max_body_part_count',
        'max_body_part_headers_size',
        'media_handlers',
    )

    def __init__(self) -> None:
        self.default_charset = 'utf-8'
        self.max_body_part_buffer_size = 1024 * 1024
        self.max_body_part_count = 64
        self.max_body_part_headers_size = 8192
        # NOTE(myusko,vytas): Here we create a copy of _DEFAULT_HANDLERS in
        #   order to prevent the modification of the class variable whenever
        #   parse_options.media_handlers are customized.
        self.media_handlers = self._DEFAULT_HANDLERS.copy()
