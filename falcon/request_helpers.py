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
from falcon.errors import HTTPMissingParam, HTTPInvalidParam

# Globals defined for the benefit of ParamProxy, below
TRUE_STRINGS = ('true', 'True', 'yes')
FALSE_STRINGS = ('false', 'False', 'no')


def header_property(wsgi_name):
    """Creates a read-only header property.
n
    Args:
        wsgi_name (str): Case-sensitive name of the header as it would
            appear in the WSGI environ ``dict`` (i.e., 'HTTP_*')

    Returns:
        A property instance than can be assigned to a class variable.

    """

    def fget(self):
        try:
            return self.env[wsgi_name] or None
        except KeyError:
            return None

    return property(fget)


class Body(object):
    """Wrap *wsgi.input* streams to make them more robust.

    ``socket._fileobject`` and ``io.BufferedReader`` are sometimes used
    to implement *wsgi.input*. However, app developers are often burned
    by the fact that the `read()` method for these objects block
    indefinitely if either no size is passed, or a size greater than
    the request's content length is passed to the method.

    This class normalizes *wsgi.input* behavior between WSGI servers
    by implementing non-blocking behavior for the cases mentioned
    above.

    Args:
        stream: Instance of ``socket._fileobject`` from
            ``environ['wsgi.input']``
        stream_len: Expected content length of the stream.

    """

    def __init__(self, stream, stream_len):
        self.stream = stream
        self.stream_len = stream_len

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.stream)

    next = __next__

    def _read(self, size, target):
        """Helper function for proxying reads to the underlying stream.

        Args:
            size (int): Maximum number of bytes/characters to read.
                Will be coerced, if None or -1, to `self.stream_len`. Will
                likewise be coerced if greater than `self.stream_len`, so
                that if the stream doesn't follow standard io semantics,
                the read won't block.
            target (callable): Once `size` has been fixed up, this function
                will be called to actually do the work.

        Returns:
            Data read from the stream, as returned by `target`.

        """

        if size is None or size == -1 or size > self.stream_len:
            size = self.stream_len

        return target(size)

    def read(self, size=None):
        """Read from the stream.

        Args:
            size (int): Maximum number of bytes/characters to read.
                Defaults to reading until EOF.

        Returns:
            Data read from the stream.

        """

        return self._read(size, self.stream.read)

    def readline(self, limit=None):
        """Read a line from the stream.

        Args:
            limit (int): Maximum number of bytes/characters to read.
                Defaults to reading until EOF.

        Returns:
            Data read from the stream.

        """

        return self._read(limit, self.stream.readline)

    def readlines(self, hint=None):
        """Read lines from the stream.

        Args:
            hint (int): Maximum number of bytes/characters to read.
                Defaults to reading until EOF.

        Returns:
            Data read from the stream.

        """

        return self._read(hint, self.stream.readlines)


