from __future__ import absolute_import

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

            Warning: Specifying this method will significantly increase the
            time it takes to process JSON documents.

    """

    __slots__ = ('_default',)

    def __init__(self, default=None):
        self._default = default

    def deserialize(self, raw):
        try:
            return json.loads(raw.decode('utf-8'))
        except ValueError as err:
            raise errors.HTTPBadRequest(
                'Invalid JSON',
                'Could not parse JSON body - {0}'.format(err)
            )

    def serialize(self, media):
        result = json.dumps(media, ensure_ascii=False, default=self._default)
        if six.PY3 or not isinstance(result, bytes):
            return result.encode('utf-8')

        return result
