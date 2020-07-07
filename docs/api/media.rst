.. _media:

Media
=====

.. contents:: :local:

Falcon allows for easy and customizable internet media type handling. By
default Falcon only enables handlers for JSON and HTML (URL-encoded and
multipart) forms. However, additional handlers can be configured through the
:any:`falcon.RequestOptions` and :any:`falcon.ResponseOptions` objects
specified on your :any:`falcon.App`.

.. note::

    To avoid unnecessary overhead, Falcon will only process request media
    the first time the media property is referenced. Once it has been
    referenced, it'll use the cached result for subsequent interactions.

Usage
-----

Zero configuration is needed if you're creating a JSON API. Simply use
:meth:`~falcon.Request.get_media()` and :attr:`~falcon.Response.media` (WSGI)
, or :meth:`~falcon.asgi.Request.get_media()` and
:attr:`~falcon.asgi.Response.media` (ASGI) to let Falcon
do the heavy lifting for you.

.. tabs::

    .. tab:: WSGI

        .. code:: python

            import falcon


            class EchoResource:
                def on_post(self, req, resp):
                    # Deserialize the request body based on the Content-Type
                    #   header in the request, or the default media type
                    #   when the Content-Type header is generic ('*/*') or
                    #   missing.
                    obj = req.get_media()

                    message = obj.get('message')

                    # The framework will look for a media handler that matches
                    #   the response's Content-Type header, or fall back to the
                    #   default media type (typically JSON) when the app does
                    #   not explicitly set the Content-Type header.
                    resp.media = {'message': message}
                    resp.status = falcon.HTTP_200

    .. tab:: ASGI

        .. code:: python

            import falcon


            class EchoResource:
                async def on_post(self, req, resp):
                    # Deserialize the request body. Note that the ASGI version
                    #   of this method must be awaited.
                    obj = await req.get_media()

                    message = obj.get('message')

                    # The framework will look for a media handler that matches
                    #   the response's Content-Type header, or fall back to the
                    #   default media type (typically JSON) when the app does
                    #   not explicitly set the Content-Type header.
                    resp.media = {'message': message}
                    resp.status = falcon.HTTP_200

.. warning::

    Once :meth:`falcon.Request.get_media()` or
    :meth:`falcon.asgi.Request.get_media()` is called on a request, it will
    consume the request's body stream.

Validating Media
----------------

Falcon currently only provides a JSON Schema media validator; however,
JSON Schema is very versatile and can be used to validate any deserialized
media type that JSON also supports (i.e. dicts, lists, etc).

.. autofunction:: falcon.media.validators.jsonschema.validate

If JSON Schema does not meet your needs, a custom validator may be
implemented in a similar manner to the one above.

.. _content-type-negotiaton:

Content-Type Negotiation
------------------------

Falcon currently only supports partial negotiation out of the box. By default,
when the ``get_media()`` method or the ``media`` attribute is used, the
framework attempts to (de)serialize based on the ``Content-Type`` header value.
The missing link that Falcon doesn't provide is the connection between the
``Accept`` header provided by a user and the ``Content-Type`` header set on the
response.

If you do need full negotiation, it is very easy to bridge the gap using
middleware. Here is an example of how this can be done:

.. tabs::

    .. tab:: WSGI

        .. code:: python

            class NegotiationMiddleware:
                def process_request(self, req, resp):
                    resp.content_type = req.accept

    .. tab:: ASGI

        .. code:: python

            class NegotiationMiddleware:
                async def process_request(self, req, resp):
                    resp.content_type = req.accept


.. _custom_media_handlers:

Replacing the Default Handlers
------------------------------

When creating your App object you can either add or completely replace all of
the handlers. For example, let's say you want to write an API that sends and
receives `MessagePack <https://msgpack.org/>`_. We can easily do this by telling
our Falcon API that we want a default media type of ``application/msgpack`` and
then create a new :any:`Handlers` object specifying the desired media type and a
handler that can process that data.

.. code:: python

    import falcon
    from falcon import media


    handlers = media.Handlers({
        'application/msgpack': media.MessagePackHandler(),
    })

    app = falcon.App(media_type='application/msgpack')

    app.req_options.media_handlers = handlers
    app.resp_options.media_handlers = handlers

Alternatively, if you would like to add an additional handler without
removing the default handlers, this can be easily done as follows:

.. code-block:: python

    import falcon
    from falcon import media


    extra_handlers = {
        'application/msgpack': media.MessagePackHandler(),
    }

    app = falcon.App()

    app.req_options.media_handlers.update(extra_handlers)
    app.resp_options.media_handlers.update(extra_handlers)


Supported Handler Types
-----------------------

.. autoclass:: falcon.media.JSONHandler
    :no-members:

.. autoclass:: falcon.media.MessagePackHandler
    :no-members:

.. autoclass:: falcon.media.MultipartFormHandler
    :no-members:

.. autoclass:: falcon.media.URLEncodedFormHandler
    :no-members:

.. _custom-media-handler-type:

Custom Handler Type
-------------------

If Falcon doesn't have an Internet media type handler that supports your
use case, you can easily implement your own using the abstract base class
provided by Falcon:

.. autoclass:: falcon.media.BaseHandler
    :members:
    :member-order: bysource

.. tip::
    In order to use your custom media handler in a :ref:`Falcon app <app>`,
    you'll have to add an instance of your class to the app's media handlers
    (specified in :attr:`RequestOptions <falcon.RequestOptions.media_handlers>`
    and :attr:`ResponseOptions<falcon.ResponseOptions.media_handlers>`,
    respectively).

    See also: :ref:`custom_media_handlers`.


Handlers Mapping
----------------

.. autoclass:: falcon.media.Handlers
    :members:


.. _media_type_constants:

Media Type Constants
--------------------

The ``falcon`` module provides a number of constants for
common media type strings, including the following:

.. code:: python

    falcon.MEDIA_JSON
    falcon.MEDIA_MSGPACK
    falcon.MEDIA_MULTIPART
    falcon.MEDIA_URLENCODED
    falcon.MEDIA_YAML
    falcon.MEDIA_XML
    falcon.MEDIA_HTML
    falcon.MEDIA_JS
    falcon.MEDIA_TEXT
    falcon.MEDIA_JPEG
    falcon.MEDIA_PNG
    falcon.MEDIA_GIF
