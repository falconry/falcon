.. _prettifying-json-responses:

Prettifying JSON Responses
==========================

To make JSON responses more human-readable, it may be desirable to
prettify the output. By default, Falcon's :class:`JSONHandler
<falcon.media.JSONHandler>` is configured to minimize serialization overhead.
However, you can easily customize the output by simply providing the
desired ``dumps`` parameters:

.. literalinclude:: ../../../examples/recipes/pretty_json_intro.py
    :language: python

You can now replace the default ``application/json``
:attr:`response media handlers <falcon.ResponseOptions.media_handlers>`
with this customized ``json_handler`` to make your application's JSON responses
prettier (see also: :ref:`custom_media_handlers`).

.. note::
    Another alternative for debugging is prettifying JSON on the client side,
    for example, the popular `HTTPie <https://httpie.org/>`_ does it by
    default. Another option is to simply pipe the JSON response into
    `jq <https://stedolan.github.io/jq/>`_.

    If your debugging case allows it, the client side approach should be
    preferred since it neither incurs performance overhead on the server side
    nor requires any customization effort.

Supporting optional indentation
-------------------------------

Internet media type (content-type) negotiation is the canonical way to
express resource representation preferences. Although not a part of the
``application/json`` media type standard, some frameworks (such as the Django
REST Framework) and services support requesting a specific JSON indentation
level using the ``indent`` content-type parameter. This recipe leaves the
interpretation to the reader as to whether such a parameter adds "new
functionality" as per `RFC 6836, Section 4.3
<https://tools.ietf.org/html/rfc6838#section-4.3>`_.

Assuming we want to add JSON ``indent`` support to a Falcon app, this can be
implemented with a :ref:`custom media handler <custom-media-handler-type>`:

.. literalinclude:: ../../../examples/recipes/pretty_json_main.py
    :language: python


Furthermore, we'll need to implement content-type negotiation to accept the
indented JSON content type for response serialization. The bare-minimum
example uses a middleware component as described here: :ref:`content-type-negotiaton`.

After installing this handler for ``application/json`` response media, as well
as adding the negotiation middleware, we should be able to produce indented
JSON output (building upon the frontpage ``QuoteResource`` example)::

    $ curl -H 'Accept: application/json; indent=4' http://localhost:8000/quote
    {
        "author": "Grace Hopper",
        "quote": "I've always been more interested in the future than in the past."
    }

.. warning::
    Implementing this in a public API available to untrusted, unauthenticated
    clients could be viewed as an unnecessary attack vector.

    In the case of a denial-of-service attack, you would be providing the
    attacker with a convenient way to increase CPU load by simply asking to
    indent the output, particularly if large JSON responses are available.

    Furthermore, replaying exactly the same requests with and without indentation
    may reveal information that is useful for timing attacks, especially if the
    attacker is able to guess the exact flavor of the JSON module used.
