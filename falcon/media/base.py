import abc

import six


@six.add_metaclass(abc.ABCMeta)
class BaseHandler(object):
    """Abstract Base Class for an internet media type handler"""

    @classmethod
    @abc.abstractmethod
    def load(cls):
        """Loads any required imports and configuration.

        Allows for implementors to specify runtime configuration
        and/or dependencies.
        """
        pass

    @classmethod
    @abc.abstractmethod
    def serialize(cls, obj):
        """Serialize the media object on a :any:`falcon.Response`

        Args:
            obj (object): A serializable object.

        Returns:
            bytes: The resulting serialized bytes from the input object.
        """
        pass

    @classmethod
    @abc.abstractmethod
    def deserialize(cls, raw):
        """Deserialize the :any:`falcon.Request` body.

        Args:
            raw (bytes): Input bytes to deserialize

        Returns:
            object: A deserialized object.
        """
        pass
