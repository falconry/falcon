.. _msgspec-recipe:

Basic msgspec integration
=========================

This recipe illustrates how the popular
`msgspec <https://jcristharif.com/msgspec/>`__ data serialization and
validation library can be used with Falcon.

Media handlers
--------------

``msgspec`` can be used for JSON serialization by simply instantiating
:class:`~falcon.media.JSONHandler` with the ``msgspec.json.decode`` and
``msgspec.json.encode`` functions:

.. literalinclude:: ../../../examples/recipes/msgspec_json_handler.py
    :language: python

.. note::
   It would be more efficient to use preconstructed ``msgspec.json.Decoder``
   and ``msgspec.json.Encoder`` instead of initializing them every time via
   ``msgspec.json.decode`` and ``msgspec.json.encode``, respectively.
   This optimization is left as an exercise for the reader.

Using ``msgspec`` for handling MessagePack (or YAML) media is slightly more
involved, as we need to implement the :class:`~falcon.media.BaseHandler`
interface:

.. literalinclude:: ../../../examples/recipes/msgspec_msgpack_handler.py
    :language: python

We can now use these handlers for request and response media
(see also: :ref:`custom_media_handlers`).


(Work in progress...)
