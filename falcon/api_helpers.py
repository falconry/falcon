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

from falcon import util


def prepare_global_hooks(hooks):
    if hooks is not None:
        if not isinstance(hooks, list):
            hooks = [hooks]

        for action in hooks:
            if not callable(action):
                raise TypeError('One or more hooks are not callable')

    return hooks


def prepare_middleware(middleware=None):
    """Check middleware interface and prepare it to iterate.

    Args:
        middleware:  list (or object) of input middleware

    Returns:
        A middleware list
    """

    # PERF(kgriffs): do getattr calls once, in advance, so we don't
    # have to do them every time in the request path.
    prepared_middleware = []

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

        prepared_middleware.append((process_request, process_resource,
                                    process_response))

    return prepared_middleware


def default_serialize_error(req, exception):
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
        exception: Instance of ``falcon.HTTPError``

    Returns:
        A ``tuple`` of the form (*media_type*, *representation*), or
        (``None``, ``None``) if the client does not support any of the
        available media types.

    """
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

    return (preferred, representation)
