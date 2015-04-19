.. _install:

Installation
============

Install from PyPI
-----------------

If available, Falcon will compile itself with Cython for an extra
speed boost. The following will make sure Cython is installed first, and
that you always have the latest and greatest.

.. code:: bash

    $ pip install --upgrade cython falcon

Note that if you are running on PyPy, you won't need Cython, so you can just
type:

.. code:: bash

    $ pip install --upgrade falcon

.. note::

    When using Cython, you should always recompile Falcon after
    upgrading Python. To do this, simply run:

    .. code:: bash

        $ pip install --force-reinstall --upgrade cython
        $ pip install --force-reinstall --upgrade falcon

Installing Cython on OS X
-------------------------

In order to get Cython working on OS X Mavericks with Xcode 5.1, you will
first need to set up Xcode Command Line Tools. Install them with
this command:

.. code:: bash

    $ xcode-select --install

The Xcode 5.1 CLang compiler treats unrecognized command-line options as
errors; this can cause problems under Python 2.6, for example:

.. code:: bash

    clang: error: unknown argument: '-mno-fused-madd' [-Wunused-command-line-argument-hard-error-in-future]

You can work around errors caused by unused arguments by setting some
environment variables:

.. code:: bash

    $ export CFLAGS=-Qunused-arguments
    $ export CPPFLAGS=-Qunused-arguments
    $ pip install cython falcon


WSGI Server
-----------

Falcon speaks WSGI. If you want to actually serve a Falcon app, you will
want a good WSGI server. Gunicorn and uWSGI are some of the more popular
ones out there, but anything that can load a WSGI app will do. Gevent is
an async library that works well with both Gunicorn and uWSGI.

.. code:: bash

    $ pip install --upgrade gevent [gunicorn|uwsgi]


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
