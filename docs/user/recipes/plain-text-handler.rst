.. _plain_text_handler_recipe:

Handling Plain Text as Media
============================

Normally, it is easiest to render a plain text response by setting
:attr:`resp.text <falcon.Response.text>`
(see also: :ref:`resp_media_data_text`).
However, if plain text is just one of
the :ref:`Internet media types <media>` that your application speaks, it may be
useful to generalize handling plain text as :ref:`media <media>` too.

This recipe demonstrates how to create a
:ref:`custom media handler <custom-media-handler-type>` to process the
``text/plain`` media type. The handler implements serialization and
deserialization of textual content, respecting the charset specified in the
``Content-Type`` header
(or defaulting to ``utf-8`` when no charset is provided).

.. literalinclude:: ../../../examples/recipes/plain_text_main.py
    :language: python

To use this handler, :ref:`register <custom_media_handlers>` it in the Falcon
application's media options for both request and response:

.. code:: python

    import falcon
    from your_module import TextHandler

    app = falcon.App()
    app.req_options.media_handlers['text/plain'] = TextHandler()
    app.resp_options.media_handlers['text/plain'] = TextHandler()

With this setup, the application can handle textual data directly
as ``text/plain``, ensuring support for various character encodings as needed.

.. warning::
    Be sure to validate and limit the size of incoming data when working with
    textual content to prevent server overload or denial-of-service attacks.
