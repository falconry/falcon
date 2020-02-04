.. _multipart:

Multipart Forms
===============

Falcon features easy and efficient access to submitted multipart forms by using
:class:`falcon.media.MultipartFormHandler` to handle the
``multipart/form-data`` :ref:`media <media>` type. This handler is enabled by
default, allowing you to use ``req.media`` to iterate over the
:class:`body parts <falcon.media.multipart.BodyPart>` in a form:

.. code:: python

    for part in req.media:
        if part.content_type == 'application/json':
            # TODO: Body part is a JSON document, do something useful with it
            resp.media = part.media
        elif part.name == 'datafile':
            while True:
                # Do something with the uploaded data (file)
                chunk = part.stream.read(8192)
                if not chunk:
                    break
                feed_data(chunk)
        elif part.name == 'imagedata':
            # Store this body part in a file.
            with open(path.join(UPLOADS, part.secure_filename), 'wb') as dest:
                part.stream.pipe(dest)
        else:
            # TODO: Do something else

.. note::
   The request stream is only consumed along iteration over the body parts in a
   form, rather than being read in and buffered all at once.

   You can then choose whether to read the whole part into the memory, store in
   a file, or :ref:`upload to the cloud <multipart_cloud_upload>`.
   Falcon offers straightforward support for all these scenarios.

Body Part Type
--------------

.. autoclass:: falcon.media.multipart.BodyPart
    :members:

Parsing Options
---------------

.. autoclass:: falcon.media.multipart.MultipartParseOptions
    :members:

Parsing Errors
--------------

.. autoclass:: falcon.media.multipart.MultipartParseError
    :members:
