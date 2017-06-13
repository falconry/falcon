from __future__ import absolute_import

from falcon import errors
from falcon.media import BaseHandler


class MessagePackHandler(BaseHandler):
    @classmethod
    def load(cls):
        import msgpack

        cls.msgpack = msgpack
        cls.packer = msgpack.Packer(
            encoding='utf-8',
            autoreset=True,
            use_bin_type=True,
        )

    @classmethod
    def deserialize(cls, raw):
        try:
            # NOTE(jmvrbanac): Using unpackb since we would need to manage
            # a buffer for Unpacker() which wouldn't gain us much.
            return cls.msgpack.unpackb(raw)
        except ValueError as err:
            raise errors.HTTPBadRequest(
                'Invalid MessagePack',
                'Could not parse MessagePack body - {0}'.format(err)
            )

    @classmethod
    def serialize(cls, media):
        return cls.packer.pack(media)
