Packaging Guide
===============

Normally, the recommended way to :ref:`install Falcon <install>` in your
project is using ``pip`` (or a compatible package manager, such as
``poetry``, ``uv``, and many others) that fetches package archives from
`PyPI`_.

WiP -- explain why in certain scenarios it is desirable to use other packages...

This guide is primarily aimed at packagers that create and maintain Falcon
packages for operating systems such as Linux and BSD distributions, as well as
alternative Python distribution channels such as
`conda-forge <https://anaconda.org/conda-forge/falcon>`__.

.. note::
    Unless noted otherwise in specific sections, this document is only
    applicable to Falcon 4.0.1 or newer.

Obtaining Release
-----------------

In order to package a specific Falcon release, you first need to obtain its
source files.

It is up to you which authoritative source to use.
The most common alternatives are:

* Source distribution (aka "*sdist*") on PyPI.

* GitHub release archive.

* Clone GitHub repository.


Metadata and Dependencies
-------------------------

It is recommend to synchronize the metadata such as the project's description
with recent releases on `PyPI`_.

Falcon has **no hard runtime dependencies** except the standard Python
library. So depending on how Python is packaged in your distribution
(i.e., whether parts of the stdlib are potentially broken out to separate
packages), Falcon should only depend on the basic installation of Python.

.. note::
    Falcon has no third-party dependencies since 2.0, however, we were
    vendoring the ``python-mimeparse`` library (which also had a different
    licence, MIT versus Falcon's Apache 2.0).

    This is no longer a concern as the relevant functionality has been
    reimplemented from scratch in Falcon 4.0, also fixing some long standing
    behavioral quirks and bugs on the way.


Supported Platforms
-------------------

Falcon supports a wide range of platforms -- the pure-Python version should be
able to run anywhere a supported version of Python runs.


Building Binaries
-----------------

The absolute minimum in terms of packaging is not building any binaries, but
just distributing the Python modules found under ``falcon/``. This is roughly
equivalent to our pure-Python wheel on `PyPI`_.

The framework would still function just fine, however, the overall performance
would be somewhat (~30-40%) lower, and potentially much lower (an order of
magnitude) for certain "hot" code paths that feature a dedicated implementation
in Cython.

.. note::
    The above notes on performance only apply to CPython.

    In the unlikely case you are packaging Falcon for PyPy, we recommend simply
    sticking to pure-Python code.

In order to build a binary package, you will obviously need a compiler
toolchain, and the CPython library headers.
Hopefully your distribution already has Python tooling that speaks
`PEP 517 <https://peps.python.org/pep-0517/>`__ -- this is how the framework's
build process is implemented
(using the popular `setuptools <https://setuptools.pypa.io/>`__).

We also use `cibuildwheel`_ to build our packages that are later uploaded to
`PyPI`_, but we realize that its isolated, Docker-centric approach probably
does not lend itself very well to packaging for a distribution of an operating
system.

If your build process does not support installation of build dependencies in
a PEP 517 compatible way, you will also have to install Cython yourself
(version 3.0.8 or newer is recommended to build Falcon).

Big-endian support
^^^^^^^^^^^^^^^^^^
We regularly build and test :ref:`binary wheels <binary_wheels>` on the
IBM Z platform (aka ``s390x``) which is big-endian.
We are not aware of endianness-related issues.

32-bit support
^^^^^^^^^^^^^^
Falcon is not very well tested on 32-bit systems, and we do not provide any
32-bit binary wheels either. We even explicitly fall back to pure-Python code
in some cases such as the multipart form parser (as the smaller ``Py_ssize_t``
would interfere with uploading of files larger than 2 GiB) if we detect a
32-bit flavor of CPython.

If you do opt to provide 32-bit binary Falcon packages, make sure that your run
:ref:`extensive tests <packaging_testing>` against the built package.


Building Documentation
----------------------

It is quite uncommon to also include offline documentation (or to provide a
separate documentation package) as the user can simply browse our documentation
at `Read the Docs <https://falcon.readthedocs.io/>`__. Even if the package does
not contain the latest version of Falcon, it is possible to switch to an
older one using Read the Docs version picker.

If you do decide to ship the offline docs too, you can build it using
``docs/Makefile`` (you can also invoke ``sphinx-build`` directly):

* To build HTML docs, use ``make html``.

  The resulting files will be built in ``docs/_build/html/``.

* To build man pages, use ``make man``.

  The resulting man page file will be called ``docs/_build/man/falcon.1``.

  You will need to rename this file to match your package naming standards, and
  copy it an appropriate man page directory
  (typically under ``/usr/share/man/`` or similar).


.. _packaging_testing:

Testing Package
---------------

WiP...

.. tip::
    You can run ``pytest`` against Falcon's ``tests/`` from any directory,
    i.e., the below should work just fine::

        /usr/local/foo-bin/pytest /bar/baz/falcon-release-dir/tests

    This pattern is regularly exercised in our Continuous Integration gates,
    as ``cibuildwheel`` (see above) does not run tests from the project's
    directory either.


Thank You
---------

WiP...


.. _PyPI: https://pypi.org/project/falcon/
.. _cibuildwheel: https://cibuildwheel.pypa.io/
