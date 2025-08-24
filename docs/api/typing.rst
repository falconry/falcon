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
