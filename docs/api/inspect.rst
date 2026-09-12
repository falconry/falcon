.. _inspect:

Inspect Module
==============

This module can be used to inspect a Falcon application to obtain information
about its registered routes, middleware objects, static routes, sinks and
error handlers. The entire application can be inspected at once using the
:func:`.inspect_app` function. Additional functions are available for
inspecting specific aspects of the app.

A ``falcon-inspect-app`` CLI script is also available; it uses the inspect
module to print a string representation of an application, as demonstrated
below:

.. code:: bash

    # my_module exposes the application as a variable named "app"
    $ falcon-inspect-app my_module:app

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

The example above shows how ``falcon-inspect-app`` simply outputs the value
returned by the :meth:`.AppInfo.to_string` method. In fact, here is a simple
script that returns the same output as the ``falcon-inspect-app`` command:

.. code:: python

    from falcon import inspect
    from my_module import app

    app_info = inspect.inspect_app(app)

    # Equivalent to print(app_info.to_string())
    print(app_info)

A more verbose description of the app can be obtained by passing
``verbose=True`` to :meth:`.AppInfo.to_string`, while the default
routes added by the framework can be included by passing ``internal=True``. The
``falcon-inspect-app`` command supports the ``--verbose`` and
``--internal`` flags to enable these options.

Using Inspect Functions
-----------------------

The values returned by the inspect functions are class instances that
contain the relevant information collected from the application. These
objects facilitate programmatic use of the collected data.

To support inspection of applications that use a custom router, the
module provides a :func:`.register_router` function to register
a handler function for the custom router class.
Inspection of the default :class:`.CompiledRouter` class is
handled by the :func:`.inspect_compiled_router`
function.

The returned information classes can be explored using the visitor
pattern. To create the string representation of the classes the
:class:`.StringVisitor` visitor is used.
This class is instantiated automatically when calling ``str()``
on an instance or when using the ``to_string()`` method.

Custom visitor implementations can subclass :class:`.InspectVisitor` and
use the :meth:`.InspectVisitor.process` method to visit
the classes.

Inspect Functions Reference
---------------------------

This module defines the following inspect functions.

.. autofunction:: falcon.inspect.inspect_app

.. autofunction:: falcon.inspect.inspect_routes

.. autofunction:: falcon.inspect.inspect_middleware

.. autofunction:: falcon.inspect.inspect_static_routes

.. autofunction:: falcon.inspect.inspect_sinks

.. autofunction:: falcon.inspect.inspect_error_handlers

Router Inspection
-----------------

The following functions enable route inspection.

.. autofunction:: falcon.inspect.register_router

.. autofunction:: falcon.inspect.inspect_compiled_router

Information Classes
-------------------

Information returned by the inspect functions is represented by these classes.

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

Visitor Classes
---------------

The following visitors are used to traverse the information classes.

.. autoclass:: falcon.inspect.InspectVisitor
    :members:

.. autoclass:: falcon.inspect.StringVisitor
