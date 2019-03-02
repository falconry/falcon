.. _install:

Installation
============

PyPy
----

`PyPy <http://pypy.org/>`__ is the fastest way to run your Falcon app.
Both PyPy2.7 and PyPy3.5 are supported as of PyPy v5.10.

.. code:: bash

    $ pip install falcon

Or, to install the latest beta or release candidate, if any:

.. code:: bash

    $ pip install --pre falcon

CPython
-------

Falcon also fully supports
`CPython <https://www.python.org/downloads/>`__ 2.7, and 3.5+.

A universal wheel is available on PyPI for the the Falcon framework.
Installing it is as simple as:

.. code:: bash

    $ pip install falcon

Installing the Falcon wheel is a great way to get up and running
quickly in a development environment, but for an extra speed boost when
deploying your application in production, Falcon can compile itself with
Cython.

The following commands tell pip to install Cython, and then to invoke
Falcon's ``setup.py``, which will in turn detect the presence of Cython
and then compile (AKA cythonize) the Falcon framework with the system's
default C compiler.

.. code:: bash

    $ pip install cython
    $ pip install --no-binary :all: falcon

If you want to verify that Cython is being invoked, simply
pass `-v` to pip in order to echo the compilation commands:

.. code:: bash

    $ pip install -v --no-binary :all: falcon

**Installing on OS X**

Xcode Command Line Tools are required to compile Cython. Install them
with this command:

.. code:: bash

    $ xcode-select --install

The Clang compiler treats unrecognized command-line options as
errors, for example:

.. code:: bash

    clang: error: unknown argument: '-mno-fused-madd' [-Wunused-command-line-argument-hard-error-in-future]

You might also see warnings about unused functions. You can work around
these issues by setting additional Clang C compiler flags as follows:

.. code:: bash

    $ export CFLAGS="-Qunused-arguments -Wno-unused-function"

Dependencies
------------

Falcon does not require the installation of any other packages, although if
Cython has been installed into the environment, it will be used to optimize
the framework as explained above.

WSGI Server
-----------

Falcon speaks WSGI, and so in order to serve a Falcon app, you will
need a WSGI server. Gunicorn and uWSGI are some of the more popular
ones out there, but anything that can load a WSGI app will do.

All Windows developers can use Waitress production-quality pure-Python WSGI server with very acceptable performance.
Unfortunately Gunicorn is still not working on Windows and uWSGI need to have Cygwin on Windows installed.
Waitress can be good alternative for Windows users if they want quick start using Falcon on it.

.. code:: bash

    $ pip install [gunicorn|uwsgi|waitress]

Source Code
-----------

Falcon `lives on GitHub <https://github.com/falconry/falcon>`_, making the
code easy to browse, download, fork, etc. Pull requests are always welcome! Also,
please remember to star the project if it makes you happy. :)

Once you have cloned the repo or downloaded a tarball from GitHub, you
can install Falcon like this:

.. code:: bash

    $ cd falcon
    $ pip install .

Or, if you want to edit the code, first fork the main repo, clone the fork
to your desktop, and then run the following to install it using symbolic
linking, so that when you change your code, the changes will be automagically
available to your app without having to reinstall the package:

.. code:: bash

    $ cd falcon
    $ pip install -e .

You can manually test changes to the Falcon framework by switching to the
directory of the cloned repo and then running pytest:

.. code:: bash

    $ cd falcon
    $ pip install -r requirements/tests
    $ pytest tests

Or, to run the default set of tests:

.. code:: bash

    $ pip install tox && tox

.. tip::

    See also the `tox.ini <https://github.com/falconry/falcon/blob/master/tox.ini>`_
    file for a full list of available environments.

Finally, to build Falcon's docs from source, simply run:

.. code:: bash

    $ pip install tox && tox -e docs

Once the docs have been built, you can view them by opening the following
index page in your browser. On OS X it's as simple as::

    $ open docs/_build/html/index.html

Or on Linux::

    $ xdg-open docs/_build/html/index.html
