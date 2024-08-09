.. _capitalizing_response_headers:

Capitalizing Response Header Names
==================================

Falcon always renders WSGI response header names in lower case; see
also: :ref:`faq_header_names_lowercase`

While this should normally never be an issue for standards-conformant HTTP
clients, it is possible to override HTTP headers using
`generic WSGI middleware
<https://www.python.org/dev/peps/pep-3333/#middleware-components-that-play-both-sides>`_:

.. literalinclude:: ../../../examples/recipes/header_name_case_mw.py
    :language: python

We can now use this middleware to wrap a Falcon app:

.. literalinclude:: ../../../examples/recipes/header_name_case_app.py
    :language: python

As a bonus, this recipe applies to non-Falcon WSGI applications too.
