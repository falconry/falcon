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
        else:
            # TODO: Do something else

Body Part Type
--------------

.. autoclass:: falcon.media.multipart.BodyPart
    :members:

Parsing Options
---------------

.. autodata:: falcon.media.multipart.DEFAULT_SUPPORTED_CHARSETS

.. autoclass:: falcon.media.multipart.MultipartParseOptions
    :members:

Parsing Errors
--------------

.. autoclass:: falcon.media.multipart.MultipartParseError
    :members:
