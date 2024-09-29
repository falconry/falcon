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


def _parse_media_type_header(media_type: str) -> Tuple[str, str, dict]:
    full_type, params = parse_header(media_type)

    # TODO(vytas): Workaround from python-mimeparse by J. Gregorio et al.
    #   Do we still need this in 2024?
    # Java URLConnection class sends an Accept header that includes a
    #   single '*'. Turn it into a legal wildcard.
    if full_type == '*':
        full_type = '*/*'

    main_type, separator, subtype = full_type.partition('/')
    if not separator:
        raise ValueError('invalid media type')

    return (main_type.strip(), subtype.strip(), params)


# TODO(vytas): Should we make these structures public?
class _MediaType:
    main_type: str
    subtype: str
    params: dict

    __slots__ = ('main_type', 'subtype', 'params')

    @classmethod
    def parse(cls, media_type: str) -> _MediaType:
        return cls(*_parse_media_type_header(media_type))

    def __init__(self, main_type: str, subtype: str, params: dict) -> None:
        self.main_type = main_type
        self.subtype = subtype
        self.params = params

    def __repr__(self) -> str:
        return f'MediaType<{self.main_type}/{self.subtype}; {self.params}>'


class _MediaRange:
    main_type: str
    subtype: str
    quality: float
    params: dict

    __slots__ = ('main_type', 'subtype', 'quality', 'params')

    _NOT_MATCHING = (-1, -1, -1, 0.0, -1)

    def __init__(
        self, main_type: str, subtype: str, quality: float, params: dict
    ) -> None:
        self.main_type = main_type
        self.subtype = subtype
        self.quality = quality
        self.params = params

    @classmethod
    def parse(cls, media_range: str) -> _MediaRange:
        main_type, subtype, params = _parse_media_type_header(media_range)

        # NOTE(vytas): We don't need to special-case Q since the above
        #   parse_header always lowercases parameters.
        q = params.pop('q', 1.0)

        try:
            quality = float(q)
        except (TypeError, ValueError) as ex:
            raise ValueError('invalid media range') from ex
        if not (0.0 <= quality <= 1.0):
            raise ValueError('q is not between 0.0 and 1.0')

        return cls(main_type, subtype, quality, params)

    def match_score(
        self, media_type: _MediaType, index: int = -1
    ) -> Tuple[int, int, int, float, int]:
        if self.main_type == '*' or media_type.main_type == '*':
            main_matches = 0
        elif self.main_type != media_type.main_type:
            return self._NOT_MATCHING
        else:
            main_matches = 1

        if self.subtype == '*' or media_type.subtype == '*':
            sub_matches = 0
        elif self.subtype != media_type.subtype:
            return self._NOT_MATCHING
        else:
            sub_matches = 1

        mr_pnames = frozenset(self.params)
        mt_pnames = frozenset(media_type.params)
        param_score = -len(mr_pnames.symmetric_difference(mt_pnames))
        matching = mr_pnames & mt_pnames
        for pname in matching:
            if self.params[pname] != media_type.params[pname]:
                return self._NOT_MATCHING
        param_score += len(matching)

        score = (main_matches, sub_matches, param_score, self.quality, index)
        print(f'score({self}, {media_type}) -> {score}')
        return (main_matches, sub_matches, param_score, self.quality, index)

    def __repr__(self) -> str:
        q = self.quality
        return f'MediaRange<{self.main_type}/{self.subtype}; {q=}; {self.params}>'


# PERF(vytas): It is possible to cache a classmethod too, but the invocation is
#   less efficient, especially in the case of a cache hit.
_parse_media_type = functools.lru_cache(_MediaType.parse)
_parse_media_range = functools.lru_cache(_MediaRange.parse)


@functools.lru_cache()
def _parse_media_ranges(header: str) -> Tuple[_MediaRange, ...]:
    return tuple(_MediaRange.parse(media_range) for media_range in header.split(','))


@functools.lru_cache()
def quality(media_type: str, header: str) -> float:
    """Get quality of the most specific matching media range.

    Media-ranges are parsed from the provided `header` value according to
    RFC 9110, Section 12.5.1 (the ``Accept`` header).

    Args:
        media_type: The Internet media type to match against the provided
            HTTP ``Accept`` header value.
        header: The value of a header that conforms to the format of the
            HTTP ``Accept`` header.

    Returns:
        Quality of the most specific media range matching the provided
        `media_type`. (If none matches, 0.0 is returned.)
    """
    parsed_media_type = _parse_media_type(media_type)
    media_ranges = _parse_media_ranges(header)

    most_specific = max(
        media_range.match_score(parsed_media_type) for media_range in media_ranges
    )
    return most_specific[-2]


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
