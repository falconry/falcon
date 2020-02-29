.. _inspect:

Inspect Module
==============

This module allows inspecting a Falcon application to obtain information
regarding the registered routes, middlewares, static routes, sinks and
error handlers using the corresponding functions of the module.
The entire application can be inspected by using the :func:`.inspect_app`

An example usage of the returned information is to obtain a string representation
of an application, like in the example below:

.. code:: python

    from falcon import inspect

    # app is a falcon application
    app_info = inspect.inspect_app(app)
    print(app_info)

The output would be:

.. code::

    Falcon App (WSGI)
    • Routes:
        ⇒ /foo - MyResponder:
           ├── DELETE - on_delete
           ├── GET - on_get
           └── POST - on_post
        ⇒ /foo/{id} - MyResponder:
           ├── DELETE - on_delete_id
           ├── GET - on_get_id
           └── POST - on_post_id
        ⇒ /bar - OtherResponder:
           ├── DELETE - on_delete_id
           ├── GET - on_get_id
           └── POST - on_post_id
    • Middleware (Middleware are independent):
        → MyMiddleware.process_request
          → OtherMiddleware.process_request

            ↣ MyMiddleware.process_resource
              ↣ OtherMiddleware.process_resource

                  ├── Process route responder

              ↢ OtherMiddleware.process_response
            ↢ CORSMiddleware.process_response
    • Static routes:
        ↦ /tests/ /path/to/tests [/path/to/test/index.html]
        ↦ /falcon/ /path/to/falcon
    • Sinks:
        ⇥ /sink_cls SinkClass
        ⇥ /sink_fn sinkFn
    • Error handlers:
        ⇜ RuntimeError my_runtime_handler

This is the default output of the :meth:`.AppInfo.to_string` method.
A more verbose version can be obtained by passing ``verbose=True``.

The values returned by the inspect functions are class instances that
contain the relevant information collected from the application, to
facilitate programatically use of the collected data.

To support inspection of applications that use a custom router, the
module supplies :func:`.register_router` that registers
an handler function for a particular router class.
The default :class:`.CompiledRouter` inspection is
handled by the :func:`.inspect_compiled_router`
function.

The returned information classes can be explored using a visitor
pattern. To create the string representation of the classes the
:class:`.StringVisitor` visitor is used.
This class is instantiated automatically when calling ``str()``
on an instance or then using the ``to_string()`` method.
Custom visitor can subclass :class:`.InspectVisitor` and
use the :meth:`.InspectVisitor.process` method to visit
the classes.

Inspect module content
----------------------

Inspect Functions
~~~~~~~~~~~~~~~~~

The inspect module defines the following inspect functions

.. autofunction:: falcon.inspect.inspect_app

.. autofunction:: falcon.inspect.inspect_routes

.. autofunction:: falcon.inspect.inspect_middlewares

.. autofunction:: falcon.inspect.inspect_static_routes

.. autofunction:: falcon.inspect.inspect_sinks

.. autofunction:: falcon.inspect.inspect_error_handlers

Router Inspection Functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Functions used to register custom inspect function for custom router implementation,
and the default inspector for the :class:`.CompiledRouter`

.. autofunction:: falcon.inspect.register_router

.. autofunction:: falcon.inspect.inspect_compiled_router

Inspect Information Classes
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Data returned by the the inspect functions

.. autoclass:: falcon.inspect.AppInfo
    :members:

.. autoclass:: falcon.inspect.RouteInfo

.. autoclass:: falcon.inspect.RouteMethodInfo

.. autoclass:: falcon.inspect.MiddlewareInfo

.. autoclass:: falcon.inspect.MiddlewareTreeInfo

.. autoclass:: falcon.inspect.MiddlewareClassInfo

.. autoclass:: falcon.inspect.MiddlewareTreeItemInfo

.. autoclass:: falcon.inspect.MiddlewareMethodInfo

.. autoclass:: falcon.inspect.StaticRouteInfo

.. autoclass:: falcon.inspect.SinkInfo

.. autoclass:: falcon.inspect.ErrorHandlerInfo

Visitors
~~~~~~~~

Classes used to traverse the information classes

.. autoclass:: falcon.inspect.InspectVisitor
    :members:

.. autoclass:: falcon.inspect.StringVisitor
