import operator as op
import sys
import types


PY2 = sys.version_info.major == 2
PY3 = sys.version_info.major == 3


if PY3:
    from http import cookies as http_cookies  # NOQA: F401
    from collections import UserDict  # NOQA: F401
    from collections.abc import Mapping, MutableMapping  # NOQA: F401
    from io import StringIO  # NOQA: F401
    from urllib.parse import quote, unquote_plus  # NOQA: F401

    string_types = (str,)
    class_types = (type,)
    text_type = str

    get_method_self = op.attrgetter('__self__')
else:
    from collections import Mapping, MutableMapping  # NOQA: F401
    import Cookie as http_cookies  # NOQA: F401
    from UserDict import UserDict  # NOQA: F401
    from StringIO import StringIO  # NOQA: F401
    from urllib import quote, unquote_plus  # NOQA: F401

    string_types = (basestring,)
    class_types = (type, types.ClassType)
    text_type = unicode

    get_method_self = op.attrgetter('im_self')


# ------------------------------------------------------------------------------
# Method: add_metaclass()
# Source: https://github.com/benjaminp/six
#
# Copyright (c) 2010-2018 Benjamin Peterson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ------------------------------------------------------------------------------
def add_metaclass(metaclass):  # pragma: nocover
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        slots = orig_vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                orig_vars.pop(slots_var)
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        if hasattr(cls, '__qualname__'):
            orig_vars['__qualname__'] = cls.__qualname__
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper
# ------------------------------------------------------------------------------
