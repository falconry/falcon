from msgspec import msgpack

from falcon import media
from falcon.typing import ReadableIO


class MsgspecMessagePackHandler(media.BaseHandler):
    def deserialize(
        self,
        stream: ReadableIO,
        content_type: str | None,
        content_length: int | None,
    ) -> object:
        return msgpack.decode(stream.read())

    def serialize(self, media: object, content_type: str) -> bytes:
        return msgpack.encode(media)


msgpack_handler = MsgspecMessagePackHandler()
