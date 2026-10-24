import functools
from typing import IO

import falcon


class TextHandler(falcon.media.BaseHandler):
    DEFAULT_CHARSET = 'utf-8'

    @classmethod
    @functools.lru_cache
    def _get_charset(cls, content_type: str) -> str:
        _, params = falcon.parse_header(content_type)
        return params.get('charset') or cls.DEFAULT_CHARSET

    def deserialize(
        self, stream: IO[bytes], content_type: str, content_length: int
    ) -> str:
        data = stream.read()
        return data.decode(self._get_charset(content_type))

    def serialize(self, media: str, content_type: str) -> bytes:
        return media.encode(self._get_charset(content_type))
