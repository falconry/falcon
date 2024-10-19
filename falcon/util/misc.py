# Copyright 2013 by Rackspace Hosting, Inc.
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

"""Miscellaneous utilities.

This module provides misc. utility functions for apps and the Falcon
framework itself. These functions are hoisted into the front-door
`falcon` module for convenience::

    import falcon

    now = falcon.http_now()
"""

from __future__ import annotations

import datetime
import functools
import http
import inspect
import re
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple, Union
import unicodedata

from falcon import status_codes
from falcon.constants import PYPY
from falcon.uri import encode_value

# NOTE(vytas): Hoist `deprecated` here since it is documented as part of the
# public Falcon interface.
from .deprecation import deprecated

try:
    from falcon.cyutil.misc import encode_items_to_latin1 as _cy_encode_items_to_latin1
except ImportError:
    _cy_encode_items_to_latin1 = None

__all__ = (
    'is_python_func',
    'deprecated',
    'http_now',
    'dt_to_http',
    'http_date_to_dt',
    'to_query_str',
    'get_bound_method',
    'get_argnames',
    'http_status_to_code',
    'code_to_http_status',
    'secure_filename',
)

_DEFAULT_HTTP_REASON = 'Unknown'

_UNSAFE_CHARS = re.compile(r'[^a-zA-Z0-9.-]')

_UTC_TIMEZONE = datetime.timezone.utc

# PERF(kgriffs): Avoid superfluous namespace lookups
_strptime: Callable[[str, str], datetime.datetime] = datetime.datetime.strptime
_utcnow: Callable[[], datetime.datetime] = functools.partial(
    datetime.datetime.now, datetime.timezone.utc
)

# The above aliases were not underscored prior to Falcon 3.1.2.
strptime: Callable[[str, str], datetime.datetime] = deprecated(
    'This was a private alias local to this module; '
    'please reference datetime.strptime() directly.'
)(datetime.datetime.strptime)
utcnow: Callable[[], datetime.datetime] = deprecated(
    'This was a private alias local to this module; '
    'please reference datetime.utcnow() directly.'
)(datetime.datetime.utcnow)


# NOTE(kgriffs,vytas): This is tested in the PyPy gate but we do not want devs
#   to have to install PyPy to check coverage on their workstations, so we use
#   the nocover pragma here.
def _lru_cache_nop(maxsize: int) -> Callable[[Callable], Callable]:  # pragma: nocover
    def decorator(func: Callable) -> Callable:
        # NOTE(kgriffs): Partially emulate the lru_cache protocol; only add
        #   cache_info() later if/when it becomes necessary.
        func.cache_clear = lambda: None  # type: ignore

        return func

    return decorator


# PERF(kgriffs): Using lru_cache is slower on PyPy when the wrapped
#   function is just doing a few non-IO operations.
if PYPY:
    _lru_cache_for_simple_logic = _lru_cache_nop  # pragma: nocover
else:
    _lru_cache_for_simple_logic = functools.lru_cache


def is_python_func(func: Union[Callable, Any]) -> bool:
    """Determine if a function or method uses a standard Python type.

    This helper can be used to check a function or method to determine if it
    uses a standard Python type, as opposed to an implementation-specific
    native extension type.

    For example, because Cython functions are not standard Python functions,
    ``is_python_func(f)`` will return ``False`` when f is a reference to a
    cythonized function or method.

    Args:
        func: The function object to check.
    Returns:
        bool: ``True`` if the function or method uses a standard Python
        type; ``False`` otherwise.

    """
    if inspect.ismethod(func):
        func = func.__func__

    return inspect.isfunction(func)


def http_now() -> str:
    """Return the current UTC time as an IMF-fixdate.

    Returns:
        str: The current UTC time as an IMF-fixdate,
        e.g., 'Tue, 15 Nov 1994 12:45:26 GMT'.
    """

    return dt_to_http(_utcnow())


def dt_to_http(dt: datetime.datetime) -> str:
    """Convert a ``datetime`` instance to an HTTP date string.

    Args:
        dt (datetime): A ``datetime`` instance to convert, assumed to be UTC.

    Returns:
        str: An RFC 1123 date string, e.g.: "Tue, 15 Nov 1994 12:45:26 GMT".

    """

    # Tue, 15 Nov 1994 12:45:26 GMT
    return dt.strftime('%a, %d %b %Y %H:%M:%S GMT')


