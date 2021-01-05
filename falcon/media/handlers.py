from collections import UserDict
import functools

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
        self._hash = 0

        handlers = initial or {
            MEDIA_JSON: JSONHandler(),
            MEDIA_MULTIPART: MultipartFormHandler(),
            MEDIA_URLENCODED: URLEncodedFormHandler(),
        }

        # NOTE(jmvrbanac): Directly calling UserDict as it's not inheritable.
        # Also, this results in self.update(...) being called.
        UserDict.__init__(self, handlers)

    def __setitem__(self, key, item):
        self.find_by_media_type.cache_clear()
        super().__setitem__(key, item)
        self._rehash()

    def __delitem__(self, key):
        self.find_by_media_type.cache_clear()
        super().__delitem__(key)
        self._rehash()

    # NOTE(kgriffs): Make instances hashable so that we can use lru_cache().
    def __hash__(self):
        return self._hash

    def _rehash(self):
        # NOTE(kgriffs): We could have done something simpler, but it would
        #   have been a leaky abstraction, and it is probably better to avoid
        #   any potential suprises from instances of Handlers not appearing to
        #   be logically equivalent.
        # NOTE(kgriffs): The generator must be wrapped in tuple() in order to
        #   get a consistent hash value, because otherwise we end up hashing
        #   the generator object itself.
        self._hash = hash(tuple((k, v) for k, v in self.data.items()))

    # NOTE(kgriffs): Even though apps probably don't need this, it is included
    #   in order to conform to the guidelines layed out in the Python Data Model:
    #
    #   https://docs.python.org/3/reference/datamodel.html#object.__hash__
    #
    def __eq__(self, other):
        return hash(self) == hash(other)

    def _resolve(self, media_type):
        # PERF(kgriffs): Even though it is slightly less performant, we can use
        #   get() here since the result will be cached.
        handler = self.data.get(media_type)

        if not handler:
            # PERF(jmvrbanac): Fallback to the slower method
            resolved = self._resolve_media_type(media_type, self.data.keys())

            if not resolved:
                return None

            handler = self.data[resolved]

        return (
            handler,
            getattr(handler, '_serialize_sync', None),
            getattr(handler, '_deserialize_sync', None),
        )

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

    # NOTE(kgriffs): Most apps will probably only use one or two media handlers,
    #   but we use maxsize=64 to give us some wiggle room just in case someone
    #   is using versioned media types or something, and to cover various
    #   combinations of the method args. We may need to tune this later.
    @functools.lru_cache(maxsize=64)
    def find_by_media_type(self, media_type, default, raise_not_found=True):
        # PERF(jmvrbanac): Check via a quick method first for performance
        if media_type == '*/*' or not media_type:
            media_type = default

        handler_info = self._resolve(media_type)

        if not handler_info:
            if raise_not_found:
                raise errors.HTTPUnsupportedMediaType(
                    description='{0} is an unsupported media type.'.format(media_type)
                )

            return None, None, None

        return handler_info


# NOTE(vytas): An ugly way to work around circular imports.
MultipartParseOptions._DEFAULT_HANDLERS = Handlers({
    MEDIA_JSON: JSONHandler(),
    MEDIA_URLENCODED: URLEncodedFormHandler(),
})  # type: ignore
