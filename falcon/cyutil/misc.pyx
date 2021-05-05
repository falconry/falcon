# Copyright 2020-2021 by Vytautas Liuolia.
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


def isascii(unicode string not None):
    """Return ``True`` if all characters in the string are ASCII.

    ASCII characters have code points in the range U+0000-U+007F.

    Note:
        On Python 3.7+, this function is just aliased to ``str.isascii``.

    This is a Cython fallback for older CPython versions. For longer strings,
    it is slightly less performant than the built-in ``str.isascii``.

    Args:
        string (str): A string to test.

    Returns:
        ``True`` if all characters are ASCII, ``False`` otherwise.
    """

    cdef Py_UCS4 ch

    for ch in string:
        if ch > 0x007F:
            return False

    return True


def encode_items_to_latin1(dict data not None):
    cdef list result = []
    cdef unicode key
    cdef unicode value

    for key, value in data.items():
        result.append((key.encode('latin1'), value.encode('latin1')))

    return result
