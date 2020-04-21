from collections import UserDict

from falcon import errors
from falcon.constants import MEDIA_MULTIPART, MEDIA_URLENCODED
from falcon.media.json import JSONHandler
from falcon.media.multipart import MultipartFormHandler, MultipartParseOptions
from falcon.media.urlencoded import URLEncodedFormHandler
from falcon.vendor import mimeparse


class Handlers(UserDict):
    """A :class:`dict`-like object that manages Internet media type handlers."""
    def __init__(self, initial=None):
        handlers = initial or {
            'application/json': JSONHandler(),
            'application/json; charset=UTF-8': JSONHandler(),
            MEDIA_MULTIPART: MultipartFormHandler(),
            MEDIA_URLENCODED: URLEncodedFormHandler(),
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
            media_type = default

        try:
            return self.data[media_type]
        except KeyError:
            pass

        # PERF(jmvrbanac): Fallback to the slower method
        resolved = self._resolve_media_type(media_type, self.data.keys())

        if not resolved:
            raise errors.HTTPUnsupportedMediaType(
                description='{0} is an unsupported media type.'.format(media_type)
            )

        return self.data[resolved]


# NOTE(vytas): An ugly way to work around circular imports.
MultipartParseOptions._DEFAULT_HANDLERS = Handlers({
    'application/json': JSONHandler(),
    'application/json; charset=UTF-8': JSONHandler(),
    MEDIA_URLENCODED: URLEncodedFormHandler(),
})  # type: ignore
