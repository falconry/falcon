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


What People are Saying
----------------------

"Falcon looks great so far. I hacked together a quick test for a
tiny server of mine and was ~40% faster with only 20 minutes of
work."

"I feel like I'm just talking HTTP at last, with nothing in the
middle. Falcon seems like the *requests* of backend."

"The source code for falcon is so good, I almost prefer it to
documentation. It basically can't be wrong."

"What other framework has integrated support for '786 TRY IT NOW' ?"


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

Useful Links
------------

- `Falcon Home <http://falconframework.org/>`_
- `Falcon @ PyPI <https://pypi.python.org/pypi/falcon>`_
- `Falcon @ GitHub <https://github.com/racker/falcon>`_

Resources
---------

- `An Unladen Web Framework <http://blog.kgriffs.com/2013/07/02/python-fast-web-service-framework.html>`_
- `The Definitive Introduction to Falcon <https://speakerdeck.com/cabrera/the-definitive-introduction-to-falcon>`_

Documentation
-------------

.. toctree::
   :maxdepth: 2

   community/index
   user/index
   api/index
   changes/index
