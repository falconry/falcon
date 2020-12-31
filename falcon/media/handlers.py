from collections import UserDict

from falcon import errors
from falcon.constants import MEDIA_JSON, MEDIA_MULTIPART, MEDIA_URLENCODED
from falcon.media.json import JSONHandler
from falcon.media.multipart import MultipartFormHandler, MultipartParseOptions
from falcon.media.urlencoded import URLEncodedFormHandler
from falcon.vendor import mimeparse


class MissingDependencyHandler:
    """Placeholder handler that always raises an error.

    This handler is used by the framework for media types that require an
    external dependency that can not be found.
    """
    def __init__(self, handler: str, library: str):
        self._msg = (
            'The {} requires the {} library, which is not installed.'
        ).format(handler, library)

    def _raise(self, *args, **kwargs):
        raise RuntimeError(self._msg)

    # TODO(kgriffs): Add support for async later if needed.
    serialize = deserialize = _raise


class Handlers(UserDict):
    """A :class:`dict`-like object that manages Internet media type handlers."""
    def __init__(self, initial=None):
        self.__handler_cache = {}
        handlers = initial or {
            MEDIA_JSON: JSONHandler(),
            MEDIA_MULTIPART: MultipartFormHandler(),
            MEDIA_URLENCODED: URLEncodedFormHandler(),
        }

        # NOTE(jmvrbanac): Directly calling UserDict as it's not inheritable.
        # Also, this results in self.update(...) being called.
        UserDict.__init__(self, handlers)

    def __setitem__(self, key, item):
        self.__handler_cache.clear()
        return super().__setitem__(key, item)

    # def _normalize_handler(self, handler):
    #     if not handler:
    #         return
    #     try:
    #         if not hasattr(handler, '_serialize_sync'):
    #             handler._serialize_sync = None
    #         if not hasattr(handler, '_deserialize_sync'):
    #             handler._deserialize_sync = None
    #         return handler
    #     except AttributeError:
    #         return _WrapHandler(handler)

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

    def find_by_media_type(self, media_type, default, raise_not_found=True):
        # PERF(jmvrbanac): Check via a quick methods first for performance
        if media_type == '*/*' or not media_type:
            media_type = default

        try:
            return self.__handler_cache[media_type]
        except KeyError:
            pass

        try:
            handler = self.data[media_type]
        except KeyError:
            handler = None

        if handler is None:
            # PERF(jmvrbanac): Fallback to the slower method
            resolved = self._resolve_media_type(media_type, self.data.keys())

            if not resolved:
                if raise_not_found:
                    raise errors.HTTPUnsupportedMediaType(
                        description='{0} is an unsupported media type.'.format(media_type)
                    )
                return None, None, None

            handler = self.data[resolved]

        cache = self.__handler_cache[media_type] = (
            handler,
            getattr(handler, '_serialize_sync', None),
            getattr(handler, '_deserialize_sync', None),
        )
        return cache

class _WrapHandler():
    _serialize_sync = None
    _deserialize_sync = None

    def __init__(self, original):
        self.__original = original
        for key in dir(original):
            if not key.startswith('_') or key in {'__getattr__', '__getattribute__'}:
                setattr(self, key, getattr(original, key))


# NOTE(vytas): An ugly way to work around circular imports.
MultipartParseOptions._DEFAULT_HANDLERS = Handlers({
    MEDIA_JSON: JSONHandler(),
    MEDIA_URLENCODED: URLEncodedFormHandler(),
})  # type: ignore
