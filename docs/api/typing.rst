Typing
======

Type checking support was introduced in version 4.0. While most of the library is
now typed, further type annotations may be added throughout the 4.x release cycle.
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


Known Limitations
-----------------

Falcon's emphasis on flexibility and performance presents certain
challenges when it comes to adding type annotations to the existing code base.

One notable limitation involves using custom :class:`~falcon.Request` and/or
:class:`~falcon.Response` types in callbacks that are passed back
to the framework, such as when adding an
:meth:`error handler <falcon.App.add_error_handler>`.
For instance, the following application might unexpectedly not pass type
checking:

.. code-block:: python

    from typing import Any

    from falcon import App, HTTPInternalServerError, Request, Response


    class MyRequest(Request):
        ...


    def handle_os_error(req: MyRequest, resp: Response, ex: Exception,
                        params: dict[str, Any]) -> None:
        raise HTTPInternalServerError(title='OS error!') from ex


    app = App(request_type=MyRequest)
    app.add_error_handler(OSError, handle_os_error)

(We are working on addressing this limitation at the time of writing --
please see the following GitHub issue for the progress, and possible solutions:
`#2372 <https://github.com/falconry/falcon/issues/2372>`__.)

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
