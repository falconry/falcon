from __future__ import absolute_import

import six

from falcon import errors
from falcon.media import BaseHandler
from falcon.util import json


class JSONHandler(BaseHandler):
    """JSON media handler.

    This handler uses Python's :py:mod:`json` by default, but will
    use :py:mod:`ujson` if available.
    """

    def deserialize(self, stream, content_type, content_length):
        try:
            return json.loads(stream.read().decode('utf-8'))
        except ValueError as err:
            raise errors.HTTPBadRequest(
                'Invalid JSON',
                'Could not parse JSON body - {0}'.format(err)
            )

    def serialize(self, media, content_type):
        result = json.dumps(media, ensure_ascii=False)
        if six.PY3 or not isinstance(result, bytes):
            return result.encode('utf-8')

        return result
