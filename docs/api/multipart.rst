.. _multipart:

Multipart Forms
===============

.. contents:: :local:

Falcon features easy and efficient access to submitted multipart forms by using
:class:`falcon.media.MultipartFormHandler` to handle the
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

Parsing Options
---------------

.. autoclass:: falcon.media.multipart.MultipartParseOptions
    :members:

Parsing Errors
--------------

.. autoclass:: falcon.media.multipart.MultipartParseError
    :members:
