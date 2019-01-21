import operator as op
import sys
import types


PY2 = sys.version_info.major == 2
PY3 = sys.version_info.major == 3


if PY3:
    from http import cookies as http_cookies  # NOQA: F401
    from collections import UserDict  # NOQA: F401
    from io import StringIO  # NOQA: F401
    from urllib.parse import quote, unquote_plus  # NOQA: F401

    string_types = (str,)
    class_types = (type,)
    text_type = str

    get_method_self = op.attrgetter('__self__')
else:
    import Cookie as http_cookies  # NOQA: F401
    from UserDict import UserDict  # NOQA: F401
    from StringIO import StringIO  # NOQA: F401
    from urllib import quote, unquote_plus  # NOQA: F401

    string_types = (basestring,)
    class_types = (type, types.ClassType)
    text_type = unicode

    get_method_self = op.attrgetter('im_self')


def add_metaclass(metaclass):
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
