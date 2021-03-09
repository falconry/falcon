from __future__ import absolute_import  # NOTE(kgriffs): Work around a Cython bug

from typing import Union

from falcon import errors
from falcon.media.base import BaseHandler
from falcon.media.base import BinaryBaseHandlerWS


class MessagePackHandler(BaseHandler):
    """Handler built using the :py:mod:`msgpack` module.

    This handler uses ``msgpack.unpackb()`` and ``msgpack.Packer().pack()``. The
    MessagePack ``bin`` type is used to distinguish between Unicode strings
    (of type ``str``) and byte strings (of type ``bytes``).

    This handler will raise a :class:`falcon.MediaNotFoundError` when attempting
    to parse an empty body; it will raise a :class:`falcon.MediaMalformedError`
    if an error happens while parsing the body.

    Note:
        This handler requires the extra ``msgpack`` package (version 0.5.2
        or higher), which must be installed in addition to ``falcon`` from
        PyPI:

        .. code::

            $ pip install msgpack
    """

    def __init__(self):
        import msgpack

        packer = msgpack.Packer(autoreset=True, use_bin_type=True)
        self._pack = packer.pack
        self._unpackb = msgpack.unpackb

        # NOTE(kgriffs): To be safe, only enable the optimized protocol when
        #   not subclassed.
        if type(self) is MessagePackHandler:
            self._serialize_sync = self._pack
            self._deserialize_sync = self._deserialize

    def _deserialize(self, data):
        if not data:
            raise errors.MediaNotFoundError('MessagePack')
        try:
            # NOTE(jmvrbanac): Using unpackb since we would need to manage
            # a buffer for Unpacker() which wouldn't gain us much.
            return self._unpackb(data, raw=False)
        except ValueError as err:
            raise errors.MediaMalformedError('MessagePack') from err

    def deserialize(self, stream, content_type, content_length):
        return self._deserialize(stream.read())

    async def deserialize_async(self, stream, content_type, content_length):
        return self._deserialize(await stream.read())

    def serialize(self, media, content_type) -> bytes:
        return self._pack(media)

    async def serialize_async(self, media, content_type) -> bytes:
        return self._pack(media)


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
        import msgpack

        packer = msgpack.Packer(autoreset=True, use_bin_type=True)
        self._pack = packer.pack
        self._unpackb = msgpack.unpackb

    def serialize(self, media: object) -> Union[bytes, bytearray, memoryview]:
        return self._pack(media)

    def deserialize(self, payload: bytes) -> object:
        # NOTE(jmvrbanac): Using unpackb since we would need to manage
        #   a buffer for Unpacker() which wouldn't gain us much.
        return self._unpackb(payload, raw=False)
