from collections import UserDict

from falcon import errors
from falcon.constants import MEDIA_JSON, MEDIA_MULTIPART, MEDIA_URLENCODED
from falcon.media.json import JSONHandler
from falcon.media.multipart import MultipartFormHandler, MultipartParseOptions
from falcon.media.urlencoded import URLEncodedFormHandler
from falcon.util import deprecation
from falcon.util import misc
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
        self._resolve = self._create_resolver()

        handlers = initial or {
            MEDIA_JSON: JSONHandler(),
            MEDIA_MULTIPART: MultipartFormHandler(),
            MEDIA_URLENCODED: URLEncodedFormHandler(),
        }

        # NOTE(jmvrbanac): Directly calling UserDict as it's not inheritable.
        # Also, this results in self.update(...) being called.
        UserDict.__init__(self, handlers)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)

        # NOTE(kgriffs): When the mapping changes, we do not want to use a
        #   cached handler from the previous mapping, in case it was
        #   replaced.
        self._resolve.cache_clear()

    def __delitem__(self, key):
        super().__delitem__(key)

        # NOTE(kgriffs): Similar to __setitem__(), we need to avoid resolving
        #   to a cached handler that was removed.
        self._resolve.cache_clear()

    def _best_match(self, media_type, all_media_types):
        result = None

        try:
            # NOTE(jmvrbanac): Mimeparse will return an empty string if it can
            # parse the media type, but cannot find a suitable type.
            result = mimeparse.best_match(
                all_media_types,
                media_type
            )
        except ValueError:
            pass

        return result

    def _create_resolver(self):
        # NOTE(kgriffs): This is defined as a private method since it is meant to
        #   only be called by the framework, rather than the app.
        # NOTE(kgriffs): Most apps will probably only use one or two media handlers,
        #   but we use maxsize=64 to give us some wiggle room just in case someone
        #   is using versioned media types or something, and to cover various
        #   combinations of the method args. We may need to tune this later.
        @misc._lru_cache_safe(maxsize=64)
        def resolve(media_type, default, raise_not_found=True):
            if media_type == '*/*' or not media_type:
                media_type = default

            # PERF(kgriffs): We just do this slower check every time, rather
            #   than trying to first check the dict directly, since the result
            #   will almost always be cached anyway.
            matched_type = self._best_match(media_type, self.data.keys())

            if not matched_type:
                if raise_not_found:
                    raise errors.HTTPUnsupportedMediaType(
                        description='{0} is an unsupported media type.'.format(media_type)
                    )

                return None, None, None

            handler = self.data[matched_type]

            return (
                handler,
                getattr(handler, '_serialize_sync', None),
                getattr(handler, '_deserialize_sync', None),
            )

        return resolve

    @deprecation.deprecated(
        'This undocumented method is no longer supported as part of the public '
        'interface and will be removed in a future release.'
    )
    def find_by_media_type(self, media_type, default, raise_not_found=True):
        # PERF(jmvrbanac): Check via a quick methods first for performance
        if media_type == '*/*' or not media_type:
            media_type = default

        try:
            return self.data[media_type]
        except KeyError:
            pass

        # PERF(jmvrbanac): Fallback to the slower method
        resolved = self._best_match(media_type, self.data.keys())

        if not resolved:
            if raise_not_found:
                raise errors.HTTPUnsupportedMediaType(
                    description='{0} is an unsupported media type.'.format(media_type)
                )
            return None

        return self.data[resolved]


# NOTE(vytas): An ugly way to work around circular imports.
MultipartParseOptions._DEFAULT_HANDLERS = Handlers({
    MEDIA_JSON: JSONHandler(),
    MEDIA_URLENCODED: URLEncodedFormHandler(),
})  # type: ignore
