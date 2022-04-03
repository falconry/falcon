# Copyright 2019 by Kurt Griffiths
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


def header_property(header_name):
    """Create a read-only header property.

    Args:
        wsgi_name (str): Case-sensitive name of the header as it would
            appear in the WSGI environ ``dict`` (i.e., 'HTTP_*')

    Returns:
        A property instance than can be assigned to a class variable.

    """

    header_name = header_name.lower().encode()

    def fget(self):
        try:
            # NOTE(vytas): Supporting ISO-8859-1 for historical reasons as per
            #   RFC 7230, Section 3.2.4; and to strive for maximum
            #   compatibility with WSGI.
            return self._asgi_headers[header_name].decode('latin1') or None
        except KeyError:
            return None

    return property(fget)
