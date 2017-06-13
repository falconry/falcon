from __future__ import absolute_import

from falcon import errors
from falcon.media import BaseHandler


class JSONHandler(BaseHandler):
    @classmethod
    def load(cls):
        import json
        cls.json = json

    @classmethod
    def deserialize(cls, raw):
        try:
            return cls.json.loads(raw.decode('utf-8'))
        except ValueError as err:
            raise errors.HTTPBadRequest(
                'Invalid JSON',
                'Could not parse JSON body - {0}'.format(err)
            )

    @classmethod
    def serialize(cls, media):
        return cls.json.dumps(media, ensure_ascii=False).encode('utf-8')
