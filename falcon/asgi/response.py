# Copyright 2019 by Kurt Griffiths
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

"""ASGI Response class."""

from asyncio.coroutines import CoroWrapper  # type: ignore
from inspect import iscoroutine
from inspect import iscoroutinefunction

from falcon import response
from falcon.constants import _UNSET
from falcon.util.misc import _encode_items_to_latin1, is_python_func

__all__ = ['Response']


class Response(response.Response):
    """Represents an HTTP response to a client request.

    Note:
        ``Response`` is not meant to be instantiated directly by responders.

    Keyword Arguments:
        options (dict): Set of global options passed from the App handler.

    Attributes:
        status: HTTP status code or line (e.g., ``'200 OK'``). This may be set
            to a member of :class:`http.HTTPStatus`, an HTTP status line string
            or byte string (e.g., ``'200 OK'``), or an ``int``.

            Note:
                The Falcon framework itself provides a number of constants for
                common status codes. They all start with the ``HTTP_`` prefix,
                as in: ``falcon.HTTP_204``. (See also: :ref:`status`.)

        media (object): A serializable object supported by the media handlers
            configured via :class:`falcon.RequestOptions`.

            Note:
                See also :ref:`media` for more information regarding media
                handling.

        text (str): String representing response content.

            Note:
                Falcon will encode the given text as UTF-8
                in the response. If the content is already a byte string,
                use the :attr:`data` attribute instead (it's faster).

        body (str): Deprecated alias for :attr:`text`. Will be removed in a future Falcon version.

        data (bytes): Byte string representing response content.

            Use this attribute in lieu of `text` when your content is
            already a byte string (of type ``bytes``).

            Warning:
                Always use the `text` attribute for text, or encode it
                first to ``bytes`` when using the `data` attribute, to
                ensure Unicode characters are properly encoded in the
                HTTP response.

        stream: An async iterator or generator that yields a series of
            byte strings that will be streamed to the ASGI server as a
            series of "http.response.body" events. Falcon will assume the
            body is complete when the iterable is exhausted or as soon as it
            yields ``None`` rather than an instance of ``bytes``::

                async def producer():
                    while True:
                        data_chunk = await read_data()
                        if not data_chunk:
                            break

                        yield data_chunk

                resp.stream = producer

            Alternatively, a file-like object may be used as long as it
            implements an awaitable ``read()`` method::

                resp.stream = await aiofiles.open('resp_data.bin', 'rb')

            If the object assigned to :py:attr:`~.stream` holds any resources
            (such as a file handle) that must be explicitly released, the
            object must implement a ``close()`` method. The ``close()`` method
            will be called after exhausting the iterable or file-like object.

            Note:
                In order to be compatible with Python 3.7+ and PEP 479,
                async iterators must return ``None`` instead of raising
                :py:class:`StopIteration`. This requirement does not
                apply to async generators (PEP 525).

            Note:
                If the stream length is known in advance, you may wish to
                also set the Content-Length header on the response.

        sse (coroutine): A Server-Sent Event (SSE) emitter, implemented as
            an async iterator or generator that yields a series of
            of :py:class:`falcon.asgi.SSEvent` instances. Each event will be
            serialized and sent to the client as HTML5 Server-Sent Events::

                async def emitter():
                    while True:
                        some_event = await get_next_event()

                        if not some_event:
                            # Send an event consisting of a single "ping"
                            #   comment to keep the connection alive.
                            yield SSEvent()

                            # Alternatively, one can simply yield None and
                            #   a "ping" will also be sent as above.

                            # yield

                            continue

                        yield SSEvent(json=some_event, retry=5000)

                        # ...or

                        yield SSEvent(data=b'something', event_id=some_id)

                        # Alternatively, you may yield anything that implements
                        #   a serialize() method that returns a byte string
                        #   conforming to the SSE event stream format.

                        # yield some_event

                resp.sse = emitter()

            Note:
                When the `sse` property is set, it supersedes both the
                `text` and `data` properties.

            Note:
                When hosting an app that emits Server-Sent Events, the web
                server should be set with a relatively long keep-alive TTL to
                minimize the overhead of connection renegotiations.

        context (object): Empty object to hold any data (in its attributes)
            about the response which is specific to your app (e.g. session
            object). Falcon itself will not interact with this attribute after
            it has been initialized.

            Note:
                The preferred way to pass response-specific data, when using the
                default context type, is to set attributes directly on the
                `context` object. For example::

                    resp.context.cache_strategy = 'lru'

        context_type (class): Class variable that determines the factory or
            type to use for initializing the `context` attribute. By default,
            the framework will instantiate bare objects (instances of the bare
            :class:`falcon.Context` class). However, you may override this
            behavior by creating a custom child class of
            :class:`falcon.asgi.Response`, and then passing that new class
            to ``falcon.App()`` by way of the latter's `response_type`
            parameter.

            Note:
                When overriding `context_type` with a factory function (as
                opposed to a class), the function is called like a method of
                the current Response instance. Therefore the first argument is
                the Response instance itself (self).

        options (dict): Set of global options passed in from the App handler.

        headers (dict): Copy of all headers set for the response,
            sans cookies. Note that a new copy is created and returned each
            time this property is referenced.

        complete (bool): Set to ``True`` from within a middleware method to
            signal to the framework that request processing should be
            short-circuited (see also :ref:`Middleware <middleware>`).
    """

    # PERF(kgriffs): These will be shadowed when set on an instance; let's
    #   us avoid having to implement __init__ and incur the overhead of
    #   an additional function call.
    _sse = None
    _registered_callbacks = None

    @property
    def sse(self):
        return self._sse

    @sse.setter
    def sse(self, value):
        self._sse = value

    def set_stream(self, stream, content_length):
        """Set both `stream` and `content_length`.

        Although the :attr:`~falcon.asgi.Response.stream` and
        :attr:`~falcon.asgi.Response.content_length` properties may be set
        directly, using this method ensures
        :attr:`~falcon.asgi.Response.content_length` is not accidentally
        neglected when the length of the stream is known in advance. Using this
        method is also slightly more performant as compared to setting the
        properties individually.

        Note:
            If the stream length is unknown, you can set
            :attr:`~falcon.asgi.Response.stream` directly, and ignore
            :attr:`~falcon.asgi.Response.content_length`. In this case, the ASGI
            server may choose to use chunked encoding for HTTP/1.1

        Args:
            stream: A readable, awaitable file-like object or async iterable
                that returns byte strings. If the object implements a close()
                method, it will be called after reading all of the data.
            content_length (int): Length of the stream, used for the
                Content-Length header in the response.
        """

        self.stream = stream

        # PERF(kgriffs): Set directly rather than incur the overhead of
        #   the self.content_length property.
        self._headers['content-length'] = str(content_length)

    async def render_body(self):
        """Get the raw bytestring content for the response body.

        This coroutine can be awaited to get the raw data for the
        HTTP response body, taking into account the :attr:`~.text`,
        :attr:`~.data`, and :attr:`~.media` attributes.

        Note:
            This method ignores :attr:`~.stream`; the caller must check
            and handle that attribute directly.

        Returns:
            bytes: The UTF-8 encoded value of the `text` attribute, if
            set. Otherwise, the value of the `data` attribute if set, or
            finally the serialized value of the `media` attribute. If
            none of these attributes are set, ``None`` is returned.
        """

        # NOTE(vytas): The code below is also inlined in asgi.App.__call__.

        text = self.text
        if text is None:
            data = self._data

            if data is None and self._media is not None:
                # NOTE(kgriffs): We use a special _UNSET singleton since
                #   None is ambiguous (the media handler might return None).
                if self._media_rendered is _UNSET:
                    if not self.content_type:
                        self.content_type = self.options.default_media_type

                    handler, serialize_sync, _ = self.options.media_handlers._resolve(
                        self.content_type,
                        self.options.default_media_type
                    )

                    if serialize_sync:
                        self._media_rendered = serialize_sync(self._media)
                    else:
                        self._media_rendered = await handler.serialize_async(
                            self._media,
                            self.content_type
                        )

                data = self._media_rendered
        else:
            try:
                # NOTE(kgriffs): Normally we expect text to be a string
                data = text.encode()
            except AttributeError:
                # NOTE(kgriffs): Assume it was a bytes object already
                data = text

        return data

    def schedule(self, callback):
        """Schedule an async callback to run soon after sending the HTTP response.

        This method can be used to execute a background job after the response
        has been returned to the client.

        The callback is assumed to be an async coroutine function. It will be
        scheduled to run on the event loop as soon as possible.

        The callback will be invoked without arguments. Use
        :any:`functools.partial` to pass arguments to the callback as needed.

        Note:
            If an unhandled exception is raised while processing the request,
            the callback will not be scheduled to run.

        Note:
            When an SSE emitter has been set on the response, the callback will
            be scheduled before the first call to the emitter.

        Warning:
            Because coroutines run on the main request thread, care should
            be taken to ensure they are non-blocking. Long-running operations
            must use async libraries or delegate to an
            :class:`~concurrent.futures.Executor` pool to avoid
            blocking the processing of subsequent requests.

        Args:
            callback(object): An async coroutine function. The callback will be
            invoked without arguments.
        """

        # NOTE(kgriffs): We also have to do the CoroWrapper check because
        #   iscoroutine is less reliable under Python 3.6.
        if not iscoroutinefunction(callback):
            if iscoroutine(callback) or isinstance(callback, CoroWrapper):
                raise TypeError(
                    'The callback object appears to '
                    'be a coroutine, rather than a coroutine function. Please '
                    'pass the function itself, rather than the result obtained '
                    'by calling the function. '
                )
            elif is_python_func(callback):  # pragma: nocover
                raise TypeError('The callback must be a coroutine function.')

            # NOTE(kgriffs): The implicit "else" branch is actually covered
            #   by tests running in a Cython environment, but we can't
            #   detect it with the coverage tool.

        rc = (callback, True)

        if not self._registered_callbacks:
            self._registered_callbacks = [rc]
        else:
            self._registered_callbacks.append(rc)

    def schedule_sync(self, callback):
        """Schedule a synchronous callback to run soon after sending the HTTP response.

        This method can be used to execute a background job after the
        response has been returned to the client.

        The callback is assumed to be a synchronous (non-coroutine) function.
        It will be scheduled on the event loop's default
        :class:`~concurrent.futures.Executor` (which can be overridden via
        :meth:`asyncio.AbstractEventLoop.set_default_executor`).

        The callback will be invoked without arguments. Use
        :any:`functools.partial` to pass arguments to the callback
        as needed.

        Note:
            If an unhandled exception is raised while processing the request,
            the callback will not be scheduled to run.

        Note:
            When an SSE emitter has been set on the response, the callback will
            be scheduled before the first call to the emitter.

        Warning:
            Synchronous callables run on the event loop's default
            :class:`~concurrent.futures.Executor`, which uses an instance of
            :class:`~concurrent.futures.ThreadPoolExecutor` unless
            :meth:`asyncio.AbstractEventLoop.set_default_executor` is used to
            change it to something else. Due to the GIL, CPU-bound jobs will
            block request processing for the current process unless the default
            :class:`~concurrent.futures.Executor` is changed to one that is
            process-based instead of thread-based (e.g., an instance of
            :class:`concurrent.futures.ProcessPoolExecutor`).

        Args:
            callback(object): An async coroutine function or a synchronous
                callable. The callback will be called without arguments.
        """

        rc = (callback, False)

        if not self._registered_callbacks:
            self._registered_callbacks = [rc]
        else:
            self._registered_callbacks.append(rc)

    # ------------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------------

    def _asgi_headers(self, media_type=None):
        """Convert headers into the format expected by ASGI servers.

        Header names must be lowercased and both name and value must be
        byte strings.

        See also: https://asgi.readthedocs.io/en/latest/specs/www.html#response-start

        Args:
            media_type: Default media type to use for the Content-Type
                header if the header was not set explicitly (default ``None``).

        """

        headers = self._headers
        # PERF(vytas): uglier inline version of Response._set_media_type
        if media_type is not None and 'content-type' not in headers:
            headers['content-type'] = media_type

        try:
            # NOTE(vytas): Supporting ISO-8859-1 for historical reasons as per
            #   RFC 7230, Section 3.2.4; and to strive for maximum
            #   compatibility with WSGI.

            # PERF(vytas): On CPython, _encode_items_to_latin1 is implemented
            #   in Cython (with a pure Python fallback), where the resulting
            #   C code speeds up the method substantially by directly invoking
            #   CPython's C API functions such as PyUnicode_EncodeLatin1.
            items = _encode_items_to_latin1(headers)
        except UnicodeEncodeError as ex:
            # TODO(vytas): In 3.1.0, update this error message to highlight the
            #   fact that we decided to allow ISO-8859-1?
            raise ValueError(
                'The modern series of HTTP standards require that header names and values '
                f'use only ASCII characters: {ex}'
            )

        if self._extra_headers:
            items += [(n.encode('ascii'), v.encode('ascii')) for n, v in self._extra_headers]

        # NOTE(kgriffs): It is important to append these after self._extra_headers
        #   in case the latter contains Set-Cookie headers that should be
        #   overridden by a call to unset_cookie().
        if self._cookies is not None:
            # PERF(tbug):
            # The below implementation is ~23% faster than
            # the alternative:
            #
            #     self._cookies.output().split("\\r\\n")
            #
            # Even without the .split("\\r\\n"), the below
            # is still ~17% faster, so don't use .output()
            items += [(b'set-cookie', c.OutputString().encode('ascii'))
                      for c in self._cookies.values()]
        return items
