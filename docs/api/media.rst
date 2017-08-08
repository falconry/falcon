.. _media:

Media
=====

Falcon allows for easy and customizable internet media type handling. By default
Falcon only enables a single JSON handler. However, additional handlers
can be configured through the :any:`falcon.RequestOptions` and
:any:`falcon.ResponseOptions` objects specified on your :any:`falcon.API`.

.. note::

    To avoid unnecessary overhead, Falcon will only process request media
    the first time the media property is referenced. Once it has been
    referenced, it'll use the cached result for subsequent interactions.

Usage
-----

Zero configuration is needed if you're creating a JSON API. Just access
or set the ``media`` attribute as appropriate and let Falcon do the heavy
lifting for you.

.. code:: python

    import falcon


    class EchoResource(object):
        def on_post(self, req, resp):
            message = req.media.get('message')

            resp.media = {'message': message}
            resp.status = falcon.HTTP_200

.. warning::

    Once `media` is called on a request, it'll consume the request's stream.

Validating Media
----------------

Falcon currently only provides a JSON Schema media validator; however,
JSON Schema is very versatile and can be used to validate any deserialized
media type that JSON also supports (i.e. dicts, lists, etc).

.. autofunction:: falcon.media.validators.jsonschema.validate

If JSON Schema does not meet your needs, a custom validator may be
implemented in a similar manner to the one above.

Content-Type Negotiation
------------------------

Falcon currently only supports partial negotiation out of the box. By default,
when the ``media`` attribute is used it attempts to de/serialize based on the
``Content-Type`` header value. The missing link that Falcon doesn't provide
is the connection between the :any:`falcon.Request` ``Accept`` header provided
by a user and the :any:`falcon.Response` ``Content-Type`` header.

If you do need full negotiation, it is very easy to bridge the gap using
middleware. Here is an example of how this can be done:

.. code-block:: python

    class NegotiationMiddleware(object):
        def process_request(self, req, resp):
            resp.content_type = req.accept


Replacing the Default Handlers
------------------------------

When creating your API object you can either add or completely
replace all of the handlers. For example, lets say you want to write an API
that sends and receives MessagePack. We can easily do this by telling our
Falcon API that we want a default media-type of ``application/msgpack`` and
then create a new :any:`Handlers` object specifying the desired media type and
a handler that can process that data.

.. code:: python

    import falcon
    from falcon import media


    handlers = media.Handlers({
        'application/msgpack': media.MessagePackHandler(),
    })

    api = falcon.API(media_type='application/msgpack')

    api.req_options.media_handlers = handlers
    api.resp_options.media_handlers = handlers

Alternatively, if you would like to add an additional handler such as
MessagePack, this can be easily done in the following manner:

.. code-block:: python

    import falcon
    from falcon import media


    extra_handlers = {
        'application/msgpack': media.MessagePackHandler(),
    }

    api = falcon.API()

    api.req_options.media_handlers.update(extra_handlers)
    api.resp_options.media_handlers.update(extra_handlers)


Supported Handler Types
-----------------------

.. autoclass:: falcon.media.JSONHandler
    :members:

.. autoclass:: falcon.media.MessagePackHandler
    :members:

Custom Handler Type
-------------------

If Falcon doesn't have an internet media type handler that supports your
use case, you can easily implement your own using the abstract base class
provided by Falcon:

.. autoclass:: falcon.media.BaseHandler
    :members:
    :member-order: bysource


Handlers
--------

.. autoclass:: falcon.media.Handlers
    :members:


.. _media_type_constants:

Media Type Constants
--------------------

The ``falcon`` module provides a number of constants for
common media types, including the following:

.. code:: python

    falcon.MEDIA_JSON
    falcon.MEDIA_MSGPACK
    falcon.MEDIA_YAML
    falcon.MEDIA_XML
    falcon.MEDIA_HTML
    falcon.MEDIA_JS
    falcon.MEDIA_TEXT
    falcon.MEDIA_JPEG
    falcon.MEDIA_PNG
    falcon.MEDIA_GIF