def http_date_to_dt(http_date: str, obs_date: bool = False) -> datetime.datetime:
    """Convert an HTTP date string to a datetime instance.

    Args:
        http_date (str): An RFC 1123 date string, e.g.:
            "Tue, 15 Nov 1994 12:45:26 GMT".

    Keyword Arguments:
        obs_date (bool): Support obs-date formats according to
            RFC 7231, e.g.:
            "Sunday, 06-Nov-94 08:49:37 GMT" (default ``False``).

    Returns:
        datetime: A UTC datetime instance corresponding to the given
        HTTP date.

    Raises:
        ValueError: http_date doesn't match any of the available time formats
        ValueError: http_date doesn't match allowed timezones

    .. versionchanged:: 4.0
        This function now returns timezone-aware :class:`~datetime.datetime`
        objects.
    """
    if not obs_date:
        # PERF(kgriffs): This violates DRY, but we do it anyway
        #   to avoid the overhead of setting up a tuple, looping
        #   over it, and setting up exception handling blocks each
        #   time around the loop, in the case that we don't actually
        #   need to check for multiple formats.
        # NOTE(vytas): According to RFC 9110, Section 5.6.7, the only allowed
        #   value for the TIMEZONE field [of IMF-fixdate] is %s"GMT", so we
        #   simply hardcode GMT in the strptime expression.
        return _strptime(http_date, '%a, %d %b %Y %H:%M:%S GMT').replace(
            tzinfo=_UTC_TIMEZONE
        )

    time_formats = (
        '%a, %d %b %Y %H:%M:%S %Z',
        '%a, %d-%b-%Y %H:%M:%S %Z',
        '%A, %d-%b-%y %H:%M:%S %Z',
        '%a %b %d %H:%M:%S %Y',
    )

    # Loop through the formats and return the first that matches
    for time_format in time_formats:
        try:
            # NOTE(chgad,vytas): As per now-obsolete RFC 850, Section 2.1.4
            #   (and later references in newer RFCs) the TIMEZONE field may be
            #   be one of many abbreviations such as EST, MDT, etc; which are
            #   not equivalent to UTC.
            #   However, Python seems unable to parse any such abbreviations
            #   except GMT and UTC due to a bug/lacking implementation
            #   (see https://github.com/python/cpython/issues/66571); so we can
            #   indiscriminately assume UTC after all.
            return _strptime(http_date, time_format).replace(tzinfo=_UTC_TIMEZONE)
        except ValueError:
            continue

    # Did not match any formats
    raise ValueError('time data %r does not match known formats' % http_date)


def to_query_str(
    params: Optional[Mapping[str, Any]],
    comma_delimited_lists: bool = True,
    prefix: bool = True,
) -> str:
    """Convert a dictionary of parameters to a query string.

    Args:
        params (dict): A dictionary of parameters, where each key is
            a parameter name, and each value is either a ``str`` or
            something that can be converted into a ``str``, or a
            list of such values. If a ``list``, the value will be
            converted to a comma-delimited string of values
            (e.g., 'thing=1,2,3').
        comma_delimited_lists (bool): Set to ``False`` to encode list
            values by specifying multiple instances of the parameter
            (e.g., 'thing=1&thing=2&thing=3'). Otherwise, parameters
            will be encoded as comma-separated values (e.g.,
            'thing=1,2,3'). Defaults to ``True``.
        prefix (bool): Set to ``False`` to exclude the '?' prefix
            in the result string (default ``True``).

    Returns:
        str: A URI query string, including the '?' prefix (unless
        `prefix` is ``False``), or an empty string if no params are
        given (the ``dict`` is empty).
    """

    if not params:
        return ''

    # PERF: This is faster than a list comprehension and join, mainly
    # because it allows us to inline the value transform.
    query_str = '?' if prefix else ''
    for k, v in params.items():
        if v is True:
            v = 'true'
        elif v is False:
            v = 'false'
        elif isinstance(v, list):
            if comma_delimited_lists:
                v = ','.join(map(encode_value, map(str, v)))
            else:
                for list_value in v:
                    if list_value is True:
                        list_value = 'true'
                    elif list_value is False:
                        list_value = 'false'
                    else:
                        list_value = encode_value(str(list_value))

                    query_str += encode_value(k) + '=' + list_value + '&'

                continue
        else:
            v = encode_value(str(v))

        query_str += encode_value(k) + '=' + v + '&'

    return query_str[:-1]


def get_bound_method(obj: object, method_name: str) -> Union[None, Callable[..., Any]]:
    """Get a bound method of the given object by name.

    Args:
        obj: Object on which to look up the method.
        method_name: Name of the method to retrieve.

    Returns:
        Bound method, or ``None`` if the method does not exist on
        the object.

    Raises:
        AttributeError: The method exists, but it isn't
            bound (most likely a class was passed, rather than
            an instance of that class).

    """

    method = getattr(obj, method_name, None)
    if method is not None:
        # NOTE(kgriffs): Ensure it is a bound method. Raises AttributeError
        # if the attribute is missing.
        getattr(method, '__self__')

    return method


def get_argnames(func: Callable[..., Any]) -> List[str]:
    """Introspect the arguments of a callable.

    Args:
        func: The callable to introspect

    Returns:
        A list of argument names, excluding *arg and **kwargs
        arguments.
    """

    sig = inspect.signature(func)

    args = [
        param.name
        for param in sig.parameters.values()
        if param.kind
        not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
    ]

    # NOTE(kgriffs): Depending on the version of Python, 'self' may or may not
    # be present, so we normalize the results by removing 'self' as needed.
    # Note that this behavior varies between 3.x versions.
    if args and args[0] == 'self':
        args = args[1:]

    return args


