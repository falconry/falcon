import abc

from falcon.util import compat


@compat.add_metaclass(abc.ABCMeta)
class BaseHandler(object):
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

    @abc.abstractmethod  # pragma: no cover
    def deserialize(self, stream, content_type, content_length):
        """Deserialize the :any:`falcon.Request` body.

        Args:
            stream (object): Input data to deserialize.
            content_type (str): Type of request content.
            content_length (int): Length of request content.

        Returns:
            object: A deserialized object.
        """
