.. note::

  The above configuration includes HTTPS with a redirect from HTTP, using
  certificate paths typical of `Let's Encrypt`_. For a plain HTTP-only
  configuration (e.g., during development), you can simplify to a single
  ``server`` block listening on port 80 without the ``ssl_*`` directives.

  For production deployments, use the `Mozilla SSL Configuration Generator`_
  to generate a configuration tuned to your requirements.

.. _`Mozilla SSL Configuration Generator`: https://ssl-config.mozilla.org/#server=nginx
