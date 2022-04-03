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

"""ASGI multipart form media handler components."""

import cgi

from falcon.asgi.reader import BufferedReader
from falcon.errors import DelimiterError
from falcon.media import multipart

_ALLOWED_CONTENT_HEADERS = multipart._ALLOWED_CONTENT_HEADERS
_CRLF = multipart._CRLF
_CRLF_CRLF = multipart._CRLF_CRLF

MultipartParseError = multipart.MultipartParseError


class BodyPart(multipart.BodyPart):
    async def get_data(self):
        if self._data is None:
            max_size = self._parse_options.max_body_part_buffer_size + 1
            self._data = await self.stream.read(max_size)
            if len(self._data) >= max_size:
                raise MultipartParseError(description='body part is too large')

        return self._data

    async def get_media(self):
        if self._media is None:
            handler, _, _ = self._parse_options.media_handlers._resolve(
                self.content_type, 'text/plain'
            )

            try:
                self._media = await handler.deserialize_async(
                    self.stream, self.content_type, None
                )
            finally:
                if handler.exhaust_stream:
                    await self.stream.exhaust()

        return self._media

    async def get_text(self):
        content_type, options = cgi.parse_header(self.content_type)
        if content_type != 'text/plain':
            return None

        charset = options.get('charset', self._parse_options.default_charset)
        try:
            return (await self.get_data()).decode(charset)
        except (ValueError, LookupError) as err:
            raise MultipartParseError(
                description='invalid text or charset: {}'.format(charset)
            ) from err

    data = property(get_data)
    media = property(get_media)
    text = property(get_text)


class MultipartForm:
    def __init__(self, stream, boundary, content_length, parse_options):
        self._stream = (
            stream if isinstance(stream, BufferedReader) else BufferedReader(stream)
        )
        self._boundary = boundary
        # NOTE(vytas): Here self._dash_boundary is not prepended with CRLF
        #   (yet) for parsing the prologue. The CRLF will be prepended later to
        #   construct the inter-part delimiter as per RFC 7578, section 4.1
        #   (see the note below).
        self._dash_boundary = b'--' + boundary
        self._parse_options = parse_options

    def __aiter__(self):
        return self._iterate_parts()

    async def _iterate_parts(self):
        prologue = True
        delimiter = self._dash_boundary
        stream = self._stream
        max_headers_size = self._parse_options.max_body_part_headers_size
        remaining_parts = self._parse_options.max_body_part_count

        while True:
            # NOTE(vytas): Either exhaust the unused stream part, or skip
            #   the prologue.
            try:
                await stream.pipe_until(delimiter, consume_delimiter=True)

                if prologue:
                    # NOTE(vytas): RFC 7578, section 4.1.
                    #   As with other multipart types, the parts are delimited
                    #   with a boundary delimiter, constructed using CRLF,
                    #   "--", and the value of the "boundary" parameter.
                    delimiter = _CRLF + delimiter
                    prologue = False

                separator = await stream.read_until(_CRLF, 2, consume_delimiter=True)
                if separator == b'--':
                    # NOTE(vytas): boundary delimiter + '--\r\n' signals the
                    # end of a multipart form.
                    break
                elif separator:
                    raise MultipartParseError(description='unexpected form structure')

            except DelimiterError as err:
                raise MultipartParseError(
                    description='unexpected form structure'
                ) from err

            headers = {}
            try:
                headers_block = await stream.read_until(
                    _CRLF_CRLF, max_headers_size, consume_delimiter=True
                )
            except DelimiterError as err:
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
