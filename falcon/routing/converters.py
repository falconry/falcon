# Copyright 2017 by Rackspace Hosting, Inc.
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

from datetime import datetime


# PERF(kgriffs): Avoid an extra namespace lookup when using this function
strptime = datetime.strptime


class IntConverter(object):
    """Converts a field value to an int.

    Keyword Args:
        num_digits (int): Require the value to have the given
            number of digits.
        min (int): Reject the value if it is less than this value.
        max (int): Reject the value if it is greater than this value.
    """

    __slots__ = ('_num_digits', '_min', '_max')

    def __init__(self, num_digits=None, min=None, max=None):
        if num_digits is not None and num_digits < 1:
            raise ValueError('num_digits must be at least 1')

        self._num_digits = num_digits
        self._min = min
        self._max = max

    def convert(self, fragment):
        if self._num_digits is not None and len(fragment) != self._num_digits:
            return None

        # NOTE(kgriffs): int() will accept numbers with preceding or
        # trailing whitespace, so we need to do our own check. Using
        # strip() is faster than either a regex or a series of or'd
        # membership checks via "in", esp. as the length of contiguous
        # numbers in the fragment grows.
        if fragment.strip() != fragment:
            return None

        try:
            value = int(fragment)
        except ValueError:
            return None

        if self._min is not None and value < self._min:
            return None

        if self._max is not None and value > self._max:
            return None

        return value


class DateTimeConverter(object):
    """Converts a field value to a datetime.

    Keyword Args:
        format_string (str): String used to parse the param value
            into a datetime. Any format recognized by strptime() is
            supported (default ``'%Y-%m-%dT%H:%M:%SZ'``).
    """

    __slots__ = ('_format_string',)

    def __init__(self, format_string='%Y-%m-%dT%H:%M:%SZ'):
        self._format_string = format_string

    def convert(self, fragment):
        try:
            return strptime(fragment, self._format_string)
        except ValueError:
            return None


BUILTIN = (
    ('int', IntConverter),
    ('dt', DateTimeConverter),
)
