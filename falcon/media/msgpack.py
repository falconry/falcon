from __future__ import absolute_import

from falcon import errors
from falcon.media import BaseHandler


class MessagePackHandler(BaseHandler):
    """Handler built using the :py:mod:`msgpack` module from python-msgpack

    Note:
        This handler uses the `bin` type option which expects bytes instead
        of strings.

    Note:
        This handler requires the ``python-msgpack`` package to be installed.
    """

    def __init__(self):
        import msgpack

        self.msgpack = msgpack
        self.packer = msgpack.Packer(
            encoding='utf-8',
            autoreset=True,
            use_bin_type=True,
        )

    def deserialize(self, raw):
        try:
            # NOTE(jmvrbanac): Using unpackb since we would need to manage
            # a buffer for Unpacker() which wouldn't gain us much.
            return self.msgpack.unpackb(raw, encoding='utf-8')
        except ValueError as err:
            raise errors.HTTPBadRequest(
                'Invalid MessagePack',
                'Could not parse MessagePack body - {0}'.format(err)
            )

    def serialize(self, media):
        return self.packer.pack(media)
