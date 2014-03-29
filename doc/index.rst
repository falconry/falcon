.. Falcon documentation master file, created by
   sphinx-quickstart on Mon Feb 17 18:21:12 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Falcon: The Unladen WSGI Framework
==================================

Release v\ |version|. (:ref:`Installation <install>`)

Falcon is a minimalist WSGI library for building fast web APIs and app backends.

When it comes to building HTTP APIs, other frameworks weigh you down with tons of dependencies and unnecessary abstractions. Falcon cuts to the chase with a clean design that embraces HTTP. We like to think of Falcon as the Dieter Rams of web frameworks; functional, simple, and elegant.

.. code:: python

    class CatalogItem(object):

        # ...

        @falcon.before(hooks.to_oid)
        def on_get(self, id):
            return self._collection.find_one(id)

    app = falcon.API(after=[hooks.serialize])
    app.add_route('/items/{id}', CatalogItem())


Testimonials
------------

**S. Magrí**
    I feel like I'm just talking HTTP at last... with nothing in the
    middle... Falcon seems like the 'requests' of backend.

**K. Conway**
    Needed to roll a REST API in a hurry for a project. Falcon proved
    fast and effective.

**jlegler**
    The source code for falcon is so good, I almost prefer it to
    documentation. It basically can't be wrong.


Features
--------

Falcon tries to do as little as possible while remaining highly effective.

- Routes based on URI templates RFC
- REST-inspired mapping of URIs to resources
- Global, resource, and method hooks
- Idiomatic HTTP error responses
- Full Unicode support
- Intuitive request and response objects
- Works great with async libraries like gevent
- Minimal attack surface for writing secure APIs
- 100% code coverage with a comprehensive test suite
- Only depends on six and mimeparse
- Python 2.6, 2.7, 3.3 + PyPy


User Guide
----------

.. toctree::
   :maxdepth: 2

   user/intro
   user/install
   user/quickstart
   user/tutorial


Community Guide
-----------------

*Coming soon*


API Documentation
-----------------

.. toctree::
   :maxdepth: 2

   api/api
   api/hooks
   api/request_and_response
   api/status_and_errors
   api/util

Contributor Guide
-----------------

*Coming soon*