def secure_filename(filename: str) -> str:
    """Sanitize the provided `filename` to contain only ASCII characters.

    Only ASCII alphanumerals, ``'.'``, ``'-'`` and ``'_'`` are allowed for
    maximum portability and safety wrt using this name as a filename on a
    regular file system. All other characters will be replaced with an
    underscore (``'_'``).

    .. note::
        The `filename` is normalized to the Unicode ``NKFD`` form prior to
        ASCII conversion in order to extract more alphanumerals where a
        decomposition is available. For instance:

        >>> secure_filename('Bold Digit 𝟏')
        'Bold_Digit_1'
        >>> secure_filename('Ångström unit physics.pdf')
        'A_ngstro_m_unit_physics.pdf'

    Args:
        filename (str): Arbitrary filename input from the request, such as a
            multipart form filename field.

    Returns:
        str: The sanitized filename.

    Raises:
        ValueError: the provided filename is an empty string.
    """
    # TODO(vytas): max_length (int): Maximum length of the returned
    #     filename. Should the returned filename exceed this restriction, it is
    #     truncated while attempting to preserve the extension.
    if not filename:
        raise ValueError('filename may not be an empty string')

    filename = unicodedata.normalize('NFKD', filename)
    if filename.startswith('.'):
        filename = filename.replace('.', '_', 1)
    return _UNSAFE_CHARS.sub('_', filename)


@_lru_cache_for_simple_logic(maxsize=64)
def http_status_to_code(status: Union[http.HTTPStatus, int, bytes, str]) -> int:
    """Normalize an HTTP status to an integer code.

    This function takes a member of :class:`http.HTTPStatus`, an HTTP status
    line string or byte string (e.g., ``'200 OK'``), or an ``int`` and
    returns the corresponding integer code.

    An LRU is used to minimize lookup time.

    Args:
        status: The status code or enum to normalize.

    Returns:
        int: Integer code for the HTTP status (e.g., 200)
    """

    if isinstance(status, http.HTTPStatus):
        return status.value

    if isinstance(status, int):
        return status

    if isinstance(status, bytes):
        status = status.decode()

    if not isinstance(status, str):
        raise ValueError('status must be an int, str, or a member of http.HTTPStatus')

    if len(status) < 3:
        raise ValueError('status strings must be at least three characters long')

    try:
        return int(status[:3])
    except ValueError:
        raise ValueError('status strings must start with a three-digit integer')


@_lru_cache_for_simple_logic(maxsize=64)
def code_to_http_status(status: Union[int, http.HTTPStatus, bytes, str]) -> str:
    """Normalize an HTTP status to an HTTP status line string.

    This function takes a member of :class:`http.HTTPStatus`, an ``int`` status
    code, an HTTP status line string or byte string (e.g., ``'200 OK'``) and
    returns the corresponding HTTP status line string.

    An LRU is used to minimize lookup time.

    Note:
        This function will not attempt to coerce a string status to an
        integer code, assuming the string already denotes an HTTP status line.

    Args:
        status: The status code or enum to normalize.

    Returns:
        str: HTTP status line corresponding to the given code. A newline
            is not included at the end of the string.
    """

    if isinstance(status, http.HTTPStatus):
        return '{} {}'.format(status.value, status.phrase)

    # NOTE(kgriffs): If it is a str but does not have a space, assume it is
    #   just the number by itself.
    if isinstance(status, str) and ' ' in status:
        return status

    if isinstance(status, bytes) and b' ' in status:
        return status.decode()

    try:
        code = int(status)
    except (ValueError, TypeError):
        raise ValueError('{!r} is not a valid status code'.format(status))
    if not 100 <= code <= 999:
        raise ValueError('{!r} is not a valid status code'.format(status))

    try:
        # NOTE(kgriffs): We do this instead of using http.HTTPStatus since
        #   the Falcon module defines a larger number of codes.
        return getattr(status_codes, 'HTTP_' + str(code))
    except AttributeError:
        return '{} {}'.format(code, _DEFAULT_HTTP_REASON)


def _encode_items_to_latin1(data: Dict[str, str]) -> List[Tuple[bytes, bytes]]:
    """Decode all key/values of a dict to Latin-1.

    Args:
        data (dict): A dict of string key/values to encode to a list of
        bytestring items.

    Returns:
        A list of (bytes, bytes) tuples.
    """
    result = []

    for key, value in data.items():
        result.append((key.encode('latin1'), value.encode('latin1')))

    return result


_encode_items_to_latin1 = _cy_encode_items_to_latin1 or _encode_items_to_latin1

isascii = deprecated(
    'This method will be removed in Falcon 5.0; please use str.isascii() instead.'
)(str.isascii)
