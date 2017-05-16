import mimeparse
from six.moves import UserDict

from falcon import errors


class Handlers(UserDict):
    """Manages Media Type Handlers.

    Attempts to load any imports for handlers as they are added.
    """
    def __init__(self, initial=None):
        handlers = initial or {'application/json; charset=UTF-8': Json}

        # Directly calling UserDict as it's not inheritable.
        UserDict.__init__(self, handlers)

    def update(self, input_dict):
        for handler in input_dict.values():
            handler.load()

        UserDict.update(self, input_dict)

    def __setitem__(self, key, item):
        item.load()
        self.data[key] = item

    def find_by_media_type(self, media_type, default):
        supported_media_types = self.data.keys()
        resolved = None

        # Check via a quick methods first for performance
        if media_type in supported_media_types:
            resolved = media_type

        elif media_type == '*/*' or not media_type:
            resolved = default

        # Fallback to the slower method
        else:
            try:
                resolved = mimeparse.best_match(
                    supported_media_types,
                    media_type
                )
            except:
                pass

        if not resolved:
            raise errors.HTTPUnsupportedMediaType(
                '{0} is a unsupported media type.'.format(media_type)
            )

        return self.data[resolved]


class Json(object):
    @classmethod
    def load(cls):
        import json
        cls.json = json

    @classmethod
    def deserialize(cls, raw):
        try:
            return cls.json.loads(raw.decode('utf-8'))
        except ValueError:
            raise errors.HTTPBadRequest(
                'Invalid JSON',
                'Could not parse JSON body'
            )

    @classmethod
    def serialize(cls, media):
        return cls.json.dumps(media)


class MessagePack(object):
    @classmethod
    def load(cls):
        import msgpack
        cls.msgpack = msgpack

    @classmethod
    def deserialize(cls, raw):
        try:
            return cls.msgpack.unpackb(raw)
        except ValueError:
            raise errors.HTTPBadRequest(
                'Invalid MessagePack',
                'Could not parse MessagePack body'
            )

    @classmethod
    def serialize(cls, media):
        return cls.msgpack.packb(media)
