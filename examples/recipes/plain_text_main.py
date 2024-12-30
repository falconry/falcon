import functools

import falcon


class TextHandler(falcon.media.BaseHandler):
    DEFAULT_CHARSET = 'utf-8'

    @classmethod
    @functools.lru_cache
    def _get_charset(cls, content_type):
        _, params = falcon.parse_header(content_type)
        return params.get('charset') or cls.DEFAULT_CHARSET

    def deserialize(self, stream, content_type, content_length):
        data = stream.read()
        return data.decode(self._get_charset(content_type))

    def serialize(self, media, content_type):
        return media.encode(self._get_charset(content_type))
