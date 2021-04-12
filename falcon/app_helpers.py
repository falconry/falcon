# Copyright 2013 by Rackspace Hosting, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utilities for the App class."""

from inspect import iscoroutinefunction

from falcon import util
from falcon.constants import MEDIA_JSON
from falcon.constants import MEDIA_XML
from falcon.errors import CompatibilityError
from falcon.util.sync import _wrap_non_coroutine_unsafe

__all__ = (
    'prepare_middleware',
    'prepare_middleware_ws',
    'default_serialize_error',
    'CloseableStreamIterator'
)


def prepare_middleware(middleware, independent_middleware=False, asgi=False):
    """Check middleware interfaces and prepare the methods for request handling.

    Note:
        This method is only applicable to WSGI apps.

    Arguments:
        middleware (iterable): An iterable of middleware objects.

    Keyword Args:
        independent_middleware (bool): ``True`` if the request and
            response middleware methods should be treated independently
            (default ``False``)
        asgi (bool): ``True`` if an ASGI app, ``False`` otherwise
            (default ``False``)

    Returns:
        tuple: A tuple of prepared middleware method tuples
    """

    # PERF(kgriffs): do getattr calls once, in advance, so we don't
    # have to do them every time in the request path.
    request_mw = []
    resource_mw = []
    response_mw = []

    for component in middleware:
        # NOTE(kgriffs): Middleware that supports both WSGI and ASGI can
        #   append an *_async postfix to the ASGI version of the method
        #   to distinguish the two. Otherwise, the prefix is unnecessary.

        if asgi:
            process_request = (
                util.get_bound_method(component, 'process_request_async') or
                _wrap_non_coroutine_unsafe(
                    util.get_bound_method(component, 'process_request')
                )
            )

            process_resource = (
                util.get_bound_method(component, 'process_resource_async') or
                _wrap_non_coroutine_unsafe(
                    util.get_bound_method(component, 'process_resource')
                )
            )

            process_response = (
                util.get_bound_method(component, 'process_response_async') or
                _wrap_non_coroutine_unsafe(
                    util.get_bound_method(component, 'process_response')
                )
            )

            for m in (process_request, process_resource, process_response):
                # NOTE(kgriffs): iscoroutinefunction() always returns False
                #   for cythonized functions.
                #
                #   https://github.com/cython/cython/issues/2273
                #   https://bugs.python.org/issue38225
                #
                if m and not iscoroutinefunction(m) and util.is_python_func(m):
                    msg = (
                        '{} must be implemented as an awaitable coroutine. If '
                        'you would like to retain compatibility '
                        'with WSGI apps, the coroutine versions of the '
                        'middleware methods may be implemented side-by-side '
                        'by applying an *_async postfix to the method names. '
                    )
                    raise CompatibilityError(msg.format(m))

        else:
            process_request = util.get_bound_method(component, 'process_request')
            process_resource = util.get_bound_method(component, 'process_resource')
            process_response = util.get_bound_method(component, 'process_response')

            for m in (process_request, process_resource, process_response):
                if m and iscoroutinefunction(m):
                    msg = (
                        '{} may not implement coroutine methods and '
                        'remain compatible with WSGI apps without '
                        'using the *_async postfix to explicitly identify '
                        'the coroutine version of a given middleware '
                        'method.'
                    )
                    raise CompatibilityError(msg.format(component))

        if not (process_request or process_resource or process_response):
            if asgi and any(
                hasattr(component, m)
                for m in [
                    'process_startup',
                    'process_shutdown',
                    'process_request_ws',
                    'process_resource_ws',
                ]
            ):
                # NOTE(kgriffs): This middleware only has ASGI lifespan
                #   event handlers
                continue

            msg = '{0} must implement at least one middleware method'
            raise TypeError(msg.format(component))

        # NOTE: depending on whether we want to execute middleware
        # independently, we group response and request middleware either
        # together or separately.
        if independent_middleware:
            if process_request:
                request_mw.append(process_request)
            if process_response:
                response_mw.insert(0, process_response)
        else:
            if process_request or process_response:
                request_mw.append((process_request, process_response))

        if process_resource:
            resource_mw.append(process_resource)

    return (tuple(request_mw), tuple(resource_mw), tuple(response_mw))


def prepare_middleware_ws(middleware):
    """Check middleware interfaces and prepare WebSocket methods for request handling.

    Note:
        This method is only applicable to ASGI apps.

    Arguments:
        middleware (iterable): An iterable of middleware objects.

    Returns:
        tuple: A two-item ``(request_mw, resource_mw)`` tuple, where
        *request_mw* is an ordered list of ``process_request_ws()`` methods,
        and *resource_mw* is an ordered list of ``process_resource_ws()``
        methods.
    """

    # PERF(kgriffs): do getattr calls once, in advance, so we don't
    # have to do them every time in the request path.
    request_mw = []
    resource_mw = []

    for component in middleware:
        process_request_ws = util.get_bound_method(component, 'process_request_ws')
        process_resource_ws = util.get_bound_method(component, 'process_resource_ws')

        for m in (process_request_ws, process_resource_ws):
            if not m:
                continue

            # NOTE(kgriffs): iscoroutinefunction() always returns False
            #   for cythonized functions.
            #
            #   https://github.com/cython/cython/issues/2273
            #   https://bugs.python.org/issue38225
            #
            if not iscoroutinefunction(m) and util.is_python_func(m):
                msg = '{} must be implemented as an awaitable coroutine.'
                raise CompatibilityError(msg.format(m))

        if process_request_ws:
            request_mw.append(process_request_ws)

        if process_resource_ws:
            resource_mw.append(process_resource_ws)

    return request_mw, resource_mw


def default_serialize_error(req, resp, exception):
    """Serialize the given instance of HTTPError.

    This function determines which of the supported media types, if
    any, are acceptable by the client, and serializes the error
    to the preferred type.

    Currently, JSON and XML are the only supported media types. If the
    client accepts both JSON and XML with equal weight, JSON will be
    chosen.

    Other media types can be supported by using a custom error serializer.

    Note:
        If a custom media type is used and the type includes a
        "+json" or "+xml" suffix, the error will be serialized
        to JSON or XML, respectively. If this behavior is not
        desirable, a custom error serializer may be used to
        override this one.

    Args:
        req: Instance of ``falcon.Request``
        resp: Instance of ``falcon.Response``
        exception: Instance of ``falcon.HTTPError``
    """
    preferred = req.client_prefers((MEDIA_XML, 'text/xml', MEDIA_JSON))

    if preferred is None:
        # NOTE(kgriffs): See if the client expects a custom media
        # type based on something Falcon supports. Returning something
        # is probably better than nothing, but if that is not
        # desired, this behavior can be customized by adding a
        # custom HTTPError serializer for the custom type.
        accept = req.accept.lower()

        # NOTE(kgriffs): Simple heuristic, but it's fast, and
        # should be sufficiently accurate for our purposes. Does
        # not take into account weights if both types are
        # acceptable (simply chooses JSON). If it turns out we
        # need to be more sophisticated, we can always change it
        # later (YAGNI).
        if '+json' in accept:
            preferred = MEDIA_JSON
        elif '+xml' in accept:
            preferred = MEDIA_XML

    if preferred is not None:
        if preferred == MEDIA_JSON:
            handler, _, _ = resp.options.media_handlers._resolve(
                MEDIA_JSON, MEDIA_JSON, raise_not_found=False
            )
            resp.data = exception.to_json(handler)
        else:
            resp.data = exception.to_xml()

        # NOTE(kgriffs): No need to append the charset param, since
        #   utf-8 is the default for both JSON and XML.
        resp.content_type = preferred

    resp.append_header('Vary', 'Accept')


class CloseableStreamIterator:
    """Iterator that wraps a file-like stream with support for close().

    This iterator can be used to read from an underlying file-like stream
    in block_size-chunks until the response from the stream is an empty
    byte string.

    This class is used to wrap WSGI response streams when a
    wsgi_file_wrapper is not provided by the server.  The fact that it
    also supports closing the underlying stream allows use of (e.g.)
    Python tempfile resources that would be deleted upon close.

    Args:
        stream (object): Readable file-like stream object.
        block_size (int): Number of bytes to read per iteration.
    """

    def __init__(self, stream, block_size):
        self._stream = stream
        self._block_size = block_size

    def __iter__(self):
        return self

    def __next__(self):
        data = self._stream.read(self._block_size)

        if data == b'':
            raise StopIteration
        else:
            return data

    def close(self):
        try:
            self._stream.close()
        except (AttributeError, TypeError):
            pass
