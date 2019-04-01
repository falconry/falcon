# Copied from the Requests library by Kenneth Reitz et al.
#
# Copyright 2013 Kenneth Reitz
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.


"""Data structures.

This module provides additional data structures not found in the
standard library. These classes are hoisted into the `falcon` module
for convenience::

    import falcon

    things = falcon.CaseInsensitiveDict()

"""

from falcon.util.compat import Mapping, MutableMapping


# TODO(kgriffs): If we ever diverge from what is upstream in Requests,
# then we will need write tests and remove the "no cover" pragma.
class CaseInsensitiveDict(MutableMapping):  # pragma: no cover
    """
    A case-insensitive ``dict``-like object.

    Implements all methods and operations of
    ``collections.abc.MutableMapping`` as well as dict's `copy`. Also
    provides `lower_items`.

    All keys are expected to be strings. The structure remembers the
    case of the last key to be set, and ``iter(instance)``,
    ``keys()``, ``items()``, ``iterkeys()``, and ``iteritems()``
    will contain case-sensitive keys. However, querying and contains
    testing is case insensitive:

        cid = CaseInsensitiveDict()
        cid['Accept'] = 'application/json'
        cid['aCCEPT'] == 'application/json'  # True
        list(cid) == ['Accept']  # True

    For example, ``headers['content-encoding']`` will return the
    value of a ``'Content-Encoding'`` response header, regardless
    of how the header name was originally stored.

    If the constructor, ``.update``, or equality comparison
    operations are given keys that have equal ``.lower()``s, the
    behavior is undefined.

    """
    def __init__(self, data=None, **kwargs):
        self._store = dict()
        if data is None:
            data = {}
        self.update(data, **kwargs)

    def __setitem__(self, key, value):
        # Use the lowercased key for lookups, but store the actual
        # key alongside the value.
        self._store[key.lower()] = (key, value)

    def __getitem__(self, key):
        return self._store[key.lower()][1]

    def __delitem__(self, key):
        del self._store[key.lower()]

    def __iter__(self):
        return (casedkey for casedkey, mappedvalue in self._store.values())

    def __len__(self):
        return len(self._store)

    def lower_items(self):
        """Like iteritems(), but with all lowercase keys."""
        return (
            (lowerkey, keyval[1])
            for (lowerkey, keyval)
            in self._store.items()
        )

    def __eq__(self, other):
        if isinstance(other, Mapping):
            other = CaseInsensitiveDict(other)
        else:
            return NotImplemented
        # Compare insensitively
        return dict(self.lower_items()) == dict(other.lower_items())

    # Copy is required
    def copy(self):
        return CaseInsensitiveDict(self._store.values())

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, dict(self.items()))


# NOTE(vytas): Although Context is effectively implementing the MutableMapping
#   interface, we choose not to subclass MutableMapping to stress the fact that
#   Context is, by design, a bare class, and the mapping interface may be
#   removed in a future Falcon release.
class Context(object):
    """
    Convenience class to hold contextual information in its attributes.

    This class is used as the default :class:`~.Request` and :class:`~Response`
    context type (see
    :attr:`Request.context_type <falcon.Request.context_type>` and
    :attr:`Response.context_type <falcon.Response.context_type>`,
    respectively).

    In Falcon versions prior to 2.0, the default context type was ``dict``. To
    ease the migration to attribute-based context object approach, this class
    also implements the mapping interface; that is, object attributes are
    linked to dictionary items, and vice versa. For instance:

    >>> context = falcon.Context()
    >>> context.cache_strategy = 'lru'
    >>> context.get('cache_strategy')
    'lru'
    >>> 'cache_strategy' in context
    True

    Note:
        Python 2 specific ``dict`` methods are exposed regardless of the
        Python language version, however, as they are delegated to the
        underlying ``__dict__``, a similar error would be raised as if
        attempting to use these methods for a usual Python 3 dict.
    """

    def __contains__(self, key):
        return self.__dict__.__contains__(key)

    def __getitem__(self, key):
        # PERF(vytas): On CPython, using this mapping interface (instead of a
        #   standard dict) to get, set and delete items incurs overhead
        #   approximately comparable to that of two function calls
        #   (per get/set/delete operation, that is).
        return self.__dict__.__getitem__(key)

    def __setitem__(self, key, value):
        return self.__dict__.__setitem__(key, value)

    def __delitem__(self, key):
        self.__dict__.__delitem__(key)

    def __iter__(self):
        return self.__dict__.__iter__()

    def __len__(self):
        return self.__dict__.__len__()

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.__dict__.__eq__(other.__dict__)
        return self.__dict__.__eq__(other)

    def __ne__(self, other):
        if isinstance(other, type(self)):
            return self.__dict__.__ne__(other.__dict__)
        return self.__dict__.__ne__(other)

    def __hash__(self):
        return hash(self.__dict__)

    def __repr__(self):
        return '{}({})'.format(type(self).__name__, self.__dict__.__repr__())

    def __str__(self):
        return '{}({})'.format(type(self).__name__, self.__dict__.__str__())

    def clear(self):
        return self.__dict__.clear()

    def copy(self):
        ctx = type(self)()
        ctx.update(self.__dict__)
        return ctx

    def get(self, key, default=None):
        return self.__dict__.get(key, default)

    def has_key(self, key):
        return self.__dict__.has_key(key)  # noqa

    def items(self):
        return self.__dict__.items()

    def iteritems(self):
        return self.__dict__.iteritems()

    def iterkeys(self):
        return self.__dict__.iterkeys()

    def itervalues(self):
        return self.__dict__.itervalues()

    def keys(self):
        return self.__dict__.keys()

    def pop(self, key, default=None):
        return self.__dict__.pop(key, default)

    def popitem(self):
        return self.__dict__.popitem()

    def setdefault(self, key, default_value=None):
        return self.__dict__.setdefault(key, default_value)

    def update(self, items):
        self.__dict__.update(items)

    def values(self):
        return self.__dict__.values()

    def viewitems(self):
        return self.__dict__.viewitems()

    def viewkeys(self):
        return self.__dict__.viewkeys()

    def viewvalues(self):
        return self.__dict__.viewvalues()


class ETag(str):
    """Convenience class to represent a parsed HTTP entity-tag.

    This class is simply a subclass of ``str`` with a few helper methods and
    an extra attribute to indicate whether the entity-tag is weak or strong. The
    value of the string is equivalent to what RFC 7232 calls an "opaque-tag",
    i.e. an entity-tag sans quotes and the weakness indicator.

    Note:

        Given that a weak entity-tag comparison can be performed by
        using the ``==`` operator (per the example below), only a
        :meth:`~.strong_compare` method is provided.

    Here is an example ``on_get()`` method that demonstrates how to use instances
    of this class::

        def on_get(self, req, resp):
            content_etag = self._get_content_etag()
            for etag in (req.if_none_match or []):
                if etag == '*' or etag == content_etag:
                    resp.status = falcon.HTTP_304
                    return

            # ...

            resp.etag = content_etag
            resp.status = falcon.HTTP_200

    (See also: RFC 7232)

    Attributes:
        is_weak (bool): ``True`` if the entity-tag is weak, otherwise ``False``.

    """

    is_weak = False

    def strong_compare(self, other):
        """Performs a strong entity-tag comparison.

        Two entity-tags are equivalent if both are not weak and their
        opaque-tags match character-by-character.

        (See also: RFC 7232, Section 2.3.2)

        Arguments:
            other (ETag): The other :class:`~.ETag` to which you are comparing
            this one.

        Returns:
            bool: ``True`` if the two entity-tags match, otherwise ``False``.

        """

        return self == other and not (self.is_weak or other.is_weak)

    def dumps(self):
        """Serialize the ETag to a string suitable for use in a precondition header.

        (See also: RFC 7232, Section 2.3)

        Returns:
            str: An opaque quoted string, possibly prefixed by a weakness
            indicator ``W/``.
        """

        if self.is_weak:
            # PERF(kgriffs): Simple concatenation like this is slightly faster
            #   than %s string formatting.
            return 'W/"' + self + '"'

        return '"' + self + '"'

    @classmethod
    def loads(cls, etag_str):
        """Class method that deserializes a single entity-tag string from a precondition header.

        Note:

            This method is meant to be used only for parsing a single
            entity-tag. It can not be used to parse a comma-separated list of
            values.

        (See also: RFC 7232, Section 2.3)

        Arguments:
            etag_str (str): An ASCII string representing a single entity-tag,
                as defined by RFC 7232.

        Returns:
            ETag: An instance of `~.ETag` representing the parsed entity-tag.

        """

        value = etag_str

        is_weak = False
        if value.startswith(('W/', 'w/')):
            is_weak = True
            value = value[2:]

        # NOTE(kgriffs): We allow for an unquoted entity-tag just in case,
        #   although it has been non-standard to do so since at least 1999
        #   with the advent of RFC 2616.
        if value[:1] == value[-1:] == '"':
            value = value[1:-1]

        t = cls(value)
        t.is_weak = is_weak

        return t
