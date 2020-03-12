.. _redirects:

Redirection
===========

Falcon defines a set of exceptions that can be raised within a
middleware method, hook, or responder in order to trigger
a 3xx (Redirection) response to the client. Raising one of these
classes short-circuits request processing in a manner similar to
raising an instance or subclass of :py:class:`~.HTTPError`.

.. autoexception:: falcon.HTTPMovedPermanently

.. autoexception:: falcon.HTTPFound

.. autoexception:: falcon.HTTPSeeOther

.. autoexception:: falcon.HTTPTemporaryRedirect

.. autoexception:: falcon.HTTPPermanentRedirect
