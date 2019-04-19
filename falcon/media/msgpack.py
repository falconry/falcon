from __future__ import absolute_import  # NOTE(kgriffs): Work around a Cython bug

from falcon import errors
from falcon.media import BaseHandler


class MessagePackHandler(BaseHandler):
    """Handler built using the :py:mod:`msgpack` module.

    This handler uses ``msgpack.unpackb()`` and ``msgpack.packb()``. The
    MessagePack ``bin`` type is used to distinguish between Unicode strings
    (of type ``str``) and byte strings (of type ``bytes``).

    Note:
        This handler requires the extra ``msgpack`` package (version 0.5.2
        or higher), which must be installed in addition to ``falcon`` from
        PyPI:

        .. code::

            $ pip install msgpack
    """

    def __init__(self):
        import msgpack

        self.msgpack = msgpack
        self.packer = msgpack.Packer(
            autoreset=True,
            use_bin_type=True,
        )

    def deserialize(self, stream, content_type, content_length):
        try:
            # NOTE(jmvrbanac): Using unpackb since we would need to manage
            # a buffer for Unpacker() which wouldn't gain us much.
            return self.msgpack.unpackb(stream.read(), raw=False)
        except ValueError as err:
            raise errors.HTTPBadRequest(
                'Invalid MessagePack',
                'Could not parse MessagePack body - {0}'.format(err)
            )

    def serialize(self, media, content_type):
        return self.packer.pack(media)
