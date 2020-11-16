from functools import wraps
from inspect import iscoroutinefunction

import falcon

try:
    import jsonschema
except ImportError:  # pragma: nocover
    pass


def validate(req_schema=None, resp_schema=None, is_async=False):
    """Validate ``req.media`` using JSON Schema.

    This decorator provides standard JSON Schema validation via the
    ``jsonschema`` package available from PyPI. Semantic validation via
    the *format* keyword is enabled for the default checkers implemented
    by ``jsonschema.FormatChecker``.

    Note:
        The `jsonschema`` package must be installed separately in order to use
        this decorator, as Falcon does not install it by default.

        See `json-schema.org <http://json-schema.org/>`_ for more
        information on defining a compatible dictionary.

    Keyword Args:
        req_schema (dict): A dictionary that follows the JSON
            Schema specification. The request will be validated against this
            schema.
        resp_schema (dict): A dictionary that follows the JSON
            Schema specification. The response will be validated against this
            schema.
        is_async (bool): Set to ``True`` for ASGI apps to provide a hint that
            the decorated responder is a coroutine function (i.e., that it
            is defined with ``async def``) or that it returns an awaitable
            coroutine object.

            Normally, when the function source is declared using ``async def``,
            the resulting function object is flagged to indicate it returns a
            coroutine when invoked, and this can be automatically detected.
            However, it is possible to use a regular function to return an
            awaitable coroutine object, in which case a hint is required to let
            the framework know what to expect. Also, a hint is always required
            when using a cythonized coroutine function, since Cython does not
            flag them in a way that can be detected in advance, even when the
            function is declared using ``async def``.

    Example:

        .. tabs::

            .. tab:: WSGI

                .. code:: python

                    from falcon.media.validators import jsonschema

                    # -- snip --

                    @jsonschema.validate(my_post_schema)
                    def on_post(self, req, resp):

                    # -- snip --

            .. tab:: ASGI

                .. code:: python

                    from falcon.media.validators import jsonschema

                    # -- snip --

                    @jsonschema.validate(my_post_schema)
                    async def on_post(self, req, resp):

                    # -- snip --

            .. tab:: ASGI (Cythonized App)

                .. code:: python

                    from falcon.media.validators import jsonschema

                    # -- snip --

                    @jsonschema.validate(my_post_schema, is_async=True)
                    async def on_post(self, req, resp):

                    # -- snip --

    """

    def decorator(func):
        if iscoroutinefunction(func) or is_async:
            return _validate_async(func, req_schema, resp_schema)

        return _validate(func, req_schema, resp_schema)

    return decorator


def _validate(func, req_schema=None, resp_schema=None):
    @wraps(func)
    def wrapper(self, req, resp, *args, **kwargs):
        if req_schema is not None:
            try:
                jsonschema.validate(
                    req.media, req_schema,
                    format_checker=jsonschema.FormatChecker()
                )
            except jsonschema.ValidationError as e:
                raise falcon.HTTPBadRequest(
                    title='Request data failed validation',
                    description=e.message
                )

        result = func(self, req, resp, *args, **kwargs)

        if resp_schema is not None:
            try:
                jsonschema.validate(
                    resp.media, resp_schema,
                    format_checker=jsonschema.FormatChecker()
                )
            except jsonschema.ValidationError:
                raise falcon.HTTPInternalServerError(
                    title='Response data failed validation'
                    # Do not return 'e.message' in the response to
                    # prevent info about possible internal response
                    # formatting bugs from leaking out to users.
                )

        return result

    return wrapper


def _validate_async(func, req_schema=None, resp_schema=None):
    @wraps(func)
    async def wrapper(self, req, resp, *args, **kwargs):
        if req_schema is not None:
            m = await req.get_media()

            try:
                jsonschema.validate(
                    m, req_schema,
                    format_checker=jsonschema.FormatChecker()
                )
            except jsonschema.ValidationError as e:
                raise falcon.HTTPBadRequest(
                    title='Request data failed validation',
                    description=e.message
                )

        result = await func(self, req, resp, *args, **kwargs)

        if resp_schema is not None:
            try:
                jsonschema.validate(
                    resp.media, resp_schema,
                    format_checker=jsonschema.FormatChecker()
                )
            except jsonschema.ValidationError:
                raise falcon.HTTPInternalServerError(
                    title='Response data failed validation'
                    # Do not return 'e.message' in the response to
                    # prevent info about possible internal response
                    # formatting bugs from leaking out to users.
                )

        return result

    return wrapper
