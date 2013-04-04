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
    return datetime.datetime.strptime(
        http_date, '%a, %d %b %Y %H:%M:%S %Z')


def to_query_str(params):
    """Converts a dict of params to an actual query string.

    Args:
        params: dict of simple key-value types, where key is a string and
            value is a string or something that can be converted into a
            string.

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
        else:
            v = str(v)

        query_str += k + '=' + v + '&'

    return query_str[:-1]
