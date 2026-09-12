.. _util:

Utilities
=========

This page describes miscellaneous utilities provided by Falcon.

URI
---

.. automodule:: falcon.uri
    :members: encode, encode_value, encode_check_escaped,
        encode_value_check_escaped, decode, parse_host,
        parse_query_string, unquote_string

Date and Time
-------------

.. NOTE(kgriffs): Use autofunction instead of automodule w/ the falcon
     module, since the latter requires :noindex: which prevents us from
     referencing these docs elsewhere.

.. autofunction:: falcon.http_now
.. autofunction:: falcon.dt_to_http
.. autofunction:: falcon.http_date_to_dt

.. autoclass:: falcon.TimezoneGMT
    :members:

HTTP Status
-----------

.. autofunction:: falcon.http_status_to_code
.. autofunction:: falcon.code_to_http_status

.. _mediatype_util:

Media types
-----------

.. autofunction:: falcon.parse_header
.. autofunction:: falcon.mediatypes.quality
.. autofunction:: falcon.mediatypes.best_match

Async
-----

Aliases
~~~~~~~

Falcon used to provide aliases for the below functions implemented in
:mod:`asyncio`, with fallbacks for older versions of Python:

* ``falcon.get_running_loop()`` → :func:`asyncio.get_running_loop`

* ``falcon.create_task(coro, *, name=None)``  → :func:`asyncio.create_task`

However, as of Falcon 4.0+, these aliases are identical to their :mod:`asyncio`
counterparts on all supported Python versions. (They are only kept for
compatibility purposes.)

Simply use :func:`asyncio.get_running_loop` or :func:`asyncio.create_task`
directly in new code.

Adapters
~~~~~~~~

These functions help traverse the barrier between sync and async code.

.. autofunction:: falcon.sync_to_async
.. autofunction:: falcon.wrap_sync_to_async
.. autofunction:: falcon.wrap_sync_to_async_unsafe
.. autofunction:: falcon.async_to_sync
.. autofunction:: falcon.runs_sync

Other
-----

.. autofunction:: falcon.util.deprecated
.. autofunction:: falcon.util.deprecated_args
.. autofunction:: falcon.to_query_str
.. autofunction:: falcon.get_bound_method
.. autofunction:: falcon.secure_filename
.. autofunction:: falcon.is_python_func

.. autoclass:: falcon.Context
    :members:
    :no-undoc-members:

.. autoclass:: falcon.ETag
    :members:
