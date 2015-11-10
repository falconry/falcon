# -*- coding: utf-8 -*-
"""
    werkzeug.urls
    ~~~~~~~~~~~~~

    ``werkzeug.urls`` used to provide several wrapper functions for Python 2
    urlparse, whose main purpose were to work around the behavior of the Py2
    stdlib and its lack of unicode support. While this was already a somewhat
    inconvenient situation, it got even more complicated because Python 3's
    ``urllib.parse`` actually does handle unicode properly. In other words,
    this module would wrap two libraries with completely different behavior. So
    now this module contains a 2-and-3-compatible backport of Python 3's
    ``urllib.parse``, which is mostly API-compatible.

    :copyright: (c) 2014 by the Werkzeug Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
import os
import re
from ._compat import text_type, PY2, to_unicode, \
    to_native, implements_to_string, try_coerce_native, \
    normalize_string_tuple, make_literal_wrapper, \
    fix_tuple_repr
from ._internal import _encode_idna, _decode_idna
# from werkzeug.datastructures import MultiDict, iter_multi_items
from collections import namedtuple


# A regular expression for what a valid schema looks like
_scheme_re = re.compile(r'^[a-zA-Z0-9+-.]+$')

# Characters that are safe in any part of an URL.
_always_safe = (b'abcdefghijklmnopqrstuvwxyz'
                b'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-+')

_hexdigits = '0123456789ABCDEFabcdef'
_hextobyte = dict(
    ((a + b).encode(), int(a + b, 16))
    for a in _hexdigits for b in _hexdigits
)


_URLTuple = fix_tuple_repr(namedtuple('_URLTuple',
                                      ['scheme', 'netloc', 'path', 'query', 'fragment']))


class BaseURL(_URLTuple):

    '''Superclass of :py:class:`URL` and :py:class:`BytesURL`.'''
    __slots__ = ()

    def replace(self, **kwargs):
        """Return an URL with the same values, except for those parameters
        given new values by whichever keyword arguments are specified."""
        return self._replace(**kwargs)

    @property
    def host(self):
        """The host part of the URL if available, otherwise `None`.  The
        host is either the hostname or the IP address mentioned in the
        URL.  It will not contain the port.
        """
        return self._split_host()[0]

    @property
    def ascii_host(self):
        """Works exactly like :attr:`host` but will return a result that
        is restricted to ASCII.  If it finds a netloc that is not ASCII
        it will attempt to idna decode it.  This is useful for socket
        operations when the URL might include internationalized characters.
        """
        rv = self.host
        if rv is not None and isinstance(rv, text_type):
            rv = _encode_idna(rv)
        return to_native(rv, 'ascii', 'ignore')

    @property
    def port(self):
        """The port in the URL as an integer if it was present, `None`
        otherwise.  This does not fill in default ports.
        """
        try:
            rv = int(to_native(self._split_host()[1]))
            if 0 <= rv <= 65535:
                return rv
        except (ValueError, TypeError):
            pass

    @property
    def auth(self):
        """The authentication part in the URL if available, `None`
        otherwise.
        """
        return self._split_netloc()[0]

    @property
    def username(self):
        """The username if it was part of the URL, `None` otherwise.
        This undergoes URL decoding and will always be a unicode string.
        """
        rv = self._split_auth()[0]
        if rv is not None:
            return _url_unquote_legacy(rv)

    @property
    def raw_username(self):
        """The username if it was part of the URL, `None` otherwise.
        Unlike :attr:`username` this one is not being decoded.
        """
        return self._split_auth()[0]

    @property
    def password(self):
        """The password if it was part of the URL, `None` otherwise.
        This undergoes URL decoding and will always be a unicode string.
        """
        rv = self._split_auth()[1]
        if rv is not None:
            return _url_unquote_legacy(rv)

    @property
    def raw_password(self):
        """The password if it was part of the URL, `None` otherwise.
        Unlike :attr:`password` this one is not being decoded.
        """
        return self._split_auth()[1]

    def decode_query(self, *args, **kwargs):
        """Decodes the query part of the URL.  Ths is a shortcut for
        calling :func:`url_decode` on the query argument.  The arguments and
        keyword arguments are forwarded to :func:`url_decode` unchanged.
        """
        return url_decode(self.query, *args, **kwargs)

    def join(self, *args, **kwargs):
        """Joins this URL with another one.  This is just a convenience
        function for calling into :meth:`url_join` and then parsing the
        return value again.
        """
        return url_parse(url_join(self, *args, **kwargs))

    def to_url(self):
        """Returns a URL string or bytes depending on the type of the
        information stored.  This is just a convenience function
        for calling :meth:`url_unparse` for this URL.
        """
        return url_unparse(self)

    def decode_netloc(self):
        """Decodes the netloc part into a string."""
        rv = _decode_idna(self.host or '')

        if ':' in rv:
            rv = '[%s]' % rv
        port = self.port
        if port is not None:
            rv = '%s:%d' % (rv, port)
        auth = ':'.join(filter(None, [
            _url_unquote_legacy(self.raw_username or '', '/:%@'),
            _url_unquote_legacy(self.raw_password or '', '/:%@'),
        ]))
        if auth:
            rv = '%s@%s' % (auth, rv)
        return rv

    def to_uri_tuple(self):
        """Returns a :class:`BytesURL` tuple that holds a URI.  This will
        encode all the information in the URL properly to ASCII using the
        rules a web browser would follow.

        It's usually more interesting to directly call :meth:`iri_to_uri` which
        will return a string.
        """
        return url_parse(iri_to_uri(self).encode('ascii'))

    def to_iri_tuple(self):
        """Returns a :class:`URL` tuple that holds a IRI.  This will try
        to decode as much information as possible in the URL without
        losing information similar to how a web browser does it for the
        URL bar.

        It's usually more interesting to directly call :meth:`uri_to_iri` which
        will return a string.
        """
        return url_parse(uri_to_iri(self))

    def get_file_location(self, pathformat=None):
        """Returns a tuple with the location of the file in the form
        ``(server, location)``.  If the netloc is empty in the URL or
        points to localhost, it's represented as ``None``.

        The `pathformat` by default is autodetection but needs to be set
        when working with URLs of a specific system.  The supported values
        are ``'windows'`` when working with Windows or DOS paths and
        ``'posix'`` when working with posix paths.

        If the URL does not point to to a local file, the server and location
        are both represented as ``None``.

        :param pathformat: The expected format of the path component.
                           Currently ``'windows'`` and ``'posix'`` are
                           supported.  Defaults to ``None`` which is
                           autodetect.
        """
        if self.scheme != 'file':
            return None, None

        path = url_unquote(self.path)
        host = self.netloc or None

        if pathformat is None:
            if os.name == 'nt':
                pathformat = 'windows'
            else:
                pathformat = 'posix'

        if pathformat == 'windows':
            if path[:1] == '/' and path[1:2].isalpha() and path[2:3] in '|:':
                path = path[1:2] + ':' + path[3:]
            windows_share = path[:3] in ('\\' * 3, '/' * 3)
            import ntpath
            path = ntpath.normpath(path)
            # Windows shared drives are represented as ``\\host\\directory``.
            # That results in a URL like ``file://///host/directory``, and a
            # path like ``///host/directory``. We need to special-case this
            # because the path contains the hostname.
            if windows_share and host is None:
                parts = path.lstrip('\\').split('\\', 1)
                if len(parts) == 2:
                    host, path = parts
                else:
                    host = parts[0]
                    path = ''
        elif pathformat == 'posix':
            import posixpath
            path = posixpath.normpath(path)
        else:
            raise TypeError('Invalid path format %s' % repr(pathformat))

        if host in ('127.0.0.1', '::1', 'localhost'):
            host = None

        return host, path

    def _split_netloc(self):
        if self._at in self.netloc:
            return self.netloc.split(self._at, 1)
        return None, self.netloc

    def _split_auth(self):
        auth = self._split_netloc()[0]
        if not auth:
            return None, None
        if self._colon not in auth:
            return auth, None
        return auth.split(self._colon, 1)

    def _split_host(self):
        rv = self._split_netloc()[1]
        if not rv:
            return None, None

        if not rv.startswith(self._lbracket):
            if self._colon in rv:
                return rv.split(self._colon, 1)
            return rv, None

        idx = rv.find(self._rbracket)
        if idx < 0:
            return rv, None

        host = rv[1:idx]
        rest = rv[idx + 1:]
        if rest.startswith(self._colon):
            return host, rest[1:]
        return host, None


@implements_to_string
class URL(BaseURL):

    """Represents a parsed URL.  This behaves like a regular tuple but
    also has some extra attributes that give further insight into the
    URL.
    """
    __slots__ = ()
    _at = '@'
    _colon = ':'
    _lbracket = '['
    _rbracket = ']'

    def __str__(self):
        return self.to_url()

    def encode_netloc(self):
        """Encodes the netloc part to an ASCII safe URL as bytes."""
        rv = self.ascii_host or ''
        if ':' in rv:
            rv = '[%s]' % rv
        port = self.port
        if port is not None:
            rv = '%s:%d' % (rv, port)
        auth = ':'.join(filter(None, [
            url_quote(self.raw_username or '', 'utf-8', 'strict', '/:%'),
            url_quote(self.raw_password or '', 'utf-8', 'strict', '/:%'),
        ]))
        if auth:
            rv = '%s@%s' % (auth, rv)
        return to_native(rv)

    def encode(self, charset='utf-8', errors='replace'):
        """Encodes the URL to a tuple made out of bytes.  The charset is
        only being used for the path, query and fragment.
        """
        return BytesURL(
            self.scheme.encode('ascii'),
            self.encode_netloc(),
            self.path.encode(charset, errors),
            self.query.encode(charset, errors),
            self.fragment.encode(charset, errors)
        )


class BytesURL(BaseURL):

    """Represents a parsed URL in bytes."""
    __slots__ = ()
    _at = b'@'
    _colon = b':'
    _lbracket = b'['
    _rbracket = b']'

    def __str__(self):
        return self.to_url().decode('utf-8', 'replace')

    def encode_netloc(self):
        """Returns the netloc unchanged as bytes."""
        return self.netloc

    def decode(self, charset='utf-8', errors='replace'):
        """Decodes the URL to a tuple made out of strings.  The charset is
        only being used for the path, query and fragment.
        """
        return URL(
            self.scheme.decode('ascii'),
            self.decode_netloc(),
            self.path.decode(charset, errors),
            self.query.decode(charset, errors),
            self.fragment.decode(charset, errors)
        )


def _unquote_to_bytes(string, unsafe=''):
    if isinstance(string, text_type):
        string = string.encode('utf-8')
    if isinstance(unsafe, text_type):
        unsafe = unsafe.encode('utf-8')
    unsafe = frozenset(bytearray(unsafe))
    bits = iter(string.split(b'%'))
    result = bytearray(next(bits, b''))
    for item in bits:
        try:
            char = _hextobyte[item[:2]]
            if char in unsafe:
                raise KeyError()
            result.append(char)
            result.extend(item[2:])
        except KeyError:
            result.extend(b'%')
            result.extend(item)
    return bytes(result)


def url_parse(url, scheme=None, allow_fragments=True):
    """Parses a URL from a string into a :class:`URL` tuple.  If the URL
    is lacking a scheme it can be provided as second argument. Otherwise,
    it is ignored.  Optionally fragments can be stripped from the URL
    by setting `allow_fragments` to `False`.

    The inverse of this function is :func:`url_unparse`.

    :param url: the URL to parse.
    :param scheme: the default schema to use if the URL is schemaless.
    :param allow_fragments: if set to `False` a fragment will be removed
                            from the URL.
    """
    s = make_literal_wrapper(url)
    is_text_based = isinstance(url, text_type)

    if scheme is None:
        scheme = s('')
    netloc = query = fragment = s('')
    i = url.find(s(':'))
    if i > 0 and _scheme_re.match(to_native(url[:i], errors='replace')):
        # make sure "iri" is not actually a port number (in which case
        # "scheme" is really part of the path)
        rest = url[i + 1:]
        if not rest or any(c not in s('0123456789') for c in rest):
            # not a port number
            scheme, url = url[:i].lower(), rest

    if url[:2] == s('//'):
        delim = len(url)
        for c in s('/?#'):
            wdelim = url.find(c, 2)
            if wdelim >= 0:
                delim = min(delim, wdelim)
        netloc, url = url[2:delim], url[delim:]
        if (s('[') in netloc and s(']') not in netloc) or \
           (s(']') in netloc and s('[') not in netloc):
            raise ValueError('Invalid IPv6 URL')

    if allow_fragments and s('#') in url:
        url, fragment = url.split(s('#'), 1)
    if s('?') in url:
        url, query = url.split(s('?'), 1)

    result_type = is_text_based and URL or BytesURL
    return result_type(scheme, netloc, url, query, fragment)


def url_unquote(string, charset='utf-8', errors='replace', unsafe=''):
    """URL decode a single string with a given encoding.  If the charset
    is set to `None` no unicode decoding is performed and raw bytes
    are returned.

    :param s: the string to unquote.
    :param charset: the charset of the query string.  If set to `None`
                    no unicode decoding will take place.
    :param errors: the error handling for the charset decoding.
    """
    rv = _unquote_to_bytes(string, unsafe)
    if charset is not None:
        rv = rv.decode(charset, errors)
    return rv
