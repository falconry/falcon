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

Falcon currently only supports a JSONSchema media type handler; however,
JSONSchema is very versatile and can be used to validate any deserialized
media type that JSON also supports (i.e. dicts, lists, etc).

.. autofunction:: falcon.media.validators.jsonschema.validate


Content-Type Negotiation
------------------------

Falcon currently only supports partial negotiation out of the box. By default,
when the ``media`` attribute is used it attempts to de/serialize based on the
``Content-Type`` header value. The missing link that Falcon doesn't provide
is the connection between the :any:`falcon.Request` ``Accept`` header provided
by a user and the :any:`falcon.Response` ``Content-Type`` header.


Replacing The Default Handlers
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

Supported Handler Types
-----------------------

.. autoclass:: falcon.media.JSONHandler
    :members:

.. autoclass:: falcon.media.MessagePackHandler
    :members:

Custom Handler Type
-------------------

If Falcon doesn't have a internet media type handler that supports your
use-case. You can easily implement your own using the abstract base class
provided by Falcon:

.. autoclass:: falcon.media.BaseHandler
    :members:
    :member-order: bysource


Handlers
--------

.. autoclass:: falcon.media.Handlers
    :members:
