.. _util:

Utilities
=========

* `URI`_
* `Date and Time`_
* `HTTP Status`_
* `Other`_

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

.. autofunction:: http_now
.. autofunction:: dt_to_http
.. autofunction:: http_date_to_dt

.. autoclass:: falcon.TimezoneGMT
    :members:

HTTP Status
-----------

.. autofunction:: http_status_to_code
.. autofunction:: code_to_http_status
.. autofunction:: get_http_status

Other
-----

.. autofunction:: deprecated
.. autofunction:: to_query_str
.. autofunction:: get_bound_method
.. autofunction:: secure_filename
.. autofunction:: is_python_func

.. autoclass:: falcon.Context
    :members:
    :no-undoc-members:

.. autoclass:: falcon.ETag
    :members:
