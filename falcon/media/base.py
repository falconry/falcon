import abc
import io
from typing import Union

from falcon.constants import MEDIA_JSON


class BaseHandler(metaclass=abc.ABCMeta):
    """Abstract Base Class for an internet media type handler."""

    # NOTE(kgriffs): The following special methods are used to enable an
    #   optimized media (de)serialization protocol for ASGI. This is not
    #   currently part of the public interface for Falcon, and is not
    #   included in the docs. Once we are happy with the protocol, we
    #   might make it part of the public interface for use by custom
    #   media type handlers.

    _serialize_sync = None
    """Override to provide a synchronous serialization method that takes an object."""

    _deserialize_sync = None
    """Override to provide a synchronous deserialization method that takes a byte string."""

    def serialize(self, media, content_type) -> bytes:
        """Serialize the media object on a :any:`falcon.Response`.

        By default, this method raises an instance of
        :py:class:`NotImplementedError`. Therefore, it must be
        overridden in order to work with WSGI apps. Child classes
        can ignore this method if they are only to be used
        with ASGI apps, as long as they override
        :py:meth:`~.BaseHandler.serialize_async`.

        Note:

            The JSON media handler is an exception in requiring the implementation of
            the sync version also for ASGI apps. See the
            :ref:`this section<note_json_handler>` for more details.

        Args:
            media (object): A serializable object.
            content_type (str): Type of response content.

        Returns:
            bytes: The resulting serialized bytes from the input object.
        """
        if MEDIA_JSON in content_type:
            raise NotImplementedError(
                'The JSON media handler requires the sync interface to be implemented even in '
                "ASGI applications, because it's used internally by the Falcon framework."
            )
        else:
            raise NotImplementedError()

    async def serialize_async(self, media, content_type) -> bytes:
        """Serialize the media object on a :any:`falcon.Response`.

        This method is similar to :py:meth:`~.BaseHandler.serialize`
        except that it is asynchronous. The default implementation simply calls
        :py:meth:`~.BaseHandler.serialize`. If the media object may be
        awaitable, or is otherwise something that should be read
        asynchronously, subclasses must override the default implementation
        in order to handle that case.

        Note:
            By default, the :py:meth:`~.BaseHandler.serialize`
            method raises an instance of :py:class:`NotImplementedError`.
            Therefore, child classes must either override
            :py:meth:`~.BaseHandler.serialize` or
            :py:meth:`~.BaseHandler.serialize_async` in order to be
            compatible with ASGI apps.

        Args:
            media (object): A serializable object.
            content_type (str): Type of response content.

        Returns:
            bytes: The resulting serialized bytes from the input object.
        """
        return self.serialize(media, content_type)

    def deserialize(self, stream, content_type, content_length) -> object:
        """Deserialize the :any:`falcon.Request` body.

        By default, this method raises an instance of
        :py:class:`NotImplementedError`. Therefore, it must be
        overridden in order to work with WSGI apps. Child classes
        can ignore this method if they are only to be used
        with ASGI apps, as long as they override
        :py:meth:`~.BaseHandler.deserialize_async`.

        Note:

            The JSON media handler is an exception in requiring the implementation of
            the sync version also for ASGI apps. See the
            :ref:`this section<note_json_handler>` for more details.

        Args:
            stream (object): Readable file-like object to deserialize.
            content_type (str): Type of request content.
            content_length (int): Length of request content.

        Returns:
            object: A deserialized object.
        """
        if MEDIA_JSON in content_type:
            raise NotImplementedError(
                'The JSON media handler requires the sync interface to be implemented even in '
                "ASGI applications, because it's used internally by the Falcon framework."
            )
        else:
            raise NotImplementedError()

    async def deserialize_async(self, stream, content_type, content_length) -> object:
        """Deserialize the :any:`falcon.Request` body.

        This method is similar to :py:meth:`~.BaseHandler.deserialize` except
        that it is asynchronous. The default implementation adapts the
        synchronous :py:meth:`~.BaseHandler.deserialize` method
        via :py:class:`io.BytesIO`. For improved performance, media handlers should
        override this method.

        Note:
            By default, the :py:meth:`~.BaseHandler.deserialize`
            method raises an instance of :py:class:`NotImplementedError`.
            Therefore, child classes must either override
            :py:meth:`~.BaseHandler.deserialize` or
            :py:meth:`~.BaseHandler.deserialize_async` in order to be
            compatible with ASGI apps.

        Args:
            stream (object): Asynchronous file-like object to deserialize.
            content_type (str): Type of request content.
            content_length (int): Length of request content.

        Returns:
            object: A deserialized object.
        """
        data = await stream.read()

        # NOTE(kgriffs): Override content length to make sure it is correct,
        #   since we know what it is in this case.
        content_length = len(data)

        return self.deserialize(io.BytesIO(data), content_type, content_length)

    exhaust_stream = False
    """Whether to exhaust the input stream upon finishing deserialization.

    Exhausting the stream may be useful for handlers that do not necessarily
    consume the whole stream, but the deserialized media object is complete and
    does not involve further streaming.
    """


class TextBaseHandlerWS(metaclass=abc.ABCMeta):
    """Abstract Base Class for a WebSocket TEXT media handler."""

    def serialize(self, media: object) -> str:
        """Serialize the media object to a Unicode string.

        By default, this method raises an instance of
        :py:class:`NotImplementedError`. Therefore, it must be
        overridden if the child class wishes to support
        serialization to TEXT (0x01) message payloads.

        Args:
            media (object): A serializable object.

        Returns:
            str: The resulting serialized string from the input object.
        """
        raise NotImplementedError()

    def deserialize(self, payload: str) -> object:
        """Deserialize TEXT payloads from a Unicode string.

        By default, this method raises an instance of
        :py:class:`NotImplementedError`. Therefore, it must be
        overridden if the child class wishes to support
        deserialization from TEXT (0x01) message payloads.

        Args:
            payload (str): Message payload to deserialize.

        Returns:
            object: A deserialized object.
        """
        raise NotImplementedError()


class BinaryBaseHandlerWS(metaclass=abc.ABCMeta):
    """Abstract Base Class for a WebSocket BINARY media handler."""

    def serialize(self, media: object) -> Union[bytes, bytearray, memoryview]:
        """Serialize the media object to a byte string.

        By default, this method raises an instance of
        :py:class:`NotImplementedError`. Therefore, it must be
        overridden if the child class wishes to support
        serialization to BINARY (0x02) message payloads.

        Args:
            media (object): A serializable object.

        Returns:
            bytes: The resulting serialized byte string from the input
            object. May be an instance of :class:`bytes`,
            :class:`bytearray`, or :class:`memoryview`.
        """
        raise NotImplementedError()

    def deserialize(self, payload: bytes) -> object:
        """Deserialize BINARY payloads from a byte string.

        By default, this method raises an instance of
        :py:class:`NotImplementedError`. Therefore, it must be
        overridden if the child class wishes to support
        deserialization from BINARY (0x02) message payloads.

        Args:
            payload (bytes): Message payload to deserialize.

        Returns:
            object: A deserialized object.
        """
        raise NotImplementedError()
