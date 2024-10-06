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

import dataclasses
import functools
import math
from typing import Dict, Iterable, Iterator, Tuple

from falcon import errors

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

    .. versionadded:: 4.0
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
        raise errors.InvalidMediaType('The media type value must contain type/subtype.')

    return (main_type.strip(), subtype.strip(), params)


# TODO(vytas): Should we make these data structures public?


# PERF(vytas): It would be nice to use frozen=True as we never modify the data,
#   but it seems to incur a performance hit (~2-3x) on CPython 3.12.
@dataclasses.dataclass
class _MediaType:
    main_type: str
    subtype: str
    params: dict

    # NOTE(vytas): Using __slots__ with dataclasses is tricky, but it seems to
    #   work here since we are not using any default values in the definition.
    __slots__ = ('main_type', 'subtype', 'params')

    @classmethod
    def parse(cls, media_type: str) -> _MediaType:
        return cls(*_parse_media_type_header(media_type))


@dataclasses.dataclass
class _MediaRange:
    main_type: str
    subtype: str
    quality: float
    params: dict

    __slots__ = ('main_type', 'subtype', 'quality', 'params')

    _NOT_MATCHING = (-1, -1, -1, -1, 0.0)

    _Q_VALUE_ERROR_MESSAGE = (
        'If provided, the q parameter must be a real number '
        'in the range 0 through 1.'
    )

    @classmethod
    def parse(cls, media_range: str) -> _MediaRange:
        try:
            main_type, subtype, params = _parse_media_type_header(media_range)
        except errors.InvalidMediaType as ex:
            raise errors.InvalidMediaRange(
                'The media range value must contain type/subtype.'
            ) from ex

        # NOTE(vytas): We don't need to special-case Q since the above
        #   parse_header always lowercases parameter names.

        # PERF(vytas): Short-circuit if q is absent.
        if 'q' not in params:
            return cls(main_type, subtype, 1.0, params)

        try:
            q = float(params.pop('q'))
        except (TypeError, ValueError) as ex:
            # NOTE(vytas): RFC 9110, Section 12.4.2:
            #   weight = OWS ";" OWS "q=" qvalue
            #   qvalue = ( "0" [ "." 0*3DIGIT ] ) / ( "1" [ "." 0*3("0") ] )
            raise errors.InvalidMediaRange(cls._Q_VALUE_ERROR_MESSAGE) from ex

        if not (0.0 <= q <= 1.0) or not math.isfinite(q):
            raise errors.InvalidMediaRange(cls._Q_VALUE_ERROR_MESSAGE)

        # NOTE(vytas): RFC 9110, Section 12.4.2 states that a sender of qvalue
        #   MUST NOT generate more than three digits after the decimal point,
        #   but we are more permissive here, and opt not to spend any extra CPU
        #   cycles, if we have already managed to convert the value to float.

        return cls(main_type, subtype, q, params)

    def match_score(self, media_type: _MediaType) -> Tuple[int, int, int, int, float]:
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

        # PERF(vytas): We could also use bitwise operators directly between
        #   params.keys(), but set()/frozenset() seem to outperform dict.keys()
        #   slightly regardless of the number of elements, especially when we
        #   reuse the same sets for both intersection and symmetric_difference.
        mr_pnames = frozenset(self.params)
        mt_pnames = frozenset(media_type.params)

        exact_match = 0 if mr_pnames ^ mt_pnames else 1

        matching = mr_pnames & mt_pnames
        for pname in matching:
            if self.params[pname] != media_type.params[pname]:
                return self._NOT_MATCHING

        return (main_matches, sub_matches, exact_match, len(matching), self.quality)


# PERF(vytas): It is possible to cache a classmethod too, but the invocation is
#   less efficient, especially in the case of a cache hit.
# NOTE(vytas): Also, if we decide to make these classes public, we need to keep
#   these cached parsers private.
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

    The provided `media_type` is matched against each of the parsed media
    ranges, and the fitness of each match is assessed as follows
    (in the decreasing priority list of criteria):

    1. Do the main types (as in ``type/subtype``) match?

       The types must either match exactly, or as wildcard (``*``).
       The matches involving a wildcard are prioritized lower.

    2. Do the subtypes (as in ``type/subtype``) match?

       The subtypes must either match exactly, or as wildcard (``*``).
       The matches involving a wildcard are prioritized lower.

    3. Do the parameters match exactly?

       If all the parameter names and values (if any) between the media range
       and media type match exactly, such match is prioritized higher than
       matches involving extraneous parameters on either side.

       Note that if parameter names match, the corresponding values must also
       be equal, or the provided media type is considered not to match the
       media range in question at all.

    4. The number of matching parameters.

    5. Finally, if two or more best media range matches are equally fit
       according to all of the above criteria (1) through (4), the highest
       quality (i.e., the value of the ``q`` parameter) of these is returned.

    Note:
        With the exception of evaluating the exact parameter match (3), the
        number of extraneous parameters (i.e. where the names are only present
        in the media type, or only in the media range) currently does not
        influence the described specificity sort order.

    Args:
        media_type: The Internet media type to match against the provided
            HTTP ``Accept`` header value.
        header: The value of a header that conforms to the format of the
            HTTP ``Accept`` header.

    Returns:
        Quality of the most specific media range matching the provided
        `media_type`. (If none matches, 0.0 is returned.)

    .. versionadded:: 4.0
    """
    parsed_media_type = _parse_media_type(media_type)
    most_specific = max(
        media_range.match_score(parsed_media_type)
        for media_range in _parse_media_ranges(header)
    )
    return most_specific[-1]


def best_match(media_types: Iterable[str], header: str) -> str:
    """Choose media type with the highest :func:`quality` from a list of candidates.

    Args:
        media_types: An iterable over one or more Internet media types
            to match against the provided header value.
        header: The value of a header that conforms to the format of the
            HTTP ``Accept`` header.

    Returns:
        Best match from the supported candidates, or an empty string if the
        provided header value does not match any of the given types.

    .. versionadded:: 4.0
    """
    # PERF(vytas): Using the default parameter, i.e., max(..., default='', 0.0)
    #   would be much nicer than EAFP, but for some reason it is quite slow
    #   regardless of whether media_types is empty or not.
    try:
        matching, best_quality = max(
            ((media_type, quality(media_type, header)) for media_type in media_types),
            key=lambda mt_quality: mt_quality[1],
        )
        if best_quality > 0.0:
            return matching
    except errors.InvalidMediaType:
        # NOTE(vytas): Do not swallow instances of InvalidMediaType
        #   (it a subclass of ValueError).
        raise
    except ValueError:
        # NOTE(vytas): Barring unknown bugs, we only expect unhandled
        #   ValueErrors from supplying an empty media_types value.
        pass

    return ''
