Typing
======

Type checking support was introduced in Falcon :doc:`4.0 </changes/4.0.0>`.
While most of the library is now typed, further type annotations may be added
throughout the 4.x release cycle.
To improve them, we may introduce changes to the typing that do not affect
runtime behavior, but may surface new or different errors with type checkers.

.. role:: python(code)
    :language: python

.. note::
    All undocumented type aliases coming from ``falcon._typing`` are considered
    private to the framework itself, and not meant for annotating applications
    using Falcon. To that end, it is advisable to only use classes from the
    public interface, and public aliases from :mod:`falcon.typing`, e.g.:

    .. code-block:: python

        class MyResource:
            def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
                resp.media = {'message': 'Hello, World!'}

    If you still decide to reuse the private aliases anyway, they should
    preferably be imported inside :python:`if TYPE_CHECKING:` blocks in order
    to avoid possible runtime errors after an update.
    Also, make sure to :ref:`let us know <chat>` which essential aliases are
    missing from the public interface!


.. _generic_app_types:

App Types
---------

Falcon's :class:`~falcon.App` (and :class:`asgi.App <falcon.asgi.App>`) is a
:class:`generic type <typing.Generic>` parametrized by its request and response
types. Consequently, static type checkers (such as Mypy or Pyright) can
correctly infer the specialized :class:`~falcon.App` type from the
`request_type` and/or `response_type` arguments supplied to the initializer.

The use of generics should in most cases require no explicit effort on your
side. However, if you annotate your variables or return types as
``falcon.App``, the type checker may require you to provide the explicit type
parameters when running in the strict mode (Mypy calls the option
``--disallow-any-generics``, also part of the ``--strict`` mode flag).

For instance, the following mini-application will not pass type checking with
Mypy in the ``--strict`` mode:

.. code-block:: python

    import falcon


    class HelloResource:
        def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
            resp.media = {'message': 'Hello, typing!'}


    def create_app() -> falcon.App:
        app = falcon.App()
        app.add_route('/', HelloResource())
        return app

In order to address this ``type-arg`` issue, we could explicitly specify which
variant of ``App`` our ``create_app()`` is expected to instantiate:

.. code-block:: python

    import falcon


    class HelloResource:
        def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
            resp.media = {'message': 'Hello, typing!'}


    def create_app() -> falcon.App[falcon.Request, falcon.Response]:
        app = falcon.App()
        app.add_route('/', HelloResource())
        return app

Alternatively, we could ask ourselves what the purpose of ``create_app()`` is.
If we want to instantiate a WSGI application suitable for a PEP-3333 compliant
app server, we could type it accordingly:

.. code-block:: python

    import wsgiref.simple_server
    import wsgiref.types

    import falcon


    class HelloResource:
        def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
            resp.media = {'message': 'Hello, typing!'}


    def create_app() -> wsgiref.types.WSGIApplication:
        app = falcon.App()
        app.add_route('/', HelloResource())
        return app


    if __name__ == '__main__':
        with wsgiref.simple_server.make_server('', 8000, create_app()) as httpd:
            httpd.serve_forever()

Both alternatives should now pass type checking in the ``--strict`` mode.

.. attention::
    For illustration purposes, we also included a
    :mod:`wsgiref.simple_server`-based server in the second revised example,
    allowing you to run the file directly with Python 3.11+.
    However, for a real deployment you should always :ref:`install <install>` a
    production-ready WSGI or ASGI server.

.. versionchanged:: 4.2
    :class:`falcon.App` and :class:`falcon.asgi.App` are now annotated as
    :class:`generic types <typing.Generic>` parametrized by the request and
    response classes.


Known Limitations
-----------------

Falcon's emphasis on flexibility and performance presents certain
challenges when it comes to adding type annotations to the existing code base.

One notable limitation involves using custom :class:`~falcon.Request` and/or
:class:`~falcon.Response` types together with a custom
:attr:`context type <falcon.Request.context_type>`:

.. code-block:: python

    from falcon import Request


    class MyRichContext:
        """My fancy context type with well annotated attributes."""

        ...


    class MyRequest(Request):
        context_type = MyRichContext

Although a code base employing the above pattern may pass type checking without
any warnings even under ``--strict`` settings, the problem here is that
:attr:`MyRequest.context <falcon.Request.context>` is still annotated as
:class:`~falcon.Context`, allowing arbitrary attribute access.
As a result, this would mask any potential typing issues in the use of
``MyRichContext``.

If you make extensive use of a custom context type, and do want to perform type
checking against its interface, you can explicitly redefine `context` as
having the desired type. In order to convince the type checker, this will
require at least one strategically placed ``# type: ignore``:

.. code-block:: python

    from falcon import Request


    class MyRichContext:
        """My fancy context type with well annotated attributes."""

        ...


    class MyRequest(Request):
        context_type = MyRichContext

        context: MyRichContext  # type: ignore[assignment]

Our efforts to work around this issue have so far hit the wall of
`PEP 526 <https://peps.python.org/pep-0526/#class-and-instance-variable-annotations>`__,
which states that a :any:`ClassVar <typing.ClassVar>` parameter cannot include
any type variables, regardless of the level of nesting.

If you come up with an elegant solution to this problem,
:ref:`let us know <chat>`!

Another known inconsistency is the typing of the
:class:`converter interface <falcon.routing.BaseConverter>`, where certain
subclasses (such as :class:`~falcon.routing.PathConverter`) declare a different
input type than the base ``convert()`` method.
(See also the discussions and possible solutions on the GitHub issue
`#2396 <https://github.com/falconry/falcon/issues/2396>`__.)

.. important::
    The above issues are only typing limitations that have no effect outside of
    type checking -- applications will work just fine at runtime!


Public Type Aliases
-------------------

.. automodule:: falcon.typing
    :members:
