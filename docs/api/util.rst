.. _util:

Utilities
=========

.. contents:: :local:

URI
---

.. automodule:: falcon.uri
    :members: encode, encode_value, decode, parse_host,
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
.. autofunction:: falcon.get_http_status

Async
-----
.. autofunction:: falcon.get_loop
.. autofunction:: falcon.sync_to_async
.. autofunction:: falcon.wrap_sync_to_async
.. autofunction:: falcon.wrap_sync_to_async_unsafe
.. autofunction:: falcon.invoke_coroutine_sync
.. autofunction:: falcon.runs_sync

Other
-----

.. autofunction:: falcon.deprecated
.. autofunction:: falcon.to_query_str
.. autofunction:: falcon.get_bound_method
.. autofunction:: falcon.secure_filename
.. autofunction:: falcon.is_python_func

.. autoclass:: falcon.Context
    :members:
    :no-undoc-members:

.. autoclass:: falcon.ETag
    :members:
