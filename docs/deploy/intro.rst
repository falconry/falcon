.. _intro:

.. _WSGI protocol: https://www.python.org/dev/peps/pep-0333/
.. _ASGI protocol: https://asgi.readthedocs.io/en/latest/specs/main.html


Preamble & Disclaimer
=====================

Falcon supports both the standard `WSGI protocol`_ that most Python web
applications have been using since 2003, and the newer `ASGI protocol`_ for
asynchronous applications (including WebSockets).

If you have deployed synchronous Python applications like Django or Flask, you
will find yourself quite at home with Falcon's WSGI stack, and servers such as
Gunicorn, uWSGI, Waitress, or Apache/mod_wsgi should suffice. For
:class:`async Falcon apps <falcon.asgi.App>`, use an ASGI server such as
Uvicorn, Daphne, or Hypercorn (often behind the same reverse proxies you
already know).

There are many ways to deploy a Python application. The aim of these quickstarts
is to simply get you up and running, not to give you a perfectly tuned or secure
environment. You will almost certainly need to customize these configurations
for any serious production deployment.
