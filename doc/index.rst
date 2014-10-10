.. Falcon documentation master file, created by
   sphinx-quickstart on Mon Feb 17 18:21:12 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

The Falcon Web Framework
=================================

Release v\ |version|. (:ref:`Installation <install>`)

.. note::

  This documentation targets the upcoming 0.2.0 release of Falcon,
  currently in beta and available on PyPI.

Falcon is a minimalist WSGI library for building speedy web APIs and app
backends. We like to think of Falcon as the `Dieter Rams` of web frameworks.

When it comes to building HTTP APIs, other frameworks weigh you down with tons
of dependencies and unnecessary abstractions. Falcon cuts to the chase with a
clean design that embraces HTTP and the REST architectural style.

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

.. Who's using Falcon?

   TODO: When we confirm enough of these, publish the list.

   Confirmed: IBM, Red Hat, Rackspace
   Unconfirmed: AT&T, Marchex

**S. Magrí**
    I feel like I'm just talking HTTP at last, with nothing in the
    middle. Falcon seems like the *requests* of backend.

**J. Legler**
    The source code for falcon is so good, I almost prefer it to
    documentation. It basically can't be wrong.

**K. Conway**
    What other framework has integrated support for "786 TRY IT NOW"?


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
- Python 2.6, 2.7, 3.3, 3.4 + PyPy


Resources
---------

- `The Definitive Introduction to Falcon <https://speakerdeck.com/cabrera/the-definitive-introduction-to-falcon>`_
- `An Unladen Web Framework <http://blog.kgriffs.com/2013/07/02/python-fast-web-service-framework.html>`_
- `Falcon WSGI Framework: 0.1.8 Highlights <http://blog.kgriffs.com/2014/02/04/falcon-wsgi-framework-highlights-0.1.8.html>`_


Community Guide
---------------

.. toctree::
   :maxdepth: 1

   community/help
   community/contribute
   community/faq


User Guide
----------

.. toctree::
   :maxdepth: 2

   user/intro
   user/install
   user/quickstart
   user/tutorial


Classes and Functions
---------------------

.. toctree::
   :maxdepth: 2

   api/api
   api/request_and_response
   api/status
   api/errors
   api/hooks
   api/util

