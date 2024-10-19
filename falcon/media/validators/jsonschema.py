from __future__ import annotations

from functools import wraps
from inspect import iscoroutinefunction
from typing import Any, Callable, Dict, Optional, TYPE_CHECKING

import falcon

try:
    import jsonschema
except ImportError:  # pragma: nocover
    pass

if TYPE_CHECKING:
    import falcon as wsgi
    from falcon import asgi

Schema = Optional[Dict[str, Any]]
ResponderMethod = Callable[..., Any]


def validate(
    req_schema: Schema = None, resp_schema: Schema = None
) -> Callable[[ResponderMethod], ResponderMethod]:
    """Validate ``req.media`` using JSON Schema.

    This decorator provides standard JSON Schema validation via the
    ``jsonschema`` package available from PyPI. Semantic validation via
    the *format* keyword is enabled for the default checkers implemented
    by ``jsonschema.FormatChecker``.

    In the case of failed request media validation, an instance of
    :class:`~falcon.MediaValidationError` is raised by the decorator. By
    default, this error is rendered as a 400 (:class:`~falcon.HTTPBadRequest`)
    response with the ``title`` and ``description`` attributes explaining the
    validation failure, but this behavior can be modified by adding a
    custom error :func:`handler <falcon.App.add_error_handler>` for
    :class:`~falcon.MediaValidationError`.

    Note:
        The ``jsonschema`` package must be installed separately in order to use
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

    Example:

        .. tab-set::

            .. tab-item:: WSGI

                .. code:: python

                    from falcon.media.validators import jsonschema

                    # -- snip --

                    @jsonschema.validate(my_post_schema)
                    def on_post(self, req, resp):

                    # -- snip --

            .. tab-item:: ASGI

                .. code:: python

                    from falcon.media.validators import jsonschema

                    # -- snip --

                    @jsonschema.validate(my_post_schema)
                    async def on_post(self, req, resp):

                    # -- snip --

    """

    def decorator(func: ResponderMethod) -> ResponderMethod:
        if iscoroutinefunction(func):
            return _validate_async(func, req_schema, resp_schema)

        return _validate(func, req_schema, resp_schema)

    return decorator


def _validate(
    func: ResponderMethod, req_schema: Schema = None, resp_schema: Schema = None
) -> ResponderMethod:
    @wraps(func)
    def wrapper(
        self: Any, req: wsgi.Request, resp: wsgi.Response, *args: Any, **kwargs: Any
    ) -> Any:
        if req_schema is not None:
            try:
                jsonschema.validate(
                    req.media, req_schema, format_checker=jsonschema.FormatChecker()
                )
            except jsonschema.ValidationError as ex:
                raise falcon.MediaValidationError(
                    title='Request data failed validation', description=ex.message
                ) from ex

        result = func(self, req, resp, *args, **kwargs)

        if resp_schema is not None:
            try:
                jsonschema.validate(
                    resp.media, resp_schema, format_checker=jsonschema.FormatChecker()
                )
            except jsonschema.ValidationError as ex:
                raise falcon.HTTPInternalServerError(
                    title='Response data failed validation'
                    # Do not return 'e.message' in the response to
                    # prevent info about possible internal response
                    # formatting bugs from leaking out to users.
                ) from ex

        return result

    return wrapper


def _validate_async(
    func: ResponderMethod, req_schema: Schema = None, resp_schema: Schema = None
) -> ResponderMethod:
    @wraps(func)
    async def wrapper(
        self: Any, req: asgi.Request, resp: asgi.Response, *args: Any, **kwargs: Any
    ) -> Any:
        if req_schema is not None:
            m = await req.get_media()

            try:
                jsonschema.validate(
                    m, req_schema, format_checker=jsonschema.FormatChecker()
                )
            except jsonschema.ValidationError as ex:
                raise falcon.MediaValidationError(
                    title='Request data failed validation', description=ex.message
                ) from ex

        result = await func(self, req, resp, *args, **kwargs)

        if resp_schema is not None:
            try:
                jsonschema.validate(
                    resp.media, resp_schema, format_checker=jsonschema.FormatChecker()
                )
            except jsonschema.ValidationError as ex:
                raise falcon.HTTPInternalServerError(
                    title='Response data failed validation'
                    # Do not return 'e.message' in the response to
                    # prevent info about possible internal response
                    # formatting bugs from leaking out to users.
                ) from ex

        return result

    return wrapper
