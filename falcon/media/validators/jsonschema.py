from __future__ import absolute_import

import falcon

try:
    import jsonschema
except ImportError:
    pass


def validate(schema_request=None, schema_response=None):
    """Decorator for validating ``req.media`` using JSON Schema.

    This decorator provides standard JSON Schema validation via the
    ``jsonschema`` package available from PyPI. Semantic validation via
    the *format* keyword is enabled for the default checkers implemented
    by ``jsonschema.FormatChecker``.

    Note:
        The `jsonschema`` package must be installed separately in order to use
        this decorator, as Falcon does not install it by default.

        See `json-schema.org <http://json-schema.org/>`_ for more
        information on defining a compatible dictionary.

    Args:
        schema_request (dict, optional): A dictionary that follows the JSON
            Schema specification. The request will be validated against this
            schema.
        schema_response (dict, optional): A dictionary that follows the JSON
            Schema specification. The response will be validated against this
            schema.

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
            if schema_request is not None:
                try:
                    jsonschema.validate(
                        req.media, schema_request,
                        format_checker=jsonschema.FormatChecker()
                    )
                except jsonschema.ValidationError as e:
                    raise falcon.HTTPBadRequest(
                        'Request data failed validation',
                        description=e.message
                    )

            result = func(self, req, resp, *args, **kwargs)

            if schema_response is not None:
                try:
                    jsonschema.validate(
                        resp.media, schema_response,
                        format_checker=jsonschema.FormatChecker()
                    )
                except jsonschema.ValidationError:
                    raise falcon.HTTPInternalServerError(
                        'Response data failed validation'
                        # Do not return 'e.message' in the response to
                        # prevent info about possible internal response
                        # formatting bugs from leaking out to users.
                    )

            return result
        return wrapper
    return decorator
