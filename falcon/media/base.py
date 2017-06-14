import abc

import six


@six.add_metaclass(abc.ABCMeta)
class BaseHandler(object):
    """Abstract Base Class for an internet media type handler"""

    @abc.abstractmethod
    def load(self):
        """Loads any required imports and configuration.

        Allows for implementors to specify runtime configuration
        and/or dependencies.
        """

    @abc.abstractmethod
    def serialize(self, obj):
        """Serialize the media object on a :any:`falcon.Response`

        Args:
            obj (object): A serializable object.

        Returns:
            bytes: The resulting serialized bytes from the input object.
        """

    @abc.abstractmethod
    def deserialize(self, raw):
        """Deserialize the :any:`falcon.Request` body.

        Args:
            raw (bytes): Input bytes to deserialize

        Returns:
            object: A deserialized object.
        """