class ParamProxy(object):
    """
    Provide `get_*` methods for both query-string parameters and
    request body parameters.
    """

    def __init__(self, request, source):
        self.req = request
        self.source = source

    def get(self, name, required=False, store=None):
        """Return the raw value of a query string parameter as a string.

        Note:
            Similar to the way multiple keys in form data is handled,
            if a query parameter is assigned a comma-separated list of
            values (e.g., 'foo=a,b,c'), only one of those values will be
            returned, and it is undefined which one. Use
            `req.get_param_as_list()` to retrieve all the values.

        Args:
            name (str): Parameter name, case-sensitive (e.g., 'sort').
            required (bool, optional): Set to ``True`` to raise
                ``HTTPBadRequest`` instead of returning ``None`` when the
                parameter is not found (default ``False``).
            store (dict, optional): A ``dict``-like object in which to place
                the value of the param, but only if the param is present.

        Returns:
            str: The value of the param as a string, or ``None`` if param is
                not found and is not required.

        Raises:
            HTTPBadRequest: A required param is missing from the request.

        """

        params = self.source

        # PERF: Use if..in since it is a good all-around performer; we don't
        #       know how likely params are to be specified by clients.
        if name in params:
            # NOTE(warsaw): If the key appeared multiple times, it will be
            # stored internally as a list.  We do not define which one
            # actually gets returned, but let's pick the last one for grins.
            param = params[name]
            if isinstance(param, list):
                param = param[-1]

            if store is not None:
                store[name] = param

            return param

        if not required:
            return None

        raise HTTPMissingParam(name)

    def get_as_int(self, name,
                   required=False, min=None, max=None, store=None):
        """Return the value of a query string parameter as an int.

        Args:
            name (str): Parameter name, case-sensitive (e.g., 'limit').
            required (bool, optional): Set to ``True`` to raise
                ``HTTPBadRequest`` instead of returning ``None`` when the
                parameter is not found or is not an integer (default
                ``False``).
            min (int, optional): Set to the minimum value allowed for this
                param. If the param is found and it is less than min, an
                ``HTTPError`` is raised.
            max (int, optional): Set to the maximum value allowed for this
                param. If the param is found and its value is greater than
                max, an ``HTTPError`` is raised.
            store (dict, optional): A ``dict``-like object in which to place
                the value of the param, but only if the param is found
                (default ``None``).

        Returns:
            int: The value of the param if it is found and can be converted to
                an integer. If the param is not found, returns ``None``, unless
                `required` is ``True``.

        Raises
            HTTPBadRequest: The param was not found in the request, even though
                it was required to be there. Also raised if the param's value
                falls outside the given interval, i.e., the value must be in
                the interval: min <= value <= max to avoid triggering an error.

        """

        params = self.source

        # PERF: Use if..in since it is a good all-around performer; we don't
        #       know how likely params are to be specified by clients.
        if name in params:
            val = params[name]
            if isinstance(val, list):
                val = val[-1]

            try:
                val = int(val)
            except ValueError:
                msg = 'The value must be an integer.'
                raise HTTPInvalidParam(msg, name)

            if min is not None and val < min:
                msg = 'The value must be at least ' + str(min)
                raise HTTPInvalidParam(msg, name)

            if max is not None and max < val:
                msg = 'The value may not exceed ' + str(max)
                raise HTTPInvalidParam(msg, name)

            if store is not None:
                store[name] = val

            return val

        if not required:
            return None

        raise HTTPMissingParam(name)

    def get_as_bool(self, name, required=False, store=None,
                    blank_as_true=False):
        """Return the value of a query string parameter as a boolean

        The following boolean strings are supported::

            TRUE_STRINGS = ('true', 'True', 'yes')
            FALSE_STRINGS = ('false', 'False', 'no')

        Args:
            name (str): Parameter name, case-sensitive (e.g., 'detailed').
            required (bool, optional): Set to ``True`` to raise
                ``HTTPBadRequest`` instead of returning ``None`` when the
                parameter is not found or is not a recognized boolean
                string (default ``False``).
            store (dict, optional): A ``dict``-like object in which to place
                the value of the param, but only if the param is found (default
                ``None``).
            blank_as_true (bool): If ``True``, an empty string value will be
                treated as ``True``. Normally empty strings are ignored; if
                you would like to recognize such parameters, you must set the
                `keep_blank_qs_values` request option to ``True``. Request
                options are set globally for each instance of ``falcon.API``
                through the `req_options` attribute.

        Returns:
            bool: The value of the param if it is found and can be converted
                to a ``bool``. If the param is not found, returns ``None``
                unless required is ``True``.

        Raises:
            HTTPBadRequest: A required param is missing from the request.

        """

        params = self.source

        # PERF: Use if..in since it is a good all-around performer; we don't
        #       know how likely params are to be specified by clients.
        if name in params:
            val = params[name]
            if isinstance(val, list):
                val = val[-1]

            if val in TRUE_STRINGS:
                val = True
            elif val in FALSE_STRINGS:
                val = False
            elif blank_as_true and not val:
                val = True
            else:
                msg = 'The value of the parameter must be "true" or "false".'
                raise HTTPInvalidParam(msg, name)

            if store is not None:
                store[name] = val

            return val

        if not required:
            return None

        raise HTTPMissingParam(name)

    def get_as_list(self, name,
                    transform=None, required=False, store=None):
        """Return the value of a query string parameter as a list.

        List items must be comma-separated or must be provided
        as multiple instances of the same param in the query string
        ala *application/x-www-form-urlencoded*.

        Args:
            name (str): Parameter name, case-sensitive (e.g., 'ids').
            transform (callable, optional): An optional transform function
                that takes as input each element in the list as a ``str`` and
                outputs a transformed element for inclusion in the list that
                will be returned. For example, passing ``int`` will
                transform list items into numbers.
            required (bool, optional): Set to ``True`` to raise
                ``HTTPBadRequest`` instead of returning ``None`` when the
                parameter is not found (default ``False``).
            store (dict, optional): A ``dict``-like object in which to place
                the value of the param, but only if the param is found (default
                ``None``).

        Returns:
            list: The value of the param if it is found. Otherwise, returns
            ``None`` unless required is True. Empty list elements will be
            discarded. For example a query string containing this::

                things=1,,3

            or a query string containing this::

                things=1&things=&things=3

            would both result in::

                ['1', '3']

        Raises:
            HTTPBadRequest: A required param is missing from the request.
            HTTPInvalidParam: A tranform function raised an instance of
                ``ValueError``.

        """

        params = self.source

        # PERF: Use if..in since it is a good all-around performer; we don't
        #       know how likely params are to be specified by clients.
        if name in params:
            items = params[name]

            # NOTE(warsaw): When a key appears multiple times in the request
            # query, it will already be represented internally as a list.
            # NOTE(kgriffs): Likewise for comma-delimited values.
            if not isinstance(items, list):
                items = [items]

            # PERF(kgriffs): Use if-else rather than a DRY approach
            # that sets transform to a passthrough function; avoids
            # function calling overhead.
            if transform is not None:
                try:
                    items = [transform(i) for i in items]

                except ValueError:
                    msg = 'The value is not formatted correctly.'
                    raise HTTPInvalidParam(msg, name)

            if store is not None:
                store[name] = items

            return items

        if not required:
            return None

        raise HTTPMissingParam(name)
