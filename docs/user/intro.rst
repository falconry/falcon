.. _introduction:

Introduction
============

Falcon is a minimalist, high-performance web framework for building RESTful services and app backends with Python. Falcon works with any WSGI container that is compliant with PEP-3333, and works great with Python 2.6, Python 2.7, Python 3.3, Python 3.4 and PyPy, giving you a wide variety of deployment options.


How is Falcon different?
------------------------

First, Falcon is one of the fastest WSGI frameworks available. When there is a conflict between saving the developer a few keystrokes and saving a few microseconds to serve a request, Falcon is strongly biased toward the latter. That being said, Falcon strives to strike a good balance between usability and speed.

Second, Falcon is lean. It doesn't try to be everything to everyone, focusing instead on a single use case: HTTP APIs. Falcon doesn't include a template engine, form helpers, or an ORM (although those are easy enough to add yourself). When you sit down to write a web service with Falcon, you choose your own adventure in terms of async I/O, serialization, data access, etc. In fact, Falcon only has two dependencies: `six`_, to make it easier to support both Python 2 and 3, and `mimeparse`_ for handling complex Accept headers. Neither of these packages pull in any further dependencies of their own.

Third, Falcon eschews magic. When you use the framework, it's pretty obvious which inputs lead to which outputs. Also, it's blatantly obvious where variables originate. All this makes it easier to reason about the code and to debug edge cases in large-scale deployments of your application.

.. _`six`: http://pythonhosted.org/six/
.. _`mimeparse`: https://code.google.com/p/mimeparse/


About Apache 2.0
----------------

Falcon is released under the terms of the `Apache 2.0 License`_. This means that you can use it in your commercial applications without having to also open-source your own code. It also means that if someone happens to contribute code that is associated with a patent, you are granted a free license to use said patent. That's a pretty sweet deal.

Now, if you do make changes to Falcon itself, please consider contributing your awesome work back to the community.

.. _`Apache 2.0 License`: http://opensource.org/licenses/Apache-2.0


Falcon License
--------------

.. include:: ../../LICENSE