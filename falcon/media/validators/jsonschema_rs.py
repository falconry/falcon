from __future__ import annotations

from typing import Any

from . import base as _base

try:
    import jsonschema_rs
except ImportError:  # pragma: nocover
    pass


def validate(req_schema: Any = None, resp_schema: Any = None, is_async: bool = False):
    """Validate ``req.media`` using JSON Schema.

    This decorator provides standard JSON Schema validation via the
    ``jsonschema_rs`` package available from PyPI.

    In the case of failed request media validation, an instance of
    :class:`~falcon.MediaValidationError` is raised by the decorator. By
    default, this error is rendered as a 400 (:class:`~falcon.HTTPBadRequest`)
    response with the ``title`` and ``description`` attributes explaining the
    validation failure, but this behavior can be modified by adding a
    custom error :func:`handler <falcon.App.add_error_handler>` for
    :class:`~falcon.MediaValidationError`.

    Note:
        The ``jsonschema_rs`` package must be installed separately in order to use
        this decorator, as Falcon does not install it by default.

        See `jsonschema_rs PyPi <https://pypi.org/project/jsonschema-rs/>`_ for more
        information on defining a compatible dictionary.

    Keyword Args:
        req_schema (dict or str): A dictionary that follows the JSON
            Schema specification. The request will be validated against this
            schema.
            Can be also a json string that will be loaded by the jsonschema_rs library
        resp_schema (dict or str): A dictionary that follows the JSON
            Schema specification. The response will be validated against this
            schema.
            Can be also a json string that will be loaded by the jsonschema_rs library
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

                    from falcon.media.validators import jsonschema_rs

                    # -- snip --

                    @jsonschema_rs.validate(my_post_schema)
                    def on_post(self, req, resp):

                    # -- snip --

            .. tab:: ASGI

                .. code:: python

                    from falcon.media.validators import jsonschema_rs

                    # -- snip --

                    @jsonschema_rs.validate(my_post_schema)
                    async def on_post(self, req, resp):

                    # -- snip --

            .. tab:: ASGI (Cythonized App)

                .. code:: python

                    from falcon.media.validators import jsonschema_rs

                    # -- snip --

                    @jsonschema_rs.validate(my_post_schema, is_async=True)
                    async def on_post(self, req, resp):

                    # -- snip --

    """

    return _base.validator_factory(
        JsonSchemaRsValidator, req_schema, resp_schema, is_async
    )


class JsonSchemaRsValidator(_base.Validator):
    def __init__(self, schema: Any) -> None:
        self.schema = schema
        if isinstance(schema, str):
            self.validator = jsonschema_rs.JSONSchema.from_str(schema)
        else:
            self.validator = jsonschema_rs.JSONSchema(schema)
        self.exceptions = jsonschema_rs.ValidationError

    @classmethod
    def from_schema(cls, schema: Any) -> JsonSchemaRsValidator:
        return cls(schema)

    def validate(self, media: Any) -> None:
        self.validator.validate(media)

    def get_exception_message(self, exception: jsonschema_rs.ValidationError):
        return exception.message
