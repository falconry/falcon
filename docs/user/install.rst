.. _install:

Installation
============

PyPy
----

`PyPy <http://pypy.org/>`__ is the fastest way to run your Falcon app.
PyPy3.5+ is supported as of PyPy v5.10.

.. code:: bash

    $ pip install falcon

Or, to install the latest beta or release candidate, if any:

.. code:: bash

    $ pip install --pre falcon

CPython
-------

Falcon fully supports
`CPython <https://www.python.org/downloads/>`__ 3.5+.

The latest stable version of Falcon can be installed directly from PyPI:

.. code:: bash

    $ pip install falcon

Or, to install the latest beta or release candidate, if any:

.. code:: bash

    $ pip install --pre falcon

In order to provide an extra speed boost, Falcon can compile itself with
Cython. Wheels containing pre-compiled binaries are available from PyPI for
several common platforms. However, if a wheel for your platform of choice is not
available, you can choose to stick with the source distribution, or use the
instructions below to cythonize Falcon for your environment.

The following commands tell pip to install Cython, and then to invoke
Falcon's ``setup.py``, which will in turn detect the presence of Cython
and then compile (AKA cythonize) the Falcon framework with the system's
default C compiler.

.. code:: bash

    $ pip install cython
    $ pip install --no-build-isolation --no-binary :all: falcon

Note that ``--no-build-isolation`` is necessary to override pip's default
PEP 517 behavior that can cause Cython not to be found in the build
environment.

If you want to verify that Cython is being invoked, simply
pass `-v` to pip in order to echo the compilation commands:

.. code:: bash

    $ pip install -v --no-build-isolation --no-binary :all: falcon

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

Windows users can try Waitress, a production-quality, pure-Python WSGI server.
Other alternatives on Windows include running Gunicorn and uWSGI via WSL,
as well as inside Linux Docker containers.

.. code:: bash

    $ pip install [gunicorn|uwsgi|waitress]

.. _install_asgi_server:

ASGI Server
-----------

Conversely, in order to run an ``async``
:class:`Falcon ASGI app <falcon.asgi.App>`, you will need an
`ASGI <https://asgi.readthedocs.io/en/latest/>`_ application server
(Falcon only supports ASGI 3.0+, aka the single-callable application style).

Uvicorn is a popular choice, owing to its fast and stable
implementation. What is more, Uvicorn is supported on Windows, and on PyPy
(however, both at a performance loss compared to CPython on Unix-like systems).

Falcon is also regularly tested against Daphne, the current ASGI reference
server.

For a more in-depth overview of available servers, see also:
`ASGI Implementations <https://asgi.readthedocs.io/en/latest/implementations.html>`_.

.. code:: bash

    $ pip install [uvicorn|daphne|hypercorn]

.. note::

    By default, the ``uvicorn`` package comes only with a minimal set of
    pure-Python dependencies.
    For CPython-based production deployments, you can install Uvicorn along
    with more optimized alternatives such as ``uvloop`` (a faster event loop),
    ``httptools`` (a faster HTTP protocol implementation) etc::

        $ pip install uvicorn[standard]

    See also a longer explanation on Uvicorn's website:
    `Quickstart <https://www.uvicorn.org/#quickstart>`_.

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
