from __future__ import absolute_import  # NOTE(kgriffs): Work around a Cython bug

from typing import Union

from falcon import errors
from falcon.media.base import BaseHandler, BinaryBaseHandlerWS


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
                title='Invalid MessagePack',
                description='Could not parse MessagePack body - {0}'.format(err)
            )

    async def deserialize_async(self, stream, content_type, content_length):
        data = await stream.read()

        try:
            # NOTE(jmvrbanac): Using unpackb since we would need to manage
            # a buffer for Unpacker() which wouldn't gain us much.
            return self.msgpack.unpackb(data, raw=False)
        except ValueError as err:
            raise errors.HTTPBadRequest(
                title='Invalid MessagePack',
                description='Could not parse MessagePack body - {0}'.format(err)
            )

    def serialize(self, media, content_type):
        return self.packer.pack(media)

    async def serialize_async(self, media, content_type):
        return self.packer.pack(media)


class MessagePackHandlerWS(BinaryBaseHandlerWS):
    """WebSocket media handler for de(serializing) MessagePack to/from BINARY payloads.

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

    __slots__ = ['msgpack', 'packer']

    def __init__(self):
        try:
            import msgpack
        except ImportError:
            self.msgpack = None
            self.packer = None
        else:
            self.msgpack = msgpack
            self.packer = msgpack.Packer(autoreset=True, use_bin_type=True)

    def serialize(self, media: object) -> Union[bytes, bytearray, memoryview]:
        if not self.msgpack:
            # TODO(kgriffs): There is probably a more elegant way to handle this situation
            raise RuntimeError(
                'The default WebSocket media handler for BINARY payloads requires '
                'the msgpack package, which is not installed.'
            )

        return self.packer.pack(media)

    def deserialize(self, payload: bytes) -> object:
        if not self.msgpack:  #
            # TODO(kgriffs): There is probably a more elegant way to handle this situation
            raise RuntimeError(
                'The default WebSocket media handler for BINARY payloads requires '
                'the msgpack package, which is not installed.'
            )

        # NOTE(jmvrbanac): Using unpackb since we would need to manage
        #   a buffer for Unpacker() which wouldn't gain us much.
        return self.msgpack.unpackb(payload, raw=False)
