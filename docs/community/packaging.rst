Packaging Guide
===============

Normally, the recommended way to :ref:`install Falcon <install>` into your
project is using ``pip`` (or a compatible package/project manager, such as
``poetry``, ``uv``, and many others) that fetches package archives from
`PyPI`_.

However, the `PyPI`_-based way of installation is not always applicable or
optimal. For instance, when the system package manager of a Linux distribution
is used to install Python-based software, it normally gets the dependencies
from the same distribution channel, as the specific versions of the packages
were carefully tested to work well together on the operating system in
question.

This guide is primarily aimed at engineers who create and maintain Falcon
packages for operating systems such as Linux and BSD distributions, as well as
alternative Python distribution channels such as
`conda-forge <https://anaconda.org/conda-forge/falcon>`__.

.. note::
    Unless noted otherwise in specific sections, this document is only
    applicable to Falcon 4.0.1 or newer.

If you run into any packaging issues, questions that this guide does not cover,
or just find a bug in Falcon, please :ref:`let us know <packaging_thank_you>`!


Obtaining Release
-----------------

In order to package a specific Falcon release, you first need to obtain its
source archive.

.. tip::
    Maintaining older versions of Falcon packages?
    See what we support on our side: :ref:`supported_releases`.

It is up to you which authoritative source to use.
The most common alternatives are:

* **Source distribution** (aka "*sdist*") on `PyPI`_.

  If you are unsure, the recommended way is to use our source distribution from
  `PyPI`_ (also available on GitHub releases, see below).

  You can query PyPA Warehouse's
  `JSON API <https://warehouse.pypa.io/api-reference/json.html>`__ in order to
  obtain the latest stable version of Falcon, fetch the *sdist* URL, and more.

  The API URL specifically for Falcon is https://pypi.org/pypi/falcon/json.
  Here is how you can query it using the popular ``requests``:

  >>> import requests
  >>> resp = requests.get('https://pypi.org/pypi/falcon/json')
  >>> for url in resp.json()['urls']:
  ...     if url['packagetype'] == 'sdist':
  ...         print(f'Latest Falcon sdist: {url["url"]}')
  ...
  Latest Falcon sdist: https://files.pythonhosted.org/<...>/falcon-4.0.2.tar.gz

  (``4.0.2`` was the latest version at the time of this writing.)

* **GitHub release archive**.

  Alternatively, you can download the archive from our
  `Releases on GitHub <https://github.com/falconry/falcon/releases>`__.
  GitHub automatically archives the whole repository for every release, and
  attaches the tarball to the release page. In addition, our release automation
  also uploads the *sdist* (see above) to the release as well.

* **Clone GitHub repository**.

  If your packaging workflow is based on a Git repository that tracks both the
  framework's source code, and your patches or tooling scripts, you will
  probably want to clone our
  `GitHGub repository <https://github.com/falconry/falcon/>`__ instead.

  Every release has a corresponding annotated Git tag that shares the name
  with the package version on PyPI, e.g., ``4.0.2``.


Semantic Versioning
-------------------

Falcon strictly adheres to :ref:`SemVer <semver>` -- incompatible API changes
are only introduced in conjunction with a major version increment.

When updating your Falcon package, you should always carefully review
:doc:`the changelog </changes/index>` for the new release that you targeting,
especially if you are moving up to a new SemVer major version.
(In that case, the release notes will include a **"Breaking Changes"**
section.)

For a packager, another section worth checking is called
**"Changes to Supported Platforms"**, where we announce support for new Python
interpreter versions (or even new implementations), as well as deprecate or
remove the old ones.

.. attention::
    The SemVer guarantees primarily cover the publicly documented API from the
    framework user's perspective, so even a minor release may contain important
    changes to the build process, tests, and project tooling.


Metadata and Dependencies
-------------------------

It is recommend to synchronize the metadata such as the project's description
with recent releases on `PyPI`_.

Falcon has **no hard runtime dependencies** except the standard Python
library. So depending on how Python is packaged in your distribution
(i.e., whether parts of the stdlib are potentially broken out to separate
packages), Falcon should only depend on the basic installation of the targeted
Python interpreter.

.. note::
    Falcon has no third-party dependencies since 2.0, however, we were
    vendoring the ``python-mimeparse`` library (which also had a different
    licence, MIT versus Falcon's Apache 2.0).

    This is no longer a concern as the relevant functionality has been
    reimplemented from scratch in Falcon 4.0.0, also fixing some long standing
    behavioral quirks and bugs on the way.
    As a result, the Falcon 4.x series currently has no vendored dependencies.

Optional dependencies
^^^^^^^^^^^^^^^^^^^^^
Falcon has no official list of optional dependencies, but if you want to
provide "suggested packages" or similar, various media (de-) serialization
libraries can make good candidates, especially those that have official media
handlers such as ``msgpack`` (:class:`~falcon.media.MessagePackHandler`).
:class:`~falcon.media.JSONHandler` can be easily customized using faster JSON
implementations such as ``orjson``, ``rapidjson``, etc, so you can suggest
those that are already packaged for your distribution.

Otherwise, various ASGI and WSGI application servers could also fit the bill.

See also :ref:`packaging_test_deps` for the list of third party libraries that
we test against in our Continuous Integration (CI) tests.


Building Binaries
-----------------

The absolute minimum in terms of packaging is not building any binaries, but
just distributing the Python modules found under ``falcon/``. This is roughly
equivalent to our pure-Python wheel on `PyPI`_.

.. tip::
    The easiest way to skip the binaries is to set the
    ``FALCON_DISABLE_CYTHON`` environment variable to a non-empty value in the
    build environment.

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
We are not aware of any endianness-related issues.

32-bit support
^^^^^^^^^^^^^^
Falcon is not very well tested on 32-bit systems, and we do not provide any
32-bit binary wheels either. We even explicitly fall back to pure-Python code
in some cases such as the multipart form parser (as the smaller ``Py_ssize_t``
would interfere with uploading of files larger than 2 GiB) if we detect a
32-bit flavor of CPython.

If you do opt to provide 32-bit Falcon binaries, make sure that you run
:ref:`extensive tests <packaging_testing>` against the built package.


Building Documentation
----------------------

It is quite uncommon to also include offline documentation (or to provide a
separate documentation package) as the user can simply browse our documentation
at `Read the Docs <https://falcon.readthedocs.io/>`__. Even if the package does
not contain the latest version of Falcon, it is possible to switch to an
older one using Read the Docs version picker.

If you do decide to ship the offline docs too, you can build it using
``docs/Makefile`` (you can also invoke ``sphinx-build`` directly).

.. note::
    Building the HTML documentation requires the packages listed in
    ``requirements/docs``.

    Building ``man`` pages requires only Sphinx itself and the plugins
    referenced directly in ``docs/conf.py``
    (currently ``myst-parser``, ``sphinx-copybutton``, and ``sphinx-design``).

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

When your Falcon package is ready, it is a common (highly recommended!)
practice to install it into your distribution, and run tests verifying that the
package functions as intended.

As of Falcon 4.0+, the only hard test dependency is ``pytest``.

You can simply run it against Falcon's test suite found in the ``tests/``
subdirectory::

  pytest tests/

These tests will provide decent (98-99%), although not complete, code coverage,
and should ensure that the basic wiring of your package is correct
(however, see also the next chapter: :ref:`packaging_test_deps`).

.. tip::
    You can run ``pytest`` from any directory, i.e., the below should work just
    fine::

        /usr/local/foo-bin/pytest /bar/baz/falcon-release-dir/tests/

    This pattern is regularly exercised in our CI gates, as `cibuildwheel`_
    (see above) does not run tests from the project's directory either.

.. _packaging_test_deps:

Optional test dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^
As mentioned above, Falcon has no hard test dependencies except ``pytest``,
however, our test suite includes optional integration tests against a selection
of third-party libraries.

When building :ref:`wheels <binary_wheels>` with `cibuildwheel`_, we install a
small subset of the basic optional test dependencies, see the
``requirements/cibwtest`` file in the repository.
Furthermore, when running our full test suite in the CI, we exercise
integration with a larger number of optional libraries and applications servers
(see the ``requirements/tests`` file, as well as various ASGI/WSGI server
integration test definitions in ``tox.ini``).

Ideally, if your distribution also provides packages for any of the above
optional test dependencies, it may be a good idea to install them into your
test environment as well. This will help verifying that your Falcon package is
compatible with the specific versions of these packages in your distribution.


.. _packaging_thank_you:

Thank You
---------

If you are already maintaining Falcon packages, thank you!

Although we do not have the bandwidth to maintain Falcon packages for any
distribution channel beyond `PyPI`_ ourselves, we are happy to help if you run
into any problems. File an
`issue on GitHub <https://github.com/falconry/falcon/issues>`__,
or just :ref:`send us a message <chat>`!


.. _PyPI: https://pypi.org/project/falcon/
.. _cibuildwheel: https://cibuildwheel.pypa.io/
