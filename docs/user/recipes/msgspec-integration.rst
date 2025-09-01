.. _msgspec_recipe:

Msgspec Integration
===================

This recipe illustrates how the popular
`msgspec <https://jcristharif.com/msgspec/>`__ data serialization and
validation library can be used with Falcon.

Media handlers
--------------

``msgspec`` can be used for JSON serialization by simply instantiating
:class:`~falcon.media.JSONHandler` with the ``msgspec.json.decode()`` and
``msgspec.json.encode()`` functions:

.. literalinclude:: ../../../examples/recipes/msgspec_json_handler.py
    :language: python

.. note::
    It would be more efficient to use preconstructed ``msgspec.json.Decoder``
    and ``msgspec.json.Encoder`` instead of initializing them every time via
    ``msgspec.json.decode()`` and ``msgspec.json.encode()``, respectively.
    This optimization is left as an exercise for the reader.

Using ``msgspec`` for handling MessagePack (or YAML) media is slightly more
involved, as we need to implement the :class:`~falcon.media.BaseHandler`
interface:

.. literalinclude:: ../../../examples/recipes/msgspec_msgpack_handler.py
    :language: python

.. attention::
    In contrast to :class:`~falcon.media.JSONHandler`, we would also need to
    implement error handling for invalid MessagePack payload. See more in the
    below chapter: :ref:`msgspec_error_handling`.

We can now use these handlers for request and response media
(see also: :ref:`custom_media_handlers`).

Media validation
----------------

Falcon currently only provides optional
:ref:`media validation <media_validation>` using JSON Schema, so we will
implement validation separately using
:ref:`process_resource middleware <middleware>`. To that end, let us assume
that resources can expose schema attributes based on the HTTP verb:
``PATCH_SCHEMA``, ``POST_SCHEMA``, etc, pointing to the ``msgspec.Struct`` in
question. We will inject the validated object into `params`:

.. literalinclude:: ../../../examples/recipes/msgspec_media_validation.py
    :language: python

Here, the name of the injected parameter is simply a lowercase version of the
schema's class name. We could instead store this name in a constant on the
resource, or on the schema class.

Note that while the above middleware is only suitable for synchronous (WSGI)
Falcon applications, you could easily transform this method to ``async``, or
even implement an async version in parallel on the same middleware as
``process_request_async(...)``. Just do not forget to ``await``
:meth:`req.get_media() <falcon.asgi.Request.get_media>`!

The astute reader may also notice that the process can be optimized even
further, as ``msgspec`` affords combined deserialization and validation in a
single call to ``decode()`` without going via an intermediate Python object
(in this case, effectively :meth:`req.media <falcon.Request.get_media>`).
However, if one wants to support more than just a single request media handler,
all the media functionality would need to be reimplemented almost from scratch.

We are looking into providing better affordances for this scenario in the
framework itself (see also
`#2202 <https://github.com/falconry/falcon/issues/2202>`__ on GitHub), as well
as offering centralized media validation connected to the application's
OpenAPI specification. Your input is extremely valuable for us, so do not
hesitate to :ref:`get in touch <chat>`, and share your vision!

.. _msgspec_error_handling:

Error handling
--------------

Schema validation can fail, and the resulting exception would unexpectedly
bubble up as a generic HTTP 500 error. We can do better!
Skimming through ``msgspec``\'s docs, we find out that this
case is represented by ``msgspec.ValidationError``. We could either create an
:meth:`error hander <falcon.App.add_error_handler>` that reraises this
exception as :class:`~falcon.MediaValidationError`, or just use a
``try.. except`` clause, and reraise directly inside middleware.

``msgspec.json.decode()`` has another peculiarity: unlike the stdlib's
:mod:`json` or the majority of other JSON libraries, ``msgspec.DecodeError`` is
not a subclass of :class:`ValueError`:

>>> import msgspec
>>> issubclass(msgspec.DecodeError, ValueError)
False

Falcon's :class:`~falcon.media.JSONHandler` works around this discrepancy by
detecting the actual deserialization exception type at the time of
initialization, but you may still encounter the issue when using the library
manually, or when using it for other media types such as MessagePack
(see above).
Furthermore, the problem has been reported upstream,
and received positive feedback from the maintainer, so hopefully it could get
resolved in the near future.

Complete recipe
---------------

Finally, we combine these snippets into a note taking application:

.. literalinclude:: ../../../examples/recipes/msgspec_main.py
    :language: python

We can now ``POST`` a new note, view the whole collection, or just ``GET`` an
individual note. (MessagePack support was omitted for brevity.)
