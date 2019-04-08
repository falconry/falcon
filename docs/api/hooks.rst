.. _hooks:

Hooks
=====

Falcon supports *before* and *after* hooks. You install a hook simply by
applying one of the decorators below, either to an individual responder or
to an entire resource.

For example, consider this hook that validates a POST request for
an image resource:

.. code:: python

    def validate_image_type(req, resp, resource, params):
        if req.content_type not in ALLOWED_IMAGE_TYPES:
            msg = 'Image type not allowed. Must be PNG, JPEG, or GIF'
            raise falcon.HTTPBadRequest('Bad request', msg)

You would attach this hook to an ``on_post`` responder like so:

.. code:: python

    @falcon.before(validate_image_type)
    def on_post(self, req, resp):
        pass

Or, suppose you had a hook that you would like to apply to *all*
responders for a given resource. In that case, you would simply
decorate the resource class:

.. code:: python

    @falcon.before(extract_project_id)
    class Message(object):
        def on_post(self, req, resp, project_id):
            pass

        def on_get(self, req, resp, project_id):
            pass

.. note::
    When decorating an entire resource class, all method names that resemble
    responders, including *suffix*\ed (see also :meth:`~falcon.API.add_route`)
    ones, are decorated. If, for instance, a method is called ``on_get_items``,
    but it is not meant for handling ``GET`` requests under a route with the
    *suffix* ``items``, the easiest workaround for preventing the hook function
    from being applied to the method is renaming it not to clash with the
    responder pattern.

Note also that you can pass additional arguments to your hook function
as needed:

.. code:: python

    def validate_image_type(req, resp, resource, params, allowed_types):
        if req.content_type not in allowed_types:
            msg = 'Image type not allowed.'
            raise falcon.HTTPBadRequest('Bad request', msg)

    @falcon.before(validate_image_type, ['image/png'])
    def on_post(self, req, resp):
        pass

Falcon supports using any callable as a hook. This allows for using a class
instead of a function:

.. code:: python

    class Authorize(object):
        def __init__(self, roles):
            self._roles = roles

        def __call__(self, req, resp, resource, params):
            pass

    @falcon.before(Authorize(['admin']))
    def on_post(self, req, resp):
        pass


Falcon :ref:`middleware components <middleware>` can also be used to insert
logic before and after requests. However, unlike hooks,
:ref:`middleware components <middleware>` are triggered **globally** for all
requests.

.. Tip::
    In order to pass data from a hook function to a resource function
    use the ``req.context`` and ``resp.context`` objects. These context objects
    are intended to hold request and response data specific to your app as it
    passes through the framework.

.. automodule:: falcon
    :members: before, after
    :undoc-members:
