import abc
import io


class BaseHandler(metaclass=abc.ABCMeta):
    """Abstract Base Class for an internet media type handler"""

    @abc.abstractmethod  # pragma: no cover
    def serialize(self, media, content_type):
        """Serialize the media object on a :any:`falcon.Response`

        Args:
            media (object): A serializable object.
            content_type (str): Type of response content.

        Returns:
            bytes: The resulting serialized bytes from the input object.
        """

    async def serialize_async(self, media, content_type):
        """Serialize the media object on a :any:`falcon.Response`

        This method is similar to serialize() except that it is
        asynchronous. The default implementation simply calls
        serialize(). If the media object may be awaitable, or is otherwise
        something that should be read asynchronously, subclasses
        must override the default implementation in order to handle
        that case.

        Args:
            media (object): A serializable object.
            content_type (str): Type of response content.

        Returns:
            bytes: The resulting serialized bytes from the input object.
        """
        return self.serialize(media, content_type)

    @abc.abstractmethod  # pragma: no cover
    def deserialize(self, stream, content_type, content_length):
        """Deserialize the :any:`falcon.Request` body.

        Args:
            stream (object): Readable file-like object to deserialize.
            content_type (str): Type of request content.
            content_length (int): Length of request content.

        Returns:
            object: A deserialized object.
        """

    async def deserialize_async(self, stream, content_type, content_length):
        """Deserialize the :any:`falcon.Request` body.

        This method is similar to deserialize() except that it is
        asynchronous. The default implementation adapts the synchronous
        deserialize() method via io.BytesIO. For improved performance,
        media handlers should override this method.

        Args:
            stream (object): Asynchronous file-like object to deserialize.
            content_type (str): Type of request content.
            content_length (int): Length of request content.

        Returns:
            object: A deserialized object.
        """

        data = await stream.read()
        return self.deserialize(io.BytesIO(data), content_type, content_length)
