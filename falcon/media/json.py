from __future__ import absolute_import
import pkgutil

import six

from falcon import errors
from falcon.media import BaseHandler
from falcon.util import json


class JSONHandler(BaseHandler):
    """Handler built using Python's :py:mod:`json` module.

    Keyword Arguments:
        default (callable): A callable taking the form ``func(object)`` which
            will be called to handle serializing objects which can't be
            otherwise serialized.

            Warning:
                Specifying this method will significantly increase the
                time it takes to process JSON documents.

            Note:
                This argument may not be specified if ujson is installed, for
                compatibility reasons.

        object_hook (callable): A callable taking the form ``func(dict)``
            which will provide an object to be used instead of the dict
            produced when JSON is deserialized.

            Warning:
                Specifying this method will significantly increase the
                time it takes to process JSON documents.

            Note:
                This argument may not be specified if ujson is installed, for
                compatibility reasons.

    """

    __slots__ = ('_default', '_object_hook')

    def __init__(self, default=None, object_hook=None):
        ujson = pkgutil.find_loader('ujson') is not None

        if default and ujson:
            raise(TypeError(
                'Specifying default is not compatible with ujson.'))
        if object_hook and ujson:
            raise(TypeError(
                'Specifying object_hook is not compatible with ujson.'))

        self._default_arg = {} if ujson else {'default': default}
        self._object_hook_arg = {} if ujson else {'object_hook': object_hook}

    def deserialize(self, raw):
        try:
            return json.loads(raw.decode('utf-8'), **self._object_hook_arg)
        except ValueError as err:
            raise errors.HTTPBadRequest(
                'Invalid JSON',
                'Could not parse JSON body - {0}'.format(err)
            )

    def serialize(self, media):
        result = json.dumps(media, ensure_ascii=False, **self._default_arg)
        if six.PY3 or not isinstance(result, bytes):
            return result.encode('utf-8')

        return result
