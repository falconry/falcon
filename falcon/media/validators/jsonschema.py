from __future__ import absolute_import

import falcon

try:
    import jsonschema
except ImportError:
    pass


def validate(schema):
    """Decorator that validates ``req.media`` using JSON Schema

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

    Note:
        This validator requires the ``jsonschema`` library available via
        PyPI. The library also requires Python 2.7+.
    """
    def decorator(func):
        def wrapper(self, req, resp, *args, **kwargs):
            try:
                jsonschema.validate(req.media, schema)
            except jsonschema.ValidationError as e:
                raise falcon.HTTPBadRequest(
                    'Failed data validation',
                    description=e.message
                )

            return func(self, req, resp, *args, **kwargs)
        return wrapper
    return decorator
