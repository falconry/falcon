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

"""Utilities for the API class."""

from falcon import util


def prepare_middleware(middleware=None, independent_middleware=False):
    """Check middleware interface and prepare it to iterate.

    Args:
        middleware: list (or object) of input middleware
        independent_middleware: bool whether should prepare request and
            response middleware independently

    Returns:
        list: A tuple of prepared middleware tuples
    """

    # PERF(kgriffs): do getattr calls once, in advance, so we don't
    # have to do them every time in the request path.
    request_mw = []
    resource_mw = []
    response_mw = []

    if middleware is None:
        middleware = []
    else:
        if not isinstance(middleware, list):
            middleware = [middleware]

    for component in middleware:
        process_request = util.get_bound_method(component,
                                                'process_request')
        process_resource = util.get_bound_method(component,
                                                 'process_resource')
        process_response = util.get_bound_method(component,
                                                 'process_response')

        if not (process_request or process_resource or process_response):
            msg = '{0} does not implement the middleware interface'
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
    if not exception.has_representation:
        return

    representation = None

    preferred = req.client_prefers(('application/xml',
                                    'text/xml',
                                    'application/json'))

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
            preferred = 'application/json'
        elif '+xml' in accept:
            preferred = 'application/xml'

    if preferred is not None:
        if preferred == 'application/json':
            representation = exception.to_json()
        else:
            representation = exception.to_xml()

        resp.body = representation

        # NOTE(kgriffs): No need to append the charset param, since
        #   utf-8 is the default for both JSON and XML.
        resp.content_type = preferred

    resp.append_header('Vary', 'Accept')


class CloseableStreamIterator(object):
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

    def next(self):
        return self.__next__()

    def close(self):
        try:
            self._stream.close()
        except (AttributeError, TypeError):
            pass
