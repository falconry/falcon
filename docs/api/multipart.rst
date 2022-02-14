.. _multipart:

Multipart Forms
===============

.. contents:: :local:

Falcon features easy and efficient access to submitted multipart forms by using
:class:`~falcon.media.MultipartFormHandler` to handle the
``multipart/form-data`` :ref:`media <media>` type. This handler is enabled by
default, allowing you to use ``req.get_media()`` to iterate over the
:class:`body parts <falcon.media.multipart.BodyPart>` in a form:

.. tabs::

    .. group-tab:: WSGI

        .. code:: python

            form = req.get_media()
            for part in form:
                if part.content_type == 'application/json':
                    # Body part is a JSON document, do something useful with it
                    resp.media = part.get_media()
                elif part.name == 'datafile':
                    while True:
                        # Do something with the uploaded data (file)
                        chunk = part.stream.read(8192)
                        if not chunk:
                            break
                        feed_data(chunk)
                elif part.name == 'imagedata':
                    # Store this body part in a file.
                    filename = os.path.join(UPLOAD_PATH, part.secure_filename)
                    with open(filename, 'wb') as dest:
                        part.stream.pipe(dest)
                else:
                    # Do something else
                    form_data[part.name] = part.text

    .. group-tab:: ASGI

        .. code:: python

            form = await req.get_media()
            async for part in form:
                if part.content_type == 'application/json':
                    # Body part is a JSON document, do something useful with it
                    resp.media = await part.get_media()
                elif part.name == 'datafile':
                    # Do something with the uploaded data (file)
                    async for chunk in part.stream:
                        await feed_data(chunk)
                elif part.name == 'imagedata':
                    # Store this body part in a file.
                    filename = os.path.join(UPLOAD_PATH, part.secure_filename)
                    async with aiofiles.open(filename, 'wb') as dest:
                        await part.stream.pipe(dest)
                else:
                    # Do something else
                    form_data[part.name] = await part.text

.. note::
   Rather than being read in and buffered all at once, the request stream is
   only consumed on-demand, while iterating over the body parts in the form.

   For each part, you can choose whether to read the whole part into memory,
   write it out to a file, or :ref:`upload it to the cloud
   <multipart_cloud_upload>`. Falcon offers straightforward support for all
   of these scenarios.

Body Part Type
--------------

.. autoclass:: falcon.media.multipart.BodyPart
    :members:
    :exclude-members: data, media, text

.. _multipart_parser_conf:

Parser Configuration
--------------------

Similar to :class:`falcon.App`\'s :attr:`~falcon.App.req_options` and
:attr:`~falcon.App.resp_options`, instantiating a
:class:`~falcon.media.MultipartFormHandler` also fills its
:attr:`~falcon.media.MultipartFormHandler.parse_options` attribute with a set
of sane default values suitable for many use cases out of the box. If you need
to customize certain form parsing aspects of your application, the preferred
way is to directly modify the properties of this attribute on the media handler
(parser) in question:

.. code:: python

    import falcon
    import falcon.media

    handler = falcon.media.MultipartFormHandler()

    # Assume text fields to be encoded in latin-1 instead of utf-8
    handler.parse_options.default_charset = 'latin-1'

    # Allow an unlimited number of body parts in the form
    handler.parse_options.max_body_part_count = 0

    # Afford parsing msgpack-encoded body parts directly via part.get_media()
    extra_handlers = {
        falcon.MEDIA_MSGPACK: falcon.media.MessagePackHandler(),
    }
    handler.parse_options.media_handlers.update(extra_handlers)

In order to use your customized handler in an app, simply replace the default
handler for ``multipart/form-data`` with the new one:

.. tabs::

    .. group-tab:: WSGI

        .. code:: python

            app = falcon.App()

            # handler is instantiated and configured as per the above snippet
            app.req_options.media_handlers[falcon.MEDIA_MULTIPART] = handler

    .. group-tab:: ASGI

        .. code:: python

            app = falcon.asgi.App()

            # handler is instantiated and configured as per the above snippet
            app.req_options.media_handlers[falcon.MEDIA_MULTIPART] = handler

.. tip::
    For more information on customizing media handlers, see also:
    :ref:`custom_media_handlers`.

Parsing Options
---------------

.. autoclass:: falcon.media.multipart.MultipartParseOptions
    :members:

Parsing Errors
--------------

.. autoclass:: falcon.media.multipart.MultipartParseError
    :members:
