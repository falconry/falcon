"""Includes private helpers for the Response class.

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


def header_property(name, doc, transform=None):
    """Creates a header getter/setter.

    Args:
        name: Header name, e.g., "Content-Type"
        doc: Docstring for the property
        transform: Transformation function to use when setting the
            property. The value will be passed to the function, and
            the function should return the transformed value to use
            as the value of the header (default None)

    """
    normalized_name = name.lower()

    def fget(self):
        try:
            return self._headers[normalized_name]
        except KeyError:
            return None

    if transform is None:
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
        value: Tuple passed to req.range

    """

    # PERF: Concatenation is faster than % string formatting as well
    #       as ''.join() in this case.
    return ('bytes ' +
            str(value[0]) + '-' +
            str(value[1]) + '/' +
            str(value[2]))
