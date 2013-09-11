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
import six

if six.PY3:  # pragma nocover
    from urllib.parse import quote as url_quote
else:  # pragma nocover
    from urllib import quote as url_quote


__all__ = ('dt_to_http', 'http_date_to_dt', 'to_query_str', 'percent_escape')


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
    """Converts a dict of params to afaln actual query string.

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
            # PERF(kgriffs): map is faster than list comprehension in
            # py26 and py33. No significant different in py27
            v = ','.join(map(str, v))
        else:
            v = str(v)

        query_str += k + '=' + v + '&'

    return query_str[:-1]


def percent_escape(url):
    """Percent-escape reserved characters in the given url.

    Args:
        url: A full or relative URL.

    Returns:
        An escaped version of the URL, excluding '/', ',' and ':'
        characters. In Python 2, unicode URL strings will be first
        encoded to a UTF-8 byte string to work around a urllib
        bug.
    """

    # Convert the string so that urllib.quote does not complain
    # if it actually has Unicode chars in it.
    if not six.PY3 and isinstance(url, six.text_type):  # pragma nocover
        url = url.encode('utf-8')

    return url_quote(url, safe='/:,=?&-_')
