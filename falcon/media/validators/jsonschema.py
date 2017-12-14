from __future__ import absolute_import

import falcon

try:
    import jsonschema
except ImportError:
    pass


def validate(schema):
    """Decorator for validating ``req.media`` using JSON Schema.

    This decorator provides standard JSON Schema validation via the
    ``jsonschema`` package available from PyPI. Semantic validation via
    the *format* keyword is enabled for the default checkers implemented
    by ``jsonschema.FormatChecker``.

    Note:
        The `jsonschema`` package must be installed separately in order to use
        this decorator, as Falcon does not install it by default.

    Args:
        schema (dict): A dictionary that follows the JSON Schema specification.
            See `json-schema.org <http://json-schema.org/>`_ for more
            information on defining a compatible dictionary.

    Example:
        .. code:: python

            from falcon.media.validators import jsonschema

            # -- snip --

            @jsonschema.validate(my_post_schema)
            def on_post(self, req, resp):

            # -- snip --

    """

    def decorator(func):
        def wrapper(self, req, resp, *args, **kwargs):
            try:
                jsonschema.validate(req.media, schema, format_checker=jsonschema.FormatChecker())
            except jsonschema.ValidationError as e:
                raise falcon.HTTPBadRequest(
                    'Failed data validation',
                    description=e.message
                )

            return func(self, req, resp, *args, **kwargs)
        return wrapper
    return decorator
