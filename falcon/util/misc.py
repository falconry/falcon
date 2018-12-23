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
import inspect
import warnings

from falcon import status_codes
from falcon.util import compat

__all__ = (
    'deprecated',
    'http_now',
    'dt_to_http',
    'http_date_to_dt',
    'to_query_str',
    'get_bound_method',
    'get_argnames',
    'get_http_status'
)


# PERF(kgriffs): Avoid superfluous namespace lookups
strptime = datetime.datetime.strptime
utcnow = datetime.datetime.utcnow


# NOTE(kgriffs): We don't want our deprecations to be ignored by default,
# so create our own type.
#
# TODO(kgriffs): Revisit this decision if users complain.
class DeprecatedWarning(UserWarning):
    pass


def deprecated(instructions):
    """Flags a method as deprecated.

    This function returns a decorator which can be used to mark deprecated
    functions. Applying this decorator will result in a warning being
    emitted when the function is used.

    Args:
        instructions (str): Specific guidance for the developer, e.g.:
            'Please migrate to add_proxy(...)''
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            message = 'Call to deprecated function {0}(...). {1}'.format(
                func.__name__,
                instructions)

            frame = inspect.currentframe().f_back

            warnings.warn_explicit(message,
                                   category=DeprecatedWarning,
                                   filename=inspect.getfile(frame.f_code),
                                   lineno=frame.f_lineno)

            return func(*args, **kwargs)

        return wrapper

    return decorator


def http_now():
    """Returns the current UTC time as an IMF-fixdate.

    Returns:
        str: The current UTC time as an IMF-fixdate,
        e.g., 'Tue, 15 Nov 1994 12:45:26 GMT'.
    """

    return dt_to_http(utcnow())


def dt_to_http(dt):
    """Converts a ``datetime`` instance to an HTTP date string.

    Args:
        dt (datetime): A ``datetime`` instance to convert, assumed to be UTC.

    Returns:
        str: An RFC 1123 date string, e.g.: "Tue, 15 Nov 1994 12:45:26 GMT".

    """

    # Tue, 15 Nov 1994 12:45:26 GMT
    return dt.strftime('%a, %d %b %Y %H:%M:%S GMT')


def http_date_to_dt(http_date, obs_date=False):
    """Converts an HTTP date string to a datetime instance.

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
    """Converts a dictionary of parameters to a query string.

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
                v = ','.join(map(str, v))
            else:
                for list_value in v:
                    if list_value is True:
                        list_value = 'true'
                    elif list_value is False:
                        list_value = 'false'
                    else:
                        list_value = str(list_value)

                    query_str += k + '=' + list_value + '&'

                continue
        else:
            v = str(v)

        query_str += k + '=' + v + '&'

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
        # NOTE(kgriffs): Ensure it is a bound method
        if compat.get_method_self(method) is None:
            # NOTE(kgriffs): In Python 3 this code is unreachable
            # because the above will raise AttributeError on its
            # own.
            msg = '{0} must be a bound method'.format(method)
            raise AttributeError(msg)

    return method


def _get_func_if_nested(callable):
    """Returns the function object of a given callable."""

    if isinstance(callable, functools.partial):
        return callable.func

    if inspect.isroutine(callable):
        return callable

    return callable.__call__


def _get_argspec(func):
    """Returns an inspect.ArgSpec instance given a function object.

    We prefer this implementation rather than the inspect module's getargspec
    since the latter has a strict check that the passed function is an instance
    of FunctionType. Cython functions do not pass this check, but they do implement
    the `func_code` and `func_defaults` attributes that we need to produce an Argspec.

    This implementation re-uses much of inspect.getargspec but removes the strict
    check allowing interface failures to be raised as AttributeError.

    (See also: https://github.com/python/cpython/blob/2.7/Lib/inspect.py)
    """
    if inspect.ismethod(func):
        func = func.im_func

    args, varargs, varkw = inspect.getargs(func.func_code)
    return inspect.ArgSpec(args, varargs, varkw, func.func_defaults)


def get_argnames(func):
    """Introspecs the arguments of a callable.

    Args:
        func: The callable to introspect

    Returns:
        A list of argument names, excluding *arg and **kwargs
        arguments.
    """

    if compat.PY2:
        func_object = _get_func_if_nested(func)
        spec = _get_argspec(func_object)

        args = spec.args

    else:
        sig = inspect.signature(func)

        args = [
            param.name
            for param in sig.parameters.values()
            if param.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        ]

    # NOTE(kgriffs): Depending on the version of Python, 'self' may or may not
    # be present, so we normalize the results by removing 'self' as needed.
    # Note that this behavior varies between 3.x versions as well as between
    # 3.x and 2.7.
    if args and args[0] == 'self':
        args = args[1:]

    return args


def get_http_status(status_code, default_reason='Unknown'):
    """Gets both the http status code and description from just a code

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
        raise ValueError('get_http_status failed: "%s" is not a '
                         'valid status code', status_code)

    # lookup the status code
    try:
        return getattr(status_codes, 'HTTP_' + str(code))
    except AttributeError:
        # not found
        return str(code) + ' ' + default_reason
