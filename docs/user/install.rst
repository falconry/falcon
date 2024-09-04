.. _install:

Installation
============

PyPy
----

`PyPy <http://pypy.org/>`__ is the fastest way to run your Falcon app.
PyPy3.8+ is supported as of PyPy v7.3.7.

.. code:: bash

    $ pip install falcon

Or, to install the latest beta or release candidate, if any:

.. code:: bash

    $ pip install --pre falcon

CPython
-------

Falcon fully supports
`CPython <https://www.python.org/downloads/>`__ 3.8+.

The latest stable version of Falcon can be installed directly from PyPI:

.. code:: bash

    $ pip install falcon

Or, to install the latest beta or release candidate, if any:

.. code:: bash

    $ pip install --pre falcon

In order to provide an extra speed boost, Falcon automatically compiles itself
with `Cython <https://cython.org/>`__. Wheels containing pre-compiled binaries
are available from PyPI for the majority of common platforms (see
:ref:`binary_wheels` below for the complete list of the platforms that we
target, or simply check
`Falcon files on PyPI <https://pypi.org/project/falcon/#files>`__).

However, even if a binary build for your platform of choice is not available,
you can choose to stick with the generic pure-Python wheel (that ``pip`` should
pick automatically), or cythonize Falcon for your environment (see
:ref:`instructions below <cythonize>`).
The pure-Python version is functionally identical to binary wheels;
it is just slower on CPython.

.. _cythonize:

Cythonizing Falcon
^^^^^^^^^^^^^^^^^^

Falcon leverages `PEP 517 <https://peps.python.org/pep-0517/>`__ to
automatically compile (AKA *cythonize*) itself with Cython whenever it is
installed from the source distribution. So if a suitable
:ref:`binary wheel <binary_wheels>` is unavailable for your platform, or if you
want to recompile locally, you simply need to instruct ``pip`` not to use
prebuilt wheels:

.. code:: bash

    $ pip install --no-binary :all: falcon

If you want to verify that Cython is being invoked,
pass ``-v`` to ``pip`` in order to echo the compilation commands:

.. code:: bash

    $ pip install -v --no-binary :all: falcon

Apart from the obvious requirement to have a functional compiler toolchain set
up with CPython development headers, the only inconvenience of running
cythonization on your side is the extra couple of minutes it takes (depending
on your hardware; it can take much more on an underpowered CI runner, or if you
are using emulation to prepare your software for another architecture).

Furthermore, you can also cythonize the latest developmental snapshot Falcon
directly from the :ref:`source code <source_code>` on GitHub:

.. code:: bash

    $ pip install git+https://github.com/falconry/falcon/

.. danger::
    Although we try to keep the main development branch in a good shape at all
    times, we strongly recommend to use only stable versions of Falcon in
    production.

Compiling on Mac OS
^^^^^^^^^^^^^^^^^^^

.. tip::
    Pre-compiled Falcon wheels are available for macOS on both Intel and Apple
    Silicon chips, so normally you should be fine with just
    ``pip install falcon``.

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

.. _binary_wheels:

Binary Wheels
^^^^^^^^^^^^^

Binary Falcon wheels are automatically built for many CPython platforms,
courtesy of `cibuildwheel <https://cibuildwheel.pypa.io/en/stable/>`__.

.. wheels:: .github/workflows/cibuildwheel.yaml

   The following table summarizes the wheel availability on different
   combinations of CPython versions vs CPython platforms:

.. warning::
    The `free-threaded build
    <https://docs.python.org/3.13/whatsnew/3.13.html#free-threaded-cpython>`__
    flag is not yet enabled for our wheels at this time.

    If you wish to experiment with
    :ref:`running Falcon in the free-threaded mode <faq_free_threading>`, you
    will need to explicitly tell the interpreter to disable GIL (via the
    ``PYTHON_GIL`` environment variable, or the ``-X gil=0`` option).
    It is also advisable to :ref:`recompile Falcon from source <cythonize>` on
    a free-threaded CPython 3.13+ build before proceeding.
    :ref:`Let us know how it went <chat>`!

While we believe that our build configuration covers the most common
development and deployment scenarios, :ref:`let us known <chat>` if you are
interested in any builds that are currently missing from our selection!

Dependencies
------------

Falcon does not require the installation of any other packages.

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

.. _source_code:

Source Code
-----------

Falcon `lives on GitHub <https://github.com/falconry/falcon>`_, making the
code easy to browse, download, fork, etc. :ref:`Pull requests <contribute>`
are always welcome!
Also, please remember to star the project if it makes you happy. :)

Once you have cloned the repo or downloaded a tarball from GitHub, you
can install Falcon like this:

.. code:: bash

    $ # Clone over SSH:
    $ #   git clone git@github.com:falconry/falcon.git
    $ # Or, if you prefer, over HTTPS:
    $ #   git clone https://github.com/falconry/falcon
    $ cd falcon
    $ pip install .

.. tip::
    The above command will automatically install the
    :ref:`cythonized <cythonize>` version of Falcon. If you just want to
    experiment with the latest snapshot, you can skip the cythonization step by
    setting the ``FALCON_DISABLE_CYTHON`` environment variable to a non-empty
    value:

    .. code:: bash

        $ cd falcon
        $ FALCON_DISABLE_CYTHON=Y pip install .

Or, if you want to edit the code, first fork the main repo, clone the fork
to your desktop, and then run the following command to install it using
symbolic linking, so that when you change your code, the changes will be
automagically available to your app without having to reinstall the package:

.. code:: bash

    $ cd falcon
    $ FALCON_DISABLE_CYTHON=Y pip install -e .

You can manually test changes to the Falcon framework by switching to the
directory of the cloned repo and then running pytest:

.. code:: bash

    $ cd falcon
    $ FALCON_DISABLE_CYTHON=Y pip install -e .
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
