.. Falcon documentation master file, created by
   sphinx-quickstart on Mon Feb 17 18:21:12 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

The Falcon Web Framework
=================================

Release v\ |version| (:ref:`Installation <install>`)

`Falcon <https://falconframework.org>`__ is a minimalist ASGI/WSGI framework for
building mission-critical REST APIs and microservices, with a focus on
reliability, correctness, and performance at scale.

We like to think of Falcon as the *Dieter Rams* of web frameworks. Falcon
encourages the REST architectural style, and tries to do as little as possible
while remaining highly effective.

.. code:: python

    class QuoteResource:

        def on_get(self, req, resp):
            """Handles GET requests"""
            quote = {
                'quote': (
                    "I've always been more interested in "
                    "the future than in the past."
                ),
                'author': 'Grace Hopper'
            }

            resp.media = quote


    app = falcon.App()
    app.add_route('/quote', QuoteResource())

Quick Links
-----------

* `Read the docs <https://falcon.readthedocs.io/en/stable>`_
  (`FAQ <https://falcon.readthedocs.io/en/stable/user/faq.html>`_ -
  `getting help <https://falcon.readthedocs.io/en/stable/community/help.html>`_ -
  `reference <https://falcon.readthedocs.io/en/stable/api/index.html>`_)
* `Falcon add-ons and complementary packages <https://github.com/falconry/falcon/wiki>`_
* `Falcon articles, talks and podcasts <https://github.com/falconry/falcon/wiki/Articles,-Talks-and-Podcasts>`_
* `falconry/user for Falcon users <https://gitter.im/falconry/user>`_ @ Gitter
* `falconry/dev for Falcon contributors <https://gitter.im/falconry/dev>`_ @ Gitter

What People are Saying
----------------------

"Falcon is rock solid and it's fast."

"We have been using Falcon as a replacement for [another framework] and
we simply love the performance (three times faster) and code base size (easily
half of our [original] code)."

"I'm loving #falconframework! Super clean and simple, I finally
have the speed and flexibility I need!"

"Falcon looks great so far. I hacked together a quick test for a
tiny server of mine and was ~40% faster with only 20 minutes of
work."

"I feel like I'm just talking HTTP at last, with nothing in the
middle. Falcon seems like the requests of backend."

"The source code for Falcon is so good, I almost prefer it to
documentation. It basically can't be wrong."

"What other framework has integrated support for 786 TRY IT NOW ?"

Features
--------

Falcon tries to do as little as possible while remaining highly effective.

- :ref:`ASGI, WSGI <app>`, and :ref:`WebSocket <ws>` support
- Native ``asyncio`` support
- No reliance on magic globals for routing and state management
- Stable interfaces with an emphasis on backwards-compatibility
- Simple API modeling through centralized RESTful :ref:`routing <routing>`
- Highly-optimized, extensible code base
- Easy access to headers and bodies through :ref:`request and response <rr>`
  objects
- DRY request processing via :ref:`middleware <middleware>` components and hooks
- Strict adherence to RFCs
- Idiomatic :ref:`HTTP error <errors>` responses
- Straightforward exception handling
- Snappy :ref:`testing <testing>` with WSGI/ASGI helpers and mocks
- CPython 3.5+ and PyPy 3.5+ support

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
   :maxdepth: 3

   user/index
   deploy/index
   community/index
   api/index
   changes/index
