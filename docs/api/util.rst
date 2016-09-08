.. _util:

Utilities
=========

URI Functions
-------------

.. NOTE(kgriffs): Due to the way we have been hoisting uri into falcon,
.. sphinx can't import just falcon.uri (root cause TBD). Whether or not
.. the way we are hoisting things is legit (hint: probably not, this
.. is something to address in Falcon 2.0), sphinx can't handle it
.. by default so we have a custom extension to fix things up.

.. automodule:: falcon.uri
    :members: encode, encode_value, decode, parse_host,
        parse_query_string, unquote_string

Miscellaneous
-------------

.. automodule:: falcon
    :members: deprecated, http_now, dt_to_http, http_date_to_dt,
        to_query_str, get_http_status, get_bound_method

.. autoclass:: falcon.TimezoneGMT
    :members:
