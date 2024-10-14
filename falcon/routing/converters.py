# Copyright 2017 by Rackspace Hosting, Inc.
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
from __future__ import annotations

import abc
from datetime import datetime
from math import isfinite
from typing import Any, ClassVar, Iterable, Optional, overload, Union
import uuid

__all__ = (
    'BaseConverter',
    'DateTimeConverter',
    'FloatConverter',
    'IntConverter',
    'PathConverter',
    'UUIDConverter',
)


# PERF(kgriffs): Avoid an extra namespace lookup when using this function
strptime = datetime.strptime


class BaseConverter(metaclass=abc.ABCMeta):
    """Abstract base class for URI template field converters."""

    CONSUME_MULTIPLE_SEGMENTS: ClassVar[bool] = False
    """When set to ``True`` it indicates that this converter will consume
    multiple URL path segments. Currently a converter with
    ``CONSUME_MULTIPLE_SEGMENTS=True`` must be at the end of the URL template
    effectively meaning that it will consume all of the remaining URL path
    segments.
    """

    @abc.abstractmethod
    def convert(self, value: str) -> Any:
        """Convert a URI template field value to another format or type.

        Args:
            value (str or List[str]): Original string to convert.
                If ``CONSUME_MULTIPLE_SEGMENTS=True`` this value is a
                list of strings containing the path segments matched by
                the converter.

        Returns:
            object: Converted field value, or ``None`` if the field
                can not be converted.
        """


def _consumes_multiple_segments(converter: object) -> bool:
    return getattr(converter, 'CONSUME_MULTIPLE_SEGMENTS', False)


class IntConverter(BaseConverter):
    """Converts a field value to an int.

    Identifier: `int`

    Keyword Args:
        num_digits (int): Require the value to have the given
            number of digits.
        min (int): Reject the value if it is less than this number.
        max (int): Reject the value if it is greater than this number.
    """

    __slots__ = ('_num_digits', '_min', '_max')

    def __init__(
        self,
        num_digits: Optional[int] = None,
        min: Optional[int] = None,
        max: Optional[int] = None,
    ) -> None:
        if num_digits is not None and num_digits < 1:
            raise ValueError('num_digits must be at least 1')
        self._num_digits = num_digits
        self._min = min
        self._max = max

    def convert(self, value: str) -> Optional[int]:
        if self._num_digits is not None and len(value) != self._num_digits:
            return None

        # NOTE(kgriffs): int() will accept numbers with preceding or
        #   trailing whitespace, so we need to do our own check. Using
        #   strip() is faster than either a regex or a series of or'd
        #   membership checks via "in", esp. as the length of contiguous
        #   numbers in the value grows.
        if value.strip() != value:
            return None

        try:
            converted = int(value)
        except ValueError:
            return None

        return _validate_min_max_value(self, converted)


@overload
def _validate_min_max_value(converter: IntConverter, value: int) -> Optional[int]: ...


@overload
def _validate_min_max_value(
    converter: FloatConverter, value: float
) -> Optional[float]: ...


def _validate_min_max_value(
    converter: Union[IntConverter, FloatConverter], value: Union[int, float]
) -> Optional[Union[int, float]]:
    if converter._min is not None and value < converter._min:
        return None
    if converter._max is not None and value > converter._max:
        return None

    return value


class FloatConverter(BaseConverter):
    """Converts a field value to an float.

    Identifier: `float`

    Keyword Args:
        min (float): Reject the value if it is less than this number.
        max (float): Reject the value if it is greater than this number.
        finite (bool) : Determines whether or not to only match ordinary
            finite numbers (default: ``True``). Set to ``False`` to match
            ``nan``, ``inf``, and ``-inf`` in addition to finite numbers.

    .. versionadded:: 4.0
    """

    __slots__ = '_finite', '_min', '_max'

    def __init__(
        self,
        min: Optional[float] = None,
        max: Optional[float] = None,
        finite: bool = True,
    ) -> None:
        self._min = min
        self._max = max
        self._finite = finite if finite is not None else True

    def convert(self, value: str) -> Optional[float]:
        if value.strip() != value:
            return None

        try:
            converted = float(value)

            if self._finite and not isfinite(converted):
                return None

        except ValueError:
            return None

        return _validate_min_max_value(self, converted)


class DateTimeConverter(BaseConverter):
    """Converts a field value to a datetime.

    Identifier: `dt`

    Keyword Args:
        format_string (str): String used to parse the field value
            into a datetime. Any format recognized by strptime() is
            supported (default ``'%Y-%m-%dT%H:%M:%S%z'``).

    .. versionchanged:: 4.0
        The default value of `format_string` was changed from
        ``'%Y-%m-%dT%H:%M:%SZ'`` to ``'%Y-%m-%dT%H:%M:%S%z'``.

        The new format is a superset of the old one parsing-wise, however, the
        converted :class:`~datetime.datetime` object is now timezone-aware.
    """

    __slots__ = ('_format_string',)

    def __init__(self, format_string: str = '%Y-%m-%dT%H:%M:%S%z') -> None:
        self._format_string = format_string

    def convert(self, value: str) -> Optional[datetime]:
        try:
            return strptime(value, self._format_string)
        except ValueError:
            return None


class UUIDConverter(BaseConverter):
    """Converts a field value to a uuid.UUID.

    Identifier: `uuid`

    In order to be converted, the field value must consist of a
    string of 32 hexadecimal digits, as defined in RFC 4122, Section 3.
    Note, however, that hyphens and the URN prefix are optional.
    """

    def convert(self, value: str) -> Optional[uuid.UUID]:
        try:
            return uuid.UUID(value)
        except ValueError:
            return None


class PathConverter(BaseConverter):
    """Field converted used to match the rest of the path.

    This field converter matches the remainder of the URL path,
    returning it as a string.

    This converter is currently supported only when used at the
    end of the URL template.

    The classic routing rules of falcon apply also to this converter:
    considering the template ``'/foo/bar/{matched_path:path}'``, the path
    ``'/foo/bar'`` will *not* match the route; ``'/foo/bar/'`` will
    match, producing ``matched_path=''``, when
    :attr:`~falcon.RequestOptions.strip_url_path_trailing_slash` is ``False``
    (the default), while it will *not* match when that option is ``True``.

    (See also: :ref:`trailing_slash_in_path`)

    .. versionadded:: 4.0
    """

    CONSUME_MULTIPLE_SEGMENTS = True

    def convert(self, value: Iterable[str]) -> str:
        return '/'.join(value)


BUILTIN = (
    ('int', IntConverter),
    ('dt', DateTimeConverter),
    ('uuid', UUIDConverter),
    ('float', FloatConverter),
    ('path', PathConverter),
)
