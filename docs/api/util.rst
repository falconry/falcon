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

.. automodule:: falcon
    :noindex:
    :members: http_now, dt_to_http, http_date_to_dt

.. autoclass:: falcon.TimezoneGMT
    :members:

HTTP Status
-----------

.. automodule:: falcon
    :noindex:
    :members: get_http_status, http_status_to_code, code_to_http_status

Other
-----

.. automodule:: falcon
    :noindex:
    :members: deprecated, to_query_str,
        get_bound_method, secure_filename, is_python_func

.. autoclass:: falcon.Context
    :members:
    :no-undoc-members:

.. autoclass:: falcon.ETag
    :members:
