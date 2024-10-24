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

from __future__ import annotations

from inspect import iscoroutinefunction
from typing import IO, Iterable, List, Literal, Optional, overload, Tuple, Union

from falcon import util
from falcon._typing import AsgiProcessRequestMethod as APRequest
from falcon._typing import AsgiProcessRequestWsMethod
from falcon._typing import AsgiProcessResourceMethod as APResource
from falcon._typing import AsgiProcessResourceWsMethod
from falcon._typing import AsgiProcessResponseMethod as APResponse
from falcon._typing import ProcessRequestMethod as PRequest
from falcon._typing import ProcessResourceMethod as PResource
from falcon._typing import ProcessResponseMethod as PResponse
from falcon.constants import MEDIA_JSON
from falcon.constants import MEDIA_XML
from falcon.errors import CompatibilityError
from falcon.errors import HTTPError
from falcon.request import Request
from falcon.response import Response
from falcon.util.sync import _wrap_non_coroutine_unsafe

__all__ = (
    'prepare_middleware',
    'prepare_middleware_ws',
    'default_serialize_error',
    'CloseableStreamIterator',
)

PreparedMiddlewareResult = Tuple[
    Union[
        Tuple[PRequest, ...], Tuple[Tuple[Optional[PRequest], Optional[PResource]], ...]
    ],
    Tuple[PResource, ...],
    Tuple[PResponse, ...],
]
AsyncPreparedMiddlewareResult = Tuple[
    Union[
        Tuple[APRequest, ...],
        Tuple[Tuple[Optional[APRequest], Optional[APResource]], ...],
    ],
    Tuple[APResource, ...],
    Tuple[APResponse, ...],
]


@overload
def prepare_middleware(
    middleware: Iterable, independent_middleware: bool = ..., asgi: Literal[False] = ...
) -> PreparedMiddlewareResult: ...


@overload
def prepare_middleware(
    middleware: Iterable, independent_middleware: bool = ..., *, asgi: Literal[True]
) -> AsyncPreparedMiddlewareResult: ...


@overload
def prepare_middleware(
    middleware: Iterable, independent_middleware: bool = ..., asgi: bool = ...
) -> Union[PreparedMiddlewareResult, AsyncPreparedMiddlewareResult]: ...


def prepare_middleware(
    middleware: Iterable[object],
    independent_middleware: bool = False,
    asgi: bool = False,
) -> Union[PreparedMiddlewareResult, AsyncPreparedMiddlewareResult]:
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
    request_mw: Union[
        List[PRequest],
        List[Tuple[Optional[PRequest], Optional[PResource]]],
        List[APRequest],
        List[Tuple[Optional[APRequest], Optional[APResource]]],
    ] = []
    resource_mw: Union[List[APResource], List[PResource]] = []
    response_mw: Union[List[APResponse], List[PResponse]] = []

    for component in middleware:
        # NOTE(kgriffs): Middleware that supports both WSGI and ASGI can
        #   append an *_async postfix to the ASGI version of the method
        #   to distinguish the two. Otherwise, the prefix is unnecessary.

        if asgi:
            process_request: Union[Optional[APRequest], Optional[PRequest]] = (
                util.get_bound_method(component, 'process_request_async')
                or _wrap_non_coroutine_unsafe(
                    util.get_bound_method(component, 'process_request')
                )
            )

            process_resource: Union[Optional[APResource], Optional[PResource]] = (
                util.get_bound_method(component, 'process_resource_async')
                or _wrap_non_coroutine_unsafe(
                    util.get_bound_method(component, 'process_resource')
                )
            )

            process_response: Union[Optional[APResponse], Optional[PResponse]] = (
                util.get_bound_method(component, 'process_response_async')
                or _wrap_non_coroutine_unsafe(
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
                request_mw.append(process_request)  # type: ignore[arg-type]
            if process_response:
                response_mw.insert(0, process_response)  # type: ignore[arg-type]
        else:
            if process_request or process_response:
                request_mw.append((process_request, process_response))  # type: ignore[arg-type]

        if process_resource:
            resource_mw.append(process_resource)  # type: ignore[arg-type]

    return tuple(request_mw), tuple(resource_mw), tuple(response_mw)  # type: ignore[return-value]


AsyncPreparedMiddlewareWsResult = Tuple[
    Tuple[AsgiProcessRequestWsMethod, ...], Tuple[AsgiProcessResourceWsMethod, ...]
]


def prepare_middleware_ws(
    middleware: Iterable[object],
) -> AsyncPreparedMiddlewareWsResult:
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
    request_mw: List[AsgiProcessRequestWsMethod] = []
    resource_mw: List[AsgiProcessResourceWsMethod] = []

    process_request_ws: Optional[AsgiProcessRequestWsMethod]
    process_resource_ws: Optional[AsgiProcessResourceWsMethod]

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

    return tuple(request_mw), tuple(resource_mw)


def default_serialize_error(req: Request, resp: Response, exception: HTTPError) -> None:
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
    options = resp.options
    predefined = (
        [MEDIA_JSON, 'text/xml', MEDIA_XML]
        if options.xml_error_serialization
        else [MEDIA_JSON]
    )
    media_handlers = [mt for mt in options.media_handlers if mt not in predefined]
    # NOTE(caselit,vytas): Add the registered handlers after the predefined
    #   ones. This ensures that in the case of an equal match, the first one
    #   (JSON) is selected and that the q parameter is taken into consideration
    #   when selecting the media handler.
    preferred = req.client_prefers(predefined + media_handlers)

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
            # NOTE(caselit): Ignore xml_error_serialization when
            #   checking if the media should be XML. This gives a chance to
            #   an XML media handler, if any, to be used.
            preferred = MEDIA_XML

    if preferred is not None:
        handler, _, _ = options.media_handlers._resolve(
            preferred, MEDIA_JSON, raise_not_found=False
        )
        if preferred == MEDIA_JSON:
            # NOTE(caselit): Special case JSON to ensure that it's always
            #   possible to serialize an error in JSON even if no JSON handler
            #   is set in the media_handlers.
            resp.data = exception.to_json(handler)
        elif handler:
            # NOTE(caselit): Let the app serialize the response even if it
            #   needs to re-get the handler, since async handlers may not have
            #   a sync version available.
            resp.media = exception.to_dict()
        elif options.xml_error_serialization:
            resp.data = exception._to_xml()

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

    def __init__(self, stream: IO[bytes], block_size: int) -> None:
        self._stream = stream
        self._block_size = block_size

    def __iter__(self) -> CloseableStreamIterator:
        return self

    def __next__(self) -> bytes:
        data = self._stream.read(self._block_size)

        if data == b'':
            raise StopIteration
        else:
            return data

    def close(self) -> None:
        try:
            self._stream.close()
        except (AttributeError, TypeError):
            pass
