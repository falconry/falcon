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
        def on_post(self, req, resp):
            pass

        def on_get(self, req, resp):
            pass

Falcon :ref:`middleware components <middleware>` can also be used to insert
logic before and after requests. However, unlike hooks,
:ref:`middleware components <middleware>` are triggered **globally** for all
requests.

.. automodule:: falcon
    :members: before, after
    :undoc-members:
