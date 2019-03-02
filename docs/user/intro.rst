.. _introduction:

Introduction
============

    Perfection is finally attained not when there is no longer anything
    to add, but when there is no longer anything to take away.

    *- Antoine de Saint-Exupéry*

`Falcon <https://falconframework.org>`__ is a reliable,
high-performance Python web framework for building
large-scale app backends and microservices. It encourages the REST
architectural style, and tries to do as little as possible while
remaining highly effective.

Falcon apps work with any WSGI server, and run like a champ under
CPython 2.7/3.5+ and PyPy.

How is Falcon different?
------------------------

We designed Falcon to support the demanding needs of large-scale
microservices and responsive app backends. Falcon complements more
general Python web frameworks by providing bare-metal performance,
reliability, and flexibility wherever you need it.

**Fast.** Same hardware, more requests. Falcon turns around
requests several times faster than most other Python frameworks. For
an extra speed boost, Falcon compiles itself with Cython when
available, and also works well with `PyPy <https://pypy.org>`__.
Considering a move to another programming language? Benchmark with
Falcon + PyPy first.

**Reliable.** We go to great lengths to avoid introducing
breaking changes, and when we do they are fully documented and only
introduced (in the spirit of
`SemVer <http://semver.org/>`__) with a major version
increment. The code is rigorously tested with numerous inputs and we
require 100% coverage at all times. Falcon does not depend on any
external Python packages.

**Flexible.** Falcon leaves a lot of decisions and implementation
details to you, the API developer. This gives you a lot of freedom to
customize and tune your implementation. Due to Falcon's minimalist
design, Python community members are free to independently innovate on
`Falcon add-ons and complementary packages <https://github.com/falconry/falcon/wiki>`__.

**Debuggable.** Falcon eschews magic. It's easy to tell which inputs
lead to which outputs. Unhandled exceptions are never encapsulated or
masked. Potentially surprising behaviors, such as automatic request body
parsing, are well-documented and disabled by default. Finally, when it
comes to the framework itself, we take care to keep logic paths simple
and understandable. All this makes it easier to reason about the code
and to debug edge cases in large-scale deployments.

Features
--------

- Highly-optimized, extensible code base
- Intuitive routing via URI templates and REST-inspired resource
  classes
- Easy access to headers and bodies through request and response
  classes
- DRY request processing via middleware components and hooks
- Idiomatic HTTP error responses
- Straightforward exception handling
- Snappy unit testing through WSGI helpers and mocks
- Supports Python 2.7, 3.5+
- Compatible with PyPy

About Apache 2.0
----------------

Falcon is released under the terms of the `Apache 2.0 License`_. This means that you can use it in your commercial applications without having to also open-source your own code. It also means that if someone happens to contribute code that is associated with a patent, you are granted a free license to use said patent. That's a pretty sweet deal.

Now, if you do make changes to Falcon itself, please consider contributing your awesome work back to the community.

.. _`Apache 2.0 License`: http://opensource.org/licenses/Apache-2.0


Falcon License
--------------

.. include:: ../../LICENSE
