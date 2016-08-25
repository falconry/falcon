.. _install:

Installation
============

PyPy
----

`PyPy <http://pypy.org/>`__ is the fastest way to run your Falcon app.
However, note that only the PyPy 2.7 compatible release is currently
supported.

.. code:: bash

    $ pip install falcon

CPython
-------

Falcon also fully supports
`CPython <https://www.python.org/downloads/>`__ 2.6-3.5.

A universal wheel is available on PyPI for the the Falcon framework.
Installing it is as simple as:

.. code:: bash

    $ pip install falcon

Installing the wheel is a great way to get up and running with Falcon
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

**Installing on OS X**

Xcode Command Line Tools are required to compile Cython. Install them
with this command:

.. code:: bash

    $ xcode-select --install

The Clang compiler treats unrecognized command-line options as
errors; this can cause problems under Python 2.6, for example:

.. code:: bash

    clang: error: unknown argument: '-mno-fused-madd' [-Wunused-command-line-argument-hard-error-in-future]

You might also see warnings about unused functions. You can work around
these issues by setting additional Clang C compiler flags as follows:

.. code:: bash

    $ export CFLAGS="-Qunused-arguments -Wno-unused-function"


WSGI Server
-----------

Falcon speaks WSGI. If you want to actually serve a Falcon app, you will
want a good WSGI server. Gunicorn and uWSGI are some of the more popular
ones out there, but anything that can load a WSGI app will do. Gevent is
an async library that works well with both Gunicorn and uWSGI.

.. code:: bash

    $ pip install gevent [gunicorn|uwsgi]


Source Code
-----------

Falcon `lives on GitHub <https://github.com/racker/falcon>`_, making the
code easy to browse, download, fork, etc. Pull requests are always welcome! Also,
please remember to star the project if it makes you happy.

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

Did we mention we love pull requests? :)
