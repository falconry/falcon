from __future__ import absolute_import

from falcon import errors
from falcon.media import BaseHandler


class JSONHandler(BaseHandler):
    """Handler built using Python's :py:mod:`json` module."""

    def load(self):
        import json
        self.json = json

    def deserialize(self, raw):
        try:
            return self.json.loads(raw.decode('utf-8'))
        except ValueError as err:
            raise errors.HTTPBadRequest(
                'Invalid JSON',
                'Could not parse JSON body - {0}'.format(err)
            )

    def serialize(self, media):
        return self.json.dumps(media, ensure_ascii=False).encode('utf-8')
