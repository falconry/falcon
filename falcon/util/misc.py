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

import datetime
import functools
import http
import inspect
import re
import unicodedata

from falcon import status_codes
from falcon.constants import PYPY
from falcon.constants import PYTHON_VERSION
from falcon.uri import encode_value

# NOTE(vytas): Hoist `deprecated` here since it is documented as part of the
# public Falcon interface.
from .deprecation import deprecated

try:
    from falcon.cyutil.misc import encode_items_to_latin1 as _cy_encode_items_to_latin1
except ImportError:
    _cy_encode_items_to_latin1 = None

try:
    from falcon.cyutil.misc import isascii as _cy_isascii
except ImportError:
    _cy_isascii = None


__all__ = (
    'is_python_func',
    'deprecated',
    'http_now',
    'dt_to_http',
    'http_date_to_dt',
    'to_query_str',
    'get_bound_method',
    'get_argnames',
    'get_http_status',
    'http_status_to_code',
    'code_to_http_status',
    'secure_filename',
)

_DEFAULT_HTTP_REASON = 'Unknown'

_UNSAFE_CHARS = re.compile(r'[^a-zA-Z0-9.-]')

# PERF(kgriffs): Avoid superfluous namespace lookups
strptime = datetime.datetime.strptime
utcnow = datetime.datetime.utcnow


# NOTE(kgriffs): This is tested in the gate but we do not want devs to
#   have to install a specific version of 3.5 to check coverage on their
#   workstations, so we use the nocover pragma here.
def _lru_cache_nop(*args, **kwargs):  # pragma: nocover
    def decorator(func):
        # NOTE(kgriffs): Partially emulate the lru_cache protocol; only add
        #   cache_info() later if/when it becomes necessary.
        func.cache_clear = lambda: None

        return func

    return decorator


# NOTE(kgriffs): https://bugs.python.org/issue28969
if PYTHON_VERSION >= (3, 5, 4) and PYTHON_VERSION != (3, 6, 0):
    _lru_cache_safe = functools.lru_cache  # type: ignore
else:
    _lru_cache_safe = _lru_cache_nop  # pragma: nocover


# PERF(kgriffs): Using lru_cache is slower on pypy when the wrapped
#   function is just doing a few non-IO operations.
if PYPY:
    _lru_cache_for_simple_logic = _lru_cache_nop  # pragma: nocover
else:
    _lru_cache_for_simple_logic = _lru_cache_safe  # type: ignore


def is_python_func(func):
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


def http_now():
    """Return the current UTC time as an IMF-fixdate.

    Returns:
        str: The current UTC time as an IMF-fixdate,
        e.g., 'Tue, 15 Nov 1994 12:45:26 GMT'.
    """

    return dt_to_http(utcnow())


def dt_to_http(dt):
    """Convert a ``datetime`` instance to an HTTP date string.

    Args:
        dt (datetime): A ``datetime`` instance to convert, assumed to be UTC.

    Returns:
        str: An RFC 1123 date string, e.g.: "Tue, 15 Nov 1994 12:45:26 GMT".

    """

    # Tue, 15 Nov 1994 12:45:26 GMT
    return dt.strftime('%a, %d %b %Y %H:%M:%S GMT')


def http_date_to_dt(http_date, obs_date=False):
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
    """

    if not obs_date:
        # PERF(kgriffs): This violates DRY, but we do it anyway
        #   to avoid the overhead of setting up a tuple, looping
        #   over it, and setting up exception handling blocks each
        #   time around the loop, in the case that we don't actually
        #   need to check for multiple formats.
        return strptime(http_date, '%a, %d %b %Y %H:%M:%S %Z')

    time_formats = (
        '%a, %d %b %Y %H:%M:%S %Z',
        '%a, %d-%b-%Y %H:%M:%S %Z',
        '%A, %d-%b-%y %H:%M:%S %Z',
        '%a %b %d %H:%M:%S %Y',
    )

    # Loop through the formats and return the first that matches
    for time_format in time_formats:
        try:
            return strptime(http_date, time_format)
        except ValueError:
            continue

    # Did not match any formats
    raise ValueError('time data %r does not match known formats' % http_date)


def to_query_str(params, comma_delimited_lists=True, prefix=True):
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


def get_bound_method(obj, method_name):
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


def get_argnames(func):
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


@deprecated('Please use falcon.code_to_http_status() instead.')
def get_http_status(status_code, default_reason=_DEFAULT_HTTP_REASON):
    """Get both the http status code and description from just a code.

    Warning:
        As of Falcon 3.0, this method has been deprecated in favor of
        :meth:`~falcon.code_to_http_status`.

    Args:
        status_code: integer or string that can be converted to an integer
        default_reason: default text to be appended to the status_code
            if the lookup does not find a result

    Returns:
        str: status code e.g. "404 Not Found"

    Raises:
        ValueError: the value entered could not be converted to an integer

    """
    # sanitize inputs
    try:
        code = float(status_code)  # float can validate values like "401.1"
        code = int(code)  # converting to int removes the decimal places
        if code < 100:
            raise ValueError
    except ValueError:
        raise ValueError(
            'get_http_status failed: "%s" is not a valid status code', status_code
        )

    # lookup the status code
    try:
        return getattr(status_codes, 'HTTP_' + str(code))
    except AttributeError:
        # not found
        return str(code) + ' ' + default_reason


def secure_filename(filename):
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
def http_status_to_code(status):
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
def code_to_http_status(status):
    """Normalize an HTTP status to an HTTP status line string.

    This function takes a member of :class:`http.HTTPStatus`, an ``int`` status
    code, an HTTP status line string or byte string (e.g., ``'200 OK'``) and
    returns the corresponding HTTP status line string.

    An LRU is used to minimize lookup time.

    Note:
        Unlike the deprecated :func:`get_http_status`, this function will not
        attempt to coerce a string status to an integer code, assuming the
        string already denotes an HTTP status line.

    Args:
        status: The status code or enum to normalize.

    Returns:
        str: HTTP status line corresponding to the given code. A newline
            is not included at the end of the string.
    """

    if isinstance(status, http.HTTPStatus):
        return '{} {}'.format(status.value, status.phrase)

    if isinstance(status, str):
        return status

    if isinstance(status, bytes):
        return status.decode()

    try:
        code = int(status)
        if not 100 <= code <= 999:
            raise ValueError('{} is not a valid status code'.format(status))
    except (ValueError, TypeError):
        raise ValueError('{!r} is not a valid status code'.format(status))

    try:
        # NOTE(kgriffs): We do this instead of using http.HTTPStatus since
        #   the Falcon module defines a larger number of codes.
        return getattr(status_codes, 'HTTP_' + str(code))
    except AttributeError:
        return '{} {}'.format(code, _DEFAULT_HTTP_REASON)


def _encode_items_to_latin1(data):
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


def _isascii(string):
    """Return ``True`` if all characters in the string are ASCII.

    ASCII characters have code points in the range U+0000-U+007F.

    Note:
        On Python 3.7+, this function is just aliased to ``str.isascii``.

    This is a pure-Python fallback for older CPython (where Cython is
    unavailable) and PyPy versions.

    Args:
        string (str): A string to test.

    Returns:
        ``True`` if all characters are ASCII, ``False`` otherwise.
    """

    try:
        string.encode('ascii')
        return True
    except ValueError:
        return False


_encode_items_to_latin1 = _cy_encode_items_to_latin1 or _encode_items_to_latin1
isascii = getattr(str, 'isascii', _cy_isascii or _isascii)
