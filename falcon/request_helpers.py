"""Defines private helper functions for the Request class.

Copyright 2013 by Rackspace Hosting, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""


def normalize_headers(env):
    """Normalize HTTP headers in an WSGI environ dictionary.

    Args:
        env: A WSGI environ dictionary to normalize (in-place)

    Raises:
        KeyError: The env dictionary did not contain a key that is required by
            PEP-333.
        TypeError: env is not dictionary-like. In other words, it has no
            attribute '__getitem__'.

    """

    # NOTE(kgriffs): Per the WSGI spec, HOST, Content-Type, and
    # CONTENT_LENGTH are not under HTTP_* and so we normalize
    # that here.

    if 'CONTENT_TYPE' in env:
        env['HTTP_CONTENT_TYPE'] = env['CONTENT_TYPE']

    if 'CONTENT_LENGTH' in env:
        env['HTTP_CONTENT_LENGTH'] = env['CONTENT_LENGTH']

    # Fallback to SERVER_* vars if the Host header isn't specified
    if 'HTTP_HOST' not in env:
        host = env['SERVER_NAME']
        port = env['SERVER_PORT']

        if port != '80':
            host = ''.join([host, ':', port])

        env['HTTP_HOST'] = host


class Body(object):
    """Wrap wsgi.input streams to make them more robust.

    The socket._fileobject and io.BufferedReader are sometimes used
    to implement wsgi.input. However, app developers are often burned
    by the fact that the read() method for these objects block
    indefinitely if either no size is passed, or a size greater than
    the request's content length is passed to the method.

    This class normalizes wsgi.input behavior between WSGI servers
    by implementing non-blocking behavior for the cases mentioned
    above.
    """

    def __init__(self, stream, stream_len):
        """Initialize the request body instance.

        Args:
            stream: Instance of socket._fileobject from environ['wsgi.input']
            stream_len: Expected content length of the stream.
        """

        self.stream = stream
        self.stream_len = stream_len

        def _make_stream_reader(func):
            def read(size=None):
                if size is None or size > self.stream_len:
                    size = self.stream_len

                return func(size)

            return read

        # NOTE(kgriffs): All of the wrapped methods take a single argument,
        # which is a size AKA length AKA limit, always in bytes/characters.
        # This is consistent with Gunicorn's "Body" class.
        for attr in ('read', 'readline', 'readlines'):
            target = getattr(self.stream, attr)
            setattr(self, attr, _make_stream_reader(target))

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.stream)

    next = __next__
