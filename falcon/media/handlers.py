from falcon import errors
from falcon.media import JSONHandler
from falcon.util.compat import UserDict
from falcon.vendor import mimeparse


class Handlers(UserDict):
    """A dictionary like object that manages internet media type handlers."""
    def __init__(self, initial=None):
        handlers = initial or {
            'application/json': JSONHandler(),
            'application/json; charset=UTF-8': JSONHandler(),
        }

        # NOTE(jmvrbanac): Directly calling UserDict as it's not inheritable.
        # Also, this results in self.update(...) being called.
        UserDict.__init__(self, handlers)

    def _resolve_media_type(self, media_type, all_media_types):
        resolved = None

        try:
            # NOTE(jmvrbanac): Mimeparse will return an empty string if it can
            # parse the media type, but cannot find a suitable type.
            resolved = mimeparse.best_match(
                all_media_types,
                media_type
            )
        except ValueError:
            pass

        return resolved

    def find_by_media_type(self, media_type, default):
        # PERF(jmvrbanac): Check via a quick methods first for performance
        if media_type == '*/*' or not media_type:
            return self.data[default]

        try:
            return self.data[media_type]
        except KeyError:
            pass

        # PERF(jmvrbanac): Fallback to the slower method
        resolved = self._resolve_media_type(media_type, self.data.keys())

        if not resolved:
            raise errors.HTTPUnsupportedMediaType(
                '{0} is an unsupported media type.'.format(media_type)
            )

        return self.data[resolved]
