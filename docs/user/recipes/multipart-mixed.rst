.. _nested-multipart-forms:

Parsing Nested Multipart Forms
==============================

Out of the box, Falcon does not offer official support for parsing nested
multipart forms (i.e., where multiple files for a single field are transmitted
using a nested ``multipart/mixed`` part).

.. note::
    Nested multipart forms are considered deprecated according to the
    `living HTML5 standard
    <https://html.spec.whatwg.org/multipage/form-control-infrastructure.html>`_
    and
    `RFC 7578, Section 4.3 <https://tools.ietf.org/html/rfc7578#section-4.3>`_.

If your app needs to handle nested forms, this can be done in the same
fashion as any other part embedded in the form -- by installing an appropriate
media handler.

Let us extend the multipart form parser :attr:`media handlers
<falcon.media.multipart.MultipartParseOptions.media_handlers>` to recursively
parse embedded forms of the ``multipart/mixed`` content type:

.. literalinclude:: ../../../examples/recipes/multipart_mixed_intro.py
    :language: python

.. note::
    Here we create a new parser (with default options) for nested parts,
    effectively disallowing further recursion.

    If traversing into even deeper multipart form hierarchy is desired, we
    can just reuse the same parser.

Let us now use the nesting-aware parser in an app:

.. literalinclude:: ../../../examples/recipes/multipart_mixed_main.py
    :language: python

We should now be able to consume a form containing a nested ``multipart/mixed``
part (the example is adapted from the now-obsolete
`RFC 1867 <https://tools.ietf.org/html/rfc1867>`_)::

    --AaB03x
    Content-Disposition: form-data; name="field1"

    Joe Blow
    --AaB03x
    Content-Disposition: form-data; name="docs"
    Content-Type: multipart/mixed; boundary=BbC04y

    --BbC04y
    Content-Disposition: attachment; filename="file1.txt"

    This is file1.

    --BbC04y
    Content-Disposition: attachment; filename="file2.txt"

    Hello, World!

    --BbC04y--

    --AaB03x--

Note that all line endings in the form above are assumed to be CRLF.

The form should be ``POST``\ed with the ``Content-Type`` header set to
``multipart/form-data; boundary=AaB03x``.
