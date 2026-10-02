.. _handling_custom_error:

Handling Custom Error
=====================

To handle your custom exception use :meth:`~.falcon.App.add_error_handler`.

To handle the output of the error use :meth:`~.falcon.App.set_error_serializer`.

.. tab-set::

    .. tab-item:: WSGI
        :sync: wsgi

        .. literalinclude:: ../../../examples/recipes/custom_error_wsgi.py
            :language: python

    .. tab-item:: ASGI
        :sync: asgi

        .. literalinclude:: ../../../examples/recipes/custom_error_asgi.py
            :language: python
