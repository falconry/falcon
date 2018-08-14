from __future__ import absolute_import

import six

from falcon import errors
from falcon.media import BaseHandler
from falcon.util import json


class JSONHandler(BaseHandler):
    """JSON media handler.

    JSONHandler uses :py:mod:`mujson` to find the most performant JSON
    functions available at import time. This behavior can be overriden by
    explicitly passing desired implementations for ``dumps`` and/or ``loads``.

    Keyword Arguments:
        dumps (func): Use this argument to explicitly specify the
            ``json.dumps``-like function to use during serialization. If not
            passed, ``JSONHandler`` will attempt to use the most performant
            ``json-dumps``-like function available at import time.
        dumps_default (func): function, if any, to pass as ``default`` keyword
            argument to ``dumps``. Use of this argument may impair performance
            when serializing JSON payloads.
        dumps_ensure_ascii (bool): value to pass as ``ensure_ascii`` keyword
            argument to ``dumps``. (default ``False``)
        loads (func): Use this argument to explicitly specify the
            ``json.loads``-like function to use during deserialization.
        loads_object_hook (func): function, if any, to pass as ``object_hook``
            keyword argument to ``loads``. Use of this argument may impair
            performance when deserializing JSON payloads.
    """
    def __init__(self, dumps=None, dumps_default=None,
                 dumps_ensure_ascii=False, loads=None,
                 loads_object_hook=None):
        self.dumps_kwargs = {'ensure_ascii': dumps_ensure_ascii}
        self.loads_kwargs = {}

        if dumps_default is not None:
            self.dumps = dumps or json.compliant_dumps
            self.dumps_kwargs['default'] = dumps_default
        else:
            self.dumps = dumps or json.dumps

        if loads_object_hook is not None:
            self.loads = loads or json.compliant_loads
            self.loads_kwargs['object_hook'] = loads_object_hook
        else:
            self.loads = loads or json.loads

    def deserialize(self, stream, content_type, content_length):
        try:
            return self.loads(
                stream.read().decode('utf-8'),
                **self.loads_kwargs)
        except ValueError as err:
            raise errors.HTTPBadRequest(
                'Invalid JSON',
                'Could not parse JSON body - {0}'.format(err)
            )

    def serialize(self, media, content_type):
        result = self.dumps(media, **self.dumps_kwargs)
        if six.PY3 or not isinstance(result, bytes):
            return result.encode('utf-8')

        return result
