.. _introduction:

Introduction
============

Falcon is a minimalist, high-performance web framework for building web services and app backends with Python. It's WSGI-based, and works great with Python 2.6, Python 2.7, Python 3.3, and PyPy, giving you a wide variety of deployment options.


Yet Another Framework
---------------------

Using something that already exists is obviously ideal. However, sometimes the wheel needs to be reinvented, and this was one of those times. Falcon was created because there were no frameworks that addressed all three of the following issues:

- Python web frameworks often perform rather poorly under load. At high concurrency, using async IO, API servers can become CPU-bound. When that happens, every microsecond counts.
- Most web frameworks come with a lot of HTML-centric tooling that is fantastic if you are developing a web app, but quite useless for building an API. In that case, all they do is waste RAM, increase your chance of a security exploit, and generally make a nuisance of themselves.
- Many frameworks try too hard, in our opinion, to abstract away what's going on under the hood, making it difficult to reason about the river of HTTP flowing in and out of your API. Magic is wonderful at development time, but a nightmare when it comes time to debug a hairy production issue.


How is Falcon different?
------------------------

First, Falcon is one of the fastest WSGI frameworks on the planet, and we are always trying to make it perform even better. When there is a conflict between saving the developer a few keystrokes and saving a few microseconds to serve a request, Falcon is strongly biased toward the latter. Falcon strives to strike a good balance between usability and close-to-the-metal speed.

Second, Falcon is lean. It doesn't try to be everything to everyone, focusing instead on a single use case: HTTP APIs. Falcon doesn't include a template engine, form helpers, or an ORM (although those are easy enough to add yourself). When you sit down to write a web service with Falcon, you choose your own adventure in terms of async I/O, serialization, data access, etc. In fact, the only dependencies Falcon takes is on six, to make it easier to support both Python 2 and 3, and on mimeparse for handling complex Accept headers.

Third, Falcon eschews magic. When you use the framework, it's pretty obvious which inputs lead to which outputs. Also, it's blatantly obvious where variables originate. All this makes it easier for you and your posterity to reason about your code, even months (or years) after you wrote it.


About Apache 2.0
----------------

Falcon is released under the terms of the `Apache 2.0 License`_. This means you can use it in your commercial applications without having to also open-source your own code. It also means that if someone happens to contribute code that is associated with a patent, you are granted a free license to use said patent. That's a pretty sweet deal.

Now, if you do make changes to Falcon itself, please consider contributing your awesome work back to the community.

.. _`Apache 2.0 License`: http://opensource.org/licenses/Apache-2.0


Falcon License
--------------

    .. include:: ../../LICENSE