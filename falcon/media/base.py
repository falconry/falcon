import abc

import six


@six.add_metaclass(abc.ABCMeta)
class BaseHandler(object):
    """Abstract Base Class for an internet media type handler"""

    @abc.abstractmethod  # pragma: no cover
    def serialize(self, obj):
        """Serialize the media object on a :any:`falcon.Response`

        Args:
            obj (object): A serializable object.

        Returns:
            bytes: The resulting serialized bytes from the input object.
        """

    @abc.abstractmethod  # pragma: no cover
    def deserialize(self, raw):
        """Deserialize the :any:`falcon.Request` body.

        Args:
            raw (bytes): Input bytes to deserialize

        Returns:
            object: A deserialized object.
        """
