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
