.. _error_handling_recipe:

Customizing Error Handling
===========================

By default, Falcon handles any raised instance of :class:`~falcon.HTTPError`
(or :class:`~falcon.HTTPStatus`) by rendering it as a JSON response. Any
other unhandled exception results in a generic
``500 Internal Server Error`` response, also rendered as JSON.

This recipe demonstrates two complementary ways to customize this behavior:
using a custom error serializer to change *how* errors are rendered across
the board, and using :meth:`~falcon.App.add_error_handler` to customize
*what happens* when a specific exception type is raised.

(See also: :ref:`errors`.)

Custom Error Serializer
------------------------

By default, Falcon serializes errors as JSON regardless of what media type
the client prefers. We can override this using
:meth:`~falcon.App.set_error_serializer` to negotiate the response format
based on the ``Accept`` header:

.. tab-set::

    .. tab-item:: WSGI
        :sync: wsgi

        .. literalinclude:: ../../../examples/recipes/error_handling_serializer_wsgi.py
            :language: python

    .. tab-item:: ASGI
        :sync: asgi

        .. literalinclude:: ../../../examples/recipes/error_handling_serializer_asgi.py
            :language: python

With this serializer in place, requesting the above resource with an
unsatisfiable division (e.g., dividing by zero) will trigger Falcon's
default ``500`` response, but rendered as plain text if the client sent
``Accept: text/plain``, or JSON otherwise.

Custom Error Handler
----------------------

Sometimes it is more convenient to intercept a specific exception type and
decide how to handle it inline, rather than (or in addition to) customizing
the serializer. :meth:`~falcon.App.add_error_handler` lets us register a
handler for a given exception class. From within the handler we can either:

* Render a response directly (by setting ``resp.status``, ``resp.text``,
  etc.), or
* Re-raise the exception as an instance of :class:`~falcon.HTTPError`, and
  let Falcon render it as usual.

The following example does both, depending on the value of one of the
routed URI parameters:

.. tab-set::

    .. tab-item:: WSGI
        :sync: wsgi

        .. literalinclude:: ../../../examples/recipes/error_handling_custom_wsgi.py
            :language: python

    .. tab-item:: ASGI
        :sync: asgi

        .. literalinclude:: ../../../examples/recipes/error_handling_custom_asgi.py
            :language: python

Here, requesting a small enough exponentiation that still overflows
(``OverflowError``) results in a custom ``422 Unprocessable Entity`` plain
text response. However, once the requested power reaches ``1000`` or more,
the handler instead raises :class:`~falcon.HTTPBadRequest`, which Falcon
renders as a standard JSON error response.