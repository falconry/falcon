"""Defines Falcon utility functions

Copyright 2013 by Rackspace Hosting, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

import datetime
import functools
import inspect
import warnings

from falcon.util import uri


__all__ = (
    'deprecated',
    'dt_to_http',
    'http_date_to_dt',
    'to_query_str',
    'percent_escape',
    'percent_unescape',
)


# NOTE(kgriffs): We don't want our deprecations to be ignored by default,
# so create our own type.
#
# TODO(kgriffs): Revisit this decision if users complain.
class DeprecatedWarning(UserWarning):
    pass


def deprecated(instructions):
    """Flags a method as deprecated.

    Args:
        instructions: A human-friendly string of instructions, such
            as: 'Please migrate to add_proxy(...) ASAP.'
    """

    def decorator(func):
        '''This is a decorator which can be used to mark functions
        as deprecated. It will result in a warning being emitted
        when the function is used.'''
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


def dt_to_http(dt):
    """Converts a datetime instance to an HTTP date string.

    Args:
        dt: A datetime object, assumed to be UTC

    Returns:
        An HTTP date string, e.g., "Tue, 15 Nov 1994 12:45:26 GMT". See
        also: http://goo.gl/R7So4
    """

    # Tue, 15 Nov 1994 12:45:26 GMT
    return dt.strftime('%a, %d %b %Y %H:%M:%S GMT')


def http_date_to_dt(http_date):
    """Converts an HTTP date string to a datetime instance.

    Args:
        http_date: An HTTP date string, e.g., "Tue, 15 Nov 1994 12:45:26 GMT".

    Returns:
        A UTC datetime instance corresponding to the given HTTP date.
    """

    return datetime.datetime.strptime(
        http_date, '%a, %d %b %Y %H:%M:%S %Z')


def to_query_str(params):
    """Converts a dict of params to an actual query string.

    Args:
        params: dict of simple key-value types, where key is a string and
            value is a string or something that can be converted into a
            string. If value is a list, it will be converted to a comma-
            delimited string (e.g., thing=1,2,3)

    Returns:
        A URI query string starting with '?', or and empty string if there
        are no params (the dict is empty).
    """

    if not params:
        return ''

    # PERF: This is faster than a list comprehension and join, mainly
    # because it allows us to inline the value transform.
    query_str = '?'
    for k, v in params.items():
        if v is True:
            v = 'true'
        elif v is False:
            v = 'false'
        elif isinstance(v, list):
            v = ','.join(map(str, v))
        else:
            v = str(v)

        query_str += k + '=' + v + '&'

    return query_str[:-1]


# TODO(kgriffs): Remove this alias in Falcon v0.2.0
percent_escape = uri.encode

# TODO(kgriffs): Remove this alias in Falcon v0.2.0
percent_unescape = uri.decode
