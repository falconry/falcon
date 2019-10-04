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

from asyncio.coroutines import CoroWrapper
from inspect import iscoroutine

import falcon.response

__all__ = ['Response']


class Response(falcon.response.Response):
    """

    Attributes:
        sse (coroutine): A Server-Sent Event (SSE) emitter, implemented as
            an async coroutine function that returns an iterable
            of :py:class:`falcon.asgi.SSEent` instances. Each event will be
            serialized and sent to the client as HTML5 Server-Sent Events.

        data (bytes): Byte string representing response content.

            Use this attribute in lieu of `body` when your content is
            already a byte string (of type ``bytes``).

            Warning:
                Always use the `body` attribute for text, or encode it
                first to ``bytes`` when using the `data` attribute, to
                ensure Unicode characters are properly encoded in the
                HTTP response.

            Note:
                Unlike the WSGI Response class, the ASGI Response class
                does not implement the side-effect of serializing
                the media object (if one is set) when the `data`
                attribute is read. Instead,
                :py:meth:`falcon.asgi.Response.render_body` should
                be used to get the correct content for the response.
    """

    # PERF(kgriffs): These will be shadowed when set on an instance; let's
    #   us avoid having to implement __init__ and incur the overhead of
    #   an additional function call.
    _sse = None
    _registered_callbacks = None
    _media_rendered = None

    @property
    def sse(self):
        return self._sse

    @sse.setter
    def sse(self, value):
        self._sse = value

    @property
    def media(self):
        return self._media

    @media.setter
    def media(self, value):
        self._media = value
        self._media_rendered = None

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    async def render_body(self):
        """Get the raw content for the response body.

        This coroutine can be awaited to get the raw body data that should
        be returned in the HTTP response.

        Returns:
            bytes: The UTF-8 encoded value of the `body` attribute, if
                set. Otherwise, the value of the `data` attribute if set, or
                finally the serialized value of the `media` attribute. If
                none of these attributes are set, ``None`` is returned.
        """

        body = self.body
        if body is None:
            data = self._data

            if data is None and self._media is not None:
                if self._media_rendered is None:
                    if not self.content_type:
                        self.content_type = self.options.default_media_type

                    handler = self.options.media_handlers.find_by_media_type(
                        self.content_type,
                        self.options.default_media_type
                    )

                    self._media_rendered = await handler.serialize_async(
                        self._media,
                        self.content_type
                    )

                data = self._media_rendered
        else:
            try:
                # NOTE(kgriffs): Normally we expect body to be a string
                data = body.encode()
            except AttributeError:
                # NOTE(kgriffs): Assume it was a bytes object already
                data = body

        return data

    def schedule(self, callback):
        """Schedules a callback to run soon after sending the HTTP response.

        This method can be used to execute a background job after the
        response has been returned to the client.

        If the callback is an async coroutine function, it will be scheduled
        to run on the event loop as soon as possible. Alternatively, if a
        synchronous callable is passed, it will be run on the event loop's
        default ``Executor`` (which can be overridden via
        :py:meth:`asyncio.AbstractEventLoop.set_default_executor`).

        The callback will be invoked without arguments. Use
        :py:meth`functools.partial` to pass arguments to the callback
        as needed.

        Note:
            If an unhandled exception is raised while processing the request,
            the callback will not be scheduled to run.

        Note:
            When an SSE emitter has been set on the response, the callback will
            be scheduled before the first call to the emitter.

        Warning:
            Because coroutines run on the main request thread, care should
            be taken to ensure they are non-blocking. Long-running operations
            must use async libraries or delegate to an Executor pool to avoid
            blocking the processing of subsequent requests.

        Warning:
            Synchronous callables run on the event loop's default ``Executor``,
            which uses an instance of ``ThreadPoolExecutor`` unless
            :py:meth:`asyncio.AbstractEventLoop.set_default_executor` is used
            to change it to something else. Due to the GIL, CPU-bound jobs
            will block request processing for the current process unless
            the default ``Executor`` is changed to one that is process-based
            instead of thread-based (e.g., an instance of
            :py:class:`concurrent.futures.ProcessPoolExecutor`).

        Args:
            callback(object): An async coroutine function or a synchronous
                callable. The callback will be called without arguments.
        """

        # NOTE(kgriffs): We also have to do the CoroWrapper check because
        #   iscoroutine is less reliable under Python 3.6.
        if iscoroutine(callback) or isinstance(callback, CoroWrapper):
            raise TypeError(
                'The callback object appears to '
                'be a coroutine, rather than a coroutine function. Please '
                'pass the function itself, rather than the result obtained '
                'by calling the function. '
            )

        if not self._registered_callbacks:
            self._registered_callbacks = [callback]
        else:
            self._registered_callbacks.append(callback)

    def set_stream(self, stream, content_length):
        """Convenience method for setting both `stream` and `content_length`.

        Although the `stream` and `content_length` properties may be set
        directly, using this method ensures `content_length` is not
        accidentally neglected when the length of the stream is known in
        advance. Using this method is also slightly more performant
        as compared to setting the properties individually.

        Note:
            If the stream length is unknown, you can set `stream`
            directly, and ignore `content_length`. In this case, the
            ASGI server may choose to use chunked encoding for HTTP/1.1

        Args:
            stream: A readable, awaitable file-like object or async iterable that
                retuns byte strings. If the object implements a close() method, it
                will be called after reading all of the data.
            content_length (int): Length of the stream, used for the
                Content-Length header in the response.
        """

        self.stream = stream

        # PERF(kgriffs): Set directly rather than incur the overhead of
        #   the self.content_length property.
        self._headers['content-length'] = str(content_length)

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

        items = [(n.encode(), v.encode()) for n, v in headers.items()]

        if self._extra_headers:
            items += [(n.encode(), v.encode()) for n, v in self._extra_headers]

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
            items += [(b'set-cookie', c.OutputString().encode())
                      for c in self._cookies.values()]
        return items
