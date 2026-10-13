.. _custom-error-handling-recipe:

Customizing Error Handling
==========================

Falcon maps uncaught exceptions to HTTP responses through two
collaboration points:

* :meth:`~falcon.App.add_error_handler` — register callables that run when a
  matching exception type is raised from a responder, hook, or middleware.
* :meth:`~falcon.App.set_error_serializer` — control how instances of
  :class:`~falcon.HTTPError` are rendered for the client (media type,
  body shape, and related headers).

Handlers may either mutate ``resp`` directly or raise another
:class:`~falcon.HTTPError` / :class:`~falcon.HTTPStatus` so the framework
(and your serializer) finish the response. Prefer raising framework errors
when you want consistent representation across the app; write to ``resp``
when you need a one-off format for that exception type.

The following recipe wires both pieces together. A custom serializer
honors ``Accept`` (JSON vs plain text), while an ``OverflowError`` handler
either re-raises :class:`~falcon.HTTPBadRequest` or returns
``422 Unprocessable Entity`` with a text body:

.. literalinclude:: ../../../examples/recipes/custom_error_handling.py
    :language: python

Try a few requests against a local server hosting ``app``::

    $ http GET localhost:8000/division/1/0
    HTTP/1.1 500 Internal Server Error
    ...

    $ http GET localhost:8000/exponentiation/2/10000 Accept:text/plain
    HTTP/1.1 400 Bad Request
    content-type: text/plain; charset=utf-8
    ...
    [Custom error serializer]
    title: Too Damn High!

    $ http GET localhost:8000/exponentiation/10/400 Accept:text/plain
    HTTP/1.1 422 Unprocessable Entity
    ...
    That was too much to handle... Check your parameters.

See also :ref:`errors`, :ref:`faq`, and the discussion in
`#1324 <https://github.com/falconry/falcon/issues/1324>`__ /
`#2692 <https://github.com/falconry/falcon/issues/2692>`__.
