import abc
import io


class BaseHandler(metaclass=abc.ABCMeta):
    """Abstract Base Class for an internet media type handler"""

    def serialize(self, media, content_type):
        """Serialize the media object on a :any:`falcon.Response`

        By default, this method raises an instance of
        :py:class:`NotImplementedError`. Therefore, it must be
        overridden in order to work with WSGI apps. Child classes
        can ignore this method if they are only to be used
        with ASGI apps, as long as they override
        :py:meth:`~.BaseHandler.serialize_async`.

        Args:
            media (object): A serializable object.
            content_type (str): Type of response content.

        Returns:
            bytes: The resulting serialized bytes from the input object.
        """
        raise NotImplementedError()

    async def serialize_async(self, media, content_type):
        """Serialize the media object on a :any:`falcon.Response`

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

    def deserialize(self, stream, content_type, content_length):
        """Deserialize the :any:`falcon.Request` body.

        By default, this method raises an instance of
        :py:class:`NotImplementedError`. Therefore, it must be
        overridden in order to work with WSGI apps. Child classes
        can ignore this method if they are only to be used
        with ASGI apps, as long as they override
        :py:meth:`~.BaseHandler.deserialize_async`.


        Args:
            stream (object): Readable file-like object to deserialize.
            content_type (str): Type of request content.
            content_length (int): Length of request content.

        Returns:
            object: A deserialized object.
        """
        raise NotImplementedError()

    async def deserialize_async(self, stream, content_type, content_length):
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
    """Whether to exhaust the WSGI input stream upon finishing deserialization.

    Exhausting the stream may be useful for handlers that do not necessarily
    consume the whole stream, but the deserialized media object is complete and
    does not involve further streaming.
    """
