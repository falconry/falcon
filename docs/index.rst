.. Falcon documentation master file, created by
   sphinx-quickstart on Mon Feb 17 18:21:12 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

The Falcon Web Framework
=================================

Release v\ |version| (:ref:`Installation <install>`)

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

"Falcon is rock solid and it's fast."

"I'm loving #falconframework! Super clean and simple, I finally
have the speed and flexibility I need!"

"I feel like I'm just talking HTTP at last, with nothing in the
middle. Falcon seems like the requests of backend."

"The source code for falcon is so good, I almost prefer it to
documentation. It basically can't be wrong."

"What other framework has integrated support for 786 TRY IT NOW ?"

Quick Links
-----------

* `Read the docs <https://falcon.readthedocs.io/en/stable>`_
* `Falcon add-ons and complementary packages <https://github.com/falconry/falcon/wiki>`_
* `Falcon talks, podcasts, and blog posts <https://github.com/falconry/falcon/wiki/Talks-and-Podcasts>`_
* `falconry/user for Falcon users <https://gitter.im/falconry/user>`_ @ Gitter
* `falconry/dev for Falcon contributors <https://gitter.im/falconry/dev>`_ @ Gitter

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
- Supports Python 2.7, 3.4+
- Compatible with PyPy

Who's Using Falcon?
-------------------

Falcon is used around the world by a growing number of organizations,
including:

- 7ideas
- Cronitor
- EMC
- Hurricane Electric
- Leadpages
- OpenStack
- Rackspace
- Shiftgig
- tempfil.es
- Opera Software

If you are using the Falcon framework for a community or commercial
project, please consider adding your information to our wiki under
`Who's Using Falcon? <https://github.com/falconry/falcon/wiki/Who's-using-Falcon%3F>`_

You might also like to view our
`Add-on Catalog <https://github.com/falconry/falcon/wiki/Add-on-Catalog>`_,
where you can find a list of add-ons maintained by the community.

Documentation
-------------

.. toctree::
   :maxdepth: 2

   user/index
   api/index
   community/index
   changes/index
