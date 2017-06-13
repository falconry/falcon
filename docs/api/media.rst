.. _media:

Media
=====

Falcon allows for easy and customizable internet media type handling. By default
Falcon only enables a single JSON handler. However, additional handlers
can be configured through the :any:`falcon.RequestOptions` and
:any:`falcon.ResponseOptions` objects specified on your :any:`falcon.API`.

.. note::

    To avoid unnecessary overhead, Falcon will only process request media
    the first time the media property is referenced. Once it has been
    referenced, it'll use the cached result for subsequent interactions.

Usage
-----

Zero configuration is needed if you're creating a JSON API. Just access
or set the ``media`` attribute as appropriate and let Falcon do the heavy
lifting for you.

.. code:: python

    import falcon


    class EchoResource(object):
        def on_post(self, req, resp):
            message = req.media.get('message')

            resp.media = {'message': message}
            resp.status = falcon.HTTP_200

.. warning::

    Once `media` is called on a request, it'll consume the request's stream.

Validating Media
----------------

Falcon currently does not validate media for you as requirements and tooling
vary quite largely between projects; however, here is an example of how you
might go about implementing a JSON Schema validator using a decorator.

.. code:: python

    import jsonschema


    def validate(schema):
        def decorator(func):
            def wrapper(self, req, resp, *args, **kwargs):
                try:
                    jsonschema.validate(req.media, schema)
                except jsonschema.ValidationError as e:
                    raise falcon.HTTPBadRequest(
                        'Failed data validation',
                        e.message
                    )

                return func(self, req, resp, *args, **kwargs)
            return wrapper
        return decorator


Given that decorator you could use it on the resource as such:

.. code:: python

    # -- snip --

    @validate(my_post_schema)
    def on_post(self, req, resp):
    # -- snip --


Replacing The Default Handlers
------------------------------

When creating your API object you can either add or completely
replace all of the handlers. For example, lets say you want to write an API
that sends and receives MessagePack. We can easily do this by telling our
Falcon API that we want a default media-type of ``application/msgpack`` and
then create a new :any:`Handlers` object specifying the desired media type and
a handler that can process that data.

.. code:: python

    import falcon
    from falcon import media


    handlers = media.Handlers({
        'application/msgpack': media.MessagePackHandler,
    })

    api = falcon.API(media_type='application/msgpack')

    api.req_options.media_handlers = handlers
    api.resp_options.media_handlers = handlers


Custom Handlers
---------------

Currently Falcon only supports a handful of media handlers out of the box;
however, you can easily create your own using the following abstract base
class:

.. autoclass:: falcon.media.BaseHandler
    :members:
    :member-order: bysource


Handlers
--------

.. autoclass:: falcon.media.Handlers
    :members:
