.. _hooks:

Hooks
=====

Falcon supports both **before** and **after** hooks. You install a hook simply by
applying one of the decorators below either to an individual responder or
to an entire resource.

For example, suppose you had a hook like this:

.. code:: python

    def validate_image_type(req, resp, params):
        if req.content_type not in ALLOWED_IMAGE_TYPES:
            msg = 'Image type not allowed. Must be PNG, JPEG, or GIF'
            raise falcon.HTTPBadRequest('Bad request', msg)

You would attach the hook to an ``on_post`` responder like so:

.. code:: python

    @falcon.before(validate_image_type)
    def on_post(self, req, resp):
        pass

Or, if you had a hook that you would like to applied to *all*
responders for a given resource, you could install the hook like this:

.. code:: python

    @falcon.before(extract_project_id)
    class Message(object):
        pass

And you can apply hooks globally by passing them into the API class
initializer (note that this does not require the use of a decorator):

.. code:: python

    falcon.API(before=[extract_project_id])


.. automodule:: falcon
    :members: before, after
    :undoc-members:
