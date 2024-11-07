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


Obtaining Release
-----------------

In order to package a specific Falcon release, you first need to obtain its
source files.

It is up to you which authoritative source to use.
The most common alternatives are:

* Source distribution (aka "*sdist*") on PyPI.

* GitHub release archive.

* Clone GitHub repository.


Building Binaries
-----------------

WiP...


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
  You can check it manually using ``man``::

      man docs/_build/man/falcon.1

  You will need to rename this file to match your package naming standards, and
  copy it an appropriate man page directory
  (typically under ``/usr/share/man/`` or similar).


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
