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

"""Utilities for the Response class."""

import six


def header_property(name, doc, transform=None):
    """Creates a header getter/setter.

    Args:
        name: Header name, e.g., "Content-Type"
        doc: Docstring for the property
        transform: Transformation function to use when setting the
            property. The value will be passed to the function, and
            the function should return the transformed value to use
            as the value of the header (default ``None``).

    """
    normalized_name = name.lower()

    def fget(self):
        try:
            return self._headers[normalized_name]
        except KeyError:
            return None

    if transform is None:
        if six.PY2:
            def fset(self, value):
                self._headers[normalized_name] = str(value)
        else:
            def fset(self, value):
                self._headers[normalized_name] = value
    else:
        def fset(self, value):
            self._headers[normalized_name] = transform(value)

    def fdel(self):
        del self._headers[normalized_name]

    return property(fget, fset, fdel, doc)


def format_range(value):
    """Formats a range header tuple per the HTTP spec.

    Args:
        value: ``tuple`` passed to `req.range`
    """

    # PERF(kgriffs): % was found to be faster than str.format(),
    # string concatenation, and str.join() in this case.

    if len(value) == 4:
        result = '%s %s-%s/%s' % (value[3], value[0], value[1], value[2])
    else:
        result = 'bytes %s-%s/%s' % (value[0], value[1], value[2])

    if six.PY2:
        # NOTE(kgriffs): In case one of the values was a unicode
        # string, convert back to str
        result = str(result)

    return result


if six.PY2:
    def format_header_value_list(iterable):
        """Joins an iterable of strings with commas."""
        return str(', '.join(iterable))
else:
    def format_header_value_list(iterable):
        """Joins an iterable of strings with commas."""
        return ', '.join(iterable)


def is_ascii_encodable(s):
    """Check if argument encodes to ascii without error."""
    try:
        s.encode('ascii')
    except UnicodeEncodeError:
        # NOTE(tbug): Py2 and Py3 will raise this if string contained
        # chars that could not be ascii encoded
        return False
    except UnicodeDecodeError:
        # NOTE(tbug): py2 will raise this if type is str
        # and contains non-ascii chars
        return False
    except AttributeError:
        # NOTE(tbug): s is probably not a string type
        return False
    return True
