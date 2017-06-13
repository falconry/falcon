import mimeparse
from six.moves import UserDict

from falcon import errors


class Handlers(UserDict):
    """Manages media type handlers.

    Attempts to load any imports for handlers as they are added.
    """
    def __init__(self, initial=None):
        handlers = initial or {
            'application/json': Json,
            'application/json; charset=UTF-8': Json
        }

        # NOTE(jmvrbanac): Directly calling UserDict as it's not inheritable.
        # Also, this results in self.update(...) being called.
        UserDict.__init__(self, handlers)

    def update(self, input_dict):
        for handler in input_dict.values():
            handler.load()

        UserDict.update(self, input_dict)

    def __setitem__(self, key, item):
        if not key:
            raise ValueError('Media Type cannot be None or an empty string')

        item.load()
        self.data[key] = item

    def _resolve_media_type(self, media_type, all_media_types):
        resolved = None

        try:
            resolved = mimeparse.best_match(
                all_media_types,
                media_type
            )
        except ValueError:
            pass

        return resolved

    def find_by_media_type(self, media_type, default):
        # PERF(jmvrbanac): Check via a quick methods first for performance
        try:
            return self.data[media_type]
        except KeyError:
            pass

        if media_type == '*/*' or not media_type:
            return self.data[default]

        # PERF(jmvrbanac): Fallback to the slower method
        resolved = self._resolve_media_type(media_type, self.data.keys())

        # NOTE(jmvrbanac): Mimeparse will return an empty string if it can
        # parse the media type, but cannot find a suitable type.
        if not resolved:
            raise errors.HTTPUnsupportedMediaType(
                '{0} is an unsupported media type.'.format(media_type)
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
        except ValueError as err:
            raise errors.HTTPBadRequest(
                'Invalid JSON',
                'Could not parse JSON body - {0}'.format(err)
            )

    @classmethod
    def serialize(cls, media):
        return cls.json.dumps(media)


class MessagePack(object):
    @classmethod
    def load(cls):
        import msgpack

        cls.msgpack = msgpack
        cls.packer = msgpack.Packer(
            encoding='utf-8',
            autoreset=True,
            use_bin_type=True,
        )

    @classmethod
    def deserialize(cls, raw):
        try:
            # NOTE(jmvrbanac): Using unpackb since we would need to manage
            # a bytes buffer anyhow, so we might as well just create a
            # new instance for the time being.
            return cls.msgpack.unpackb(raw)
        except ValueError as err:
            raise errors.HTTPBadRequest(
                'Invalid MessagePack',
                'Could not parse MessagePack body - {0}'.format(err)
            )

    @classmethod
    def serialize(cls, media):
        return cls.packer.pack(media)
