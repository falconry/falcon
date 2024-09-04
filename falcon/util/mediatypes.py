# Copyright 2023-2024 by Vytautas Liuolia.
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

"""Media (aka MIME) type parsing and matching utilities."""

from __future__ import annotations

import functools
from typing import Dict, Iterable, Iterator, Optional, Tuple

__all__ = ('best_match', 'parse_header', 'quality')


def _parse_param_old_stdlib(s: str) -> Iterator[str]:
    while s[:1] == ';':
        s = s[1:]
        end = s.find(';')
        while end > 0 and (s.count('"', 0, end) - s.count('\\"', 0, end)) % 2:
            end = s.find(';', end + 1)
        if end < 0:
            end = len(s)
        f = s[:end]
        yield f.strip()
        s = s[end:]


def _parse_header_old_stdlib(line: str) -> Tuple[str, Dict[str, str]]:
    """Parse a Content-type like header.

    Return the main content-type and a dictionary of options.

    Note:
        This method has been copied (almost) verbatim from CPython 3.8 stdlib.
        It is slated for removal from the stdlib in 3.13.
    """
    parts = _parse_param_old_stdlib(';' + line)
    key = parts.__next__()
    pdict: Dict[str, str] = {}
    for p in parts:
        i = p.find('=')
        if i >= 0:
            name = p[:i].strip().lower()
            value = p[i + 1 :].strip()
            if len(value) >= 2 and value[0] == value[-1] == '"':
                value = value[1:-1]
                value = value.replace('\\\\', '\\').replace('\\"', '"')
            pdict[name] = value
    return key, pdict


def parse_header(line: str) -> Tuple[str, Dict[str, str]]:
    """Parse a Content-type like header.

    Return the main content-type and a dictionary of options.

    Args:
        line: A header value to parse.

    Returns:
        tuple: (the main content-type, dictionary of options).

    Note:
        This function replaces an equivalent method previously available in the
        stdlib as ``cgi.parse_header()``.
        It was removed from the stdlib in Python 3.13.
    """
    if '"' not in line and '\\' not in line:
        key, semicolon, parts = line.partition(';')
        if not semicolon:
            return (key.strip(), {})

        pdict = {}
        for part in parts.split(';'):
            name, equals, value = part.partition('=')
            if equals:
                pdict[name.strip().lower()] = value.strip()

        return (key.strip(), pdict)

    return _parse_header_old_stdlib(line)


class _MediaRange(tuple):
    @classmethod
    def parse(cls, media_range):
        pass

    def matches(self, media_type):
        pass


@functools.lru_cache()
def _parse_media_ranges(header):
    return tuple(_MediaRange.parse(media_range) for media_range in header.split(','))


@functools.lru_cache()
def quality(media_type: str, header: str) -> float:
    """Get quality of the most specific matching media range.

    Media-ranges are parsed from the provided `header` value according to
    RFC 9110, Section 12.5.1 (The ``Accept`` header).

    Args:
        media_type: The Internet media type to match against the provided
            HTTP ``Accept`` header value.
        header: The value of a header that conforms to the format of the
            HTTP ``Accept`` header.

    Returns:
        Quality of the most specific media range matching the provided
        `media_type`.
    """
    return 0.0


def best_match(media_types: Iterable[str], header: str) -> Optional[str]:
    """Choose media type with the highest quality from a list of candidates.

    Args:
        media_types: An iterable over one or more Internet media types
            to match against the provided header value.
        header: The value of a header that conforms to the format of the
            HTTP ``Accept`` header.

    Returns:
        Best match from the supported candidates, or ``None`` if the provided
        header value does not match any of the given types.
    """
    # media_ranges = _parse_media_ranges(header)
    return None
