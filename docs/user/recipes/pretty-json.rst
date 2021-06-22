.. _prettifying-json-responses:

Prettifying JSON Responses
==========================

To make JSON responses more human-readable, it may be desirable to
prettify the output. By default, Falcon's :class:`JSONHandler
<falcon.media.JSONHandler>` is configured to minimize serialization overhead.
However, you can easily customize the output by simply providing the
desired ``dumps`` parameters:

.. code:: python

    import functools
    import json

    from falcon import media

    json_handler = media.JSONHandler(
        dumps=functools.partial(json.dumps, indent=4, sort_keys=True),
    )

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

.. code:: python

    import cgi
    import json

    import falcon


    class CustomJSONHandler(falcon.media.BaseHandler):
        MAX_INDENT_LEVEL = 8

        def deserialize(self, stream, content_type, content_length):
            data = stream.read()
            return json.loads(data.decode())

        def serialize(self, media, content_type):
            _, params = cgi.parse_header(content_type)
            indent = params.get('indent')
            if indent is not None:
                try:
                    indent = int(indent)
                    # NOTE: Impose a reasonable indentation level limit.
                    if indent < 0 or indent > self.MAX_INDENT_LEVEL:
                        indent = None
                except ValueError:
                    # TODO: Handle invalid params?
                    indent = None

            result = json.dumps(media, indent=indent, sort_keys=bool(indent))
            return result.encode()

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
