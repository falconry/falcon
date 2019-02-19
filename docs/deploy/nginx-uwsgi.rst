.. _deploy:


Deploying Falcon on Linux with NGINX and uWSGI
==============================================


NGINX is a powerful web server and reverse proxy and uWSGI is a fast and
highly-configurable WSGI application server. Together, NGINX and uWSGI create a
one-two punch of speed and functionality which will suffice for most
applications. In addition, this stack provides the building blocks for a
horizontally-scalable and highly-available (HA) production environment and the
configuration below is just a starting point.

This guide provides instructions for deploying to a Linux environment only.
However, with a bit of effort you should be able to adapt this configuration to
other operating systems, such as OpenBSD.


Running your Application as a Different User
''''''''''''''''''''''''''''''''''''''''''''

It is best to execute the application as a different OS user than the one who
owns the source code for your application. The application user should *NOT*
have write access to your source. This mitigates the chance that someone could
write a malicious Python file to your source directory through an upload
endpoint you might define; when your application restarts, the malicious file is
loaded and proceeds to cause any number of BadThings\ :sup:(tm) to happen.

.. code:: sh

  $ useradd myproject --create-home
  $ useradd myproject-runner --no-create-home

It is helpful to switch to the project user (myproject) and use the home
directory as the application environment.

If you are working on a remote server, switch to the myproject user and pull
down the source code for your application.

.. code:: sh

  $ git clone git@github.com/myorg/myproject.git /home/myproject/src


.. note::

  You could use a tarball, zip file, scp or any other means to get your source
  onto a server.

Next, create a virtual environment which can be used to install your
dependencies.

.. code:: sh

  # For Python 3
  $ python3 -m venv /home/myproject/venv

  # For Python 2
  $ virtualenv /home/myproject/venv

Then install your dependencies.

.. code:: sh

  $ /home/myproject/venv/bin/pip install -r /home/myproject/src/requirements.txt
  $ /home/myproject/venv/bin/pip install -e /home/myproject/src
  $ /home/myproject/venv/bin/pip install uwsgi


.. note::

  The exact commands for creating a virtual environment might differ based on
  the Python version you are using and your operating system. At the end of the
  day the application needs a virtualenv in /home/myproject/venv with the
  project dependencies installed. Use the ``pip`` binary within the virtual
  environment by ``source venv/bin/activate`` or using the full path.


Preparing your Application for Service
''''''''''''''''''''''''''''''''''''''

For the purposes of this tutorial, we'll assume that you have implemented
a way to configure your application, such as with a
``create_api()`` function or a module-level script. This role of this
function or script is to supply an instance of :any:`falcon.API`, which
implements the standard WSGI callable interface.

You will need to expose the :any:`falcon.API` instance in some way so that
uWSGI can find it. For this tutorial we recommend creating a ``wsgi.py`` file.
Modify the logic of the following example file to properly configure your
application.  Ensure that you expose a variable called ``application`` which
is assigned to your :any:`falcon.API` instance.

.. code-block:: python
  :caption: /home/myproject/src/wsgi.py

  import os
  import myproject

  # Replace with your app's method of configuration
  config = myproject.get_config(os.environ['MYPROJECT_CONFIG'])

  # uWSGI will look for this variable
  application = myproject.create_api(config)

Note that in the above example, the WSGI callable is simple assigned to a
variable, ``application``, rather than being passed to a self-hosting
WSGI server such as `wsgiref.simple_server.make_server`. Starting an
independent WSGI server in your ``wsgi.py`` file will render unexpected
results.


Deploying Falcon behind uWSGI
'''''''''''''''''''''''''''''

With your ``wsgi.py`` file in place, it is time to configure uWSGI. Start by
creating a simple ``uwsgi.ini`` file. In general, you shouldn't commit this
file to source control; it should be generated from a template by your
deployment toolchain according to the target environment (number of CPUs, etc.).

This configuration, when executed, will create a new uWSGI server backed by
your ``wsgi.py`` file and listening at ``12.0.0.1:8080``.

.. code-block:: ini
  :caption: /home/myproject/src/uwsgi.ini

  [uwsgi]
  master = 1
  vacuum = true
  socket = 127.0.0.1:8080
  enable-threads = true
  thunder-lock = true
  threads = 2
  processes = 2
  virtualenv = /home/myproject/venv
  wsgi-file = /home/myproject/src/wsgi.py
  chdir = /home/myproject/src
  uid = myproject-runner
  gid = myproject-runner


.. note::

  **Threads vs. Processes**

  There are many questions to consider when deciding how to manage the processes
  that actually run your Python code. Are you generally CPU bound or IO bound?
  Is your application thread-safe? How many CPU's do you have? What system are
  you on? Do you need an in-process cache?

  The configuration presented here enables both threads and processes. However,
  you will have to experiment and do some research to understand your
  application's unique requirements, and then tailor your uWSGI configuration
  accordingly. Generally speaking, uWSGI is flexible enough to support most
  types of applications.

.. note::

  **TCP vs. UNIX Sockets**

  NGINX and uWSGI can communicate via normal TCP (using an IP address) or UNIX
  sockets (using a socket file). TCP sockets are easier to set up and generally
  work for simple deployments. If you want to have finer control over which
  processes, users, or groups may access the uWSGI application, or you are looking
  for a bit of a speed boost, consider using UNIX sockets. uWSGI can automatically
  drop privileges with ``chmod-socket`` and switch users with ``chown-socket``.

The ``uid`` and ``gid`` settings, as shown above, are critical to securing your
deployment. These values control the OS-level user and group the server
will use to execute the application. The specified OS user and group should not
have write permissions to the source directory. In this case, we use the
`myproject-runner` user that was created earlier for this purpose.

You can now start uWSGI like this:

.. code:: sh

  $ /home/myproject/venv/bin/uwsgi -c uwsgi.ini

If everything goes well, you should see something like this:

::

    *** Operational MODE: preforking+threaded ***
    ...
    *** uWSGI is running in multiple interpreter mode ***
    ...
    spawned uWSGI master process (pid: 91828)
    spawned uWSGI worker 1 (pid: 91866, cores: 2)
    spawned uWSGI worker 2 (pid: 91867, cores: 2)


.. note::

  It is always a good idea to keep an eye on the uWSGI logs, as they will contain
  exceptions and other information from your application that can help shed some
  light on unexpected behaviors.


Connecting NGINX and uWSGI
''''''''''''''''''''''''''

Although uWSGI may serve HTTP requests directly, it can be helpful to use a reverse
proxy, such as NGINX, to offload TLS negotiation, static file serving, etc.

NGINX natively supports `the uwsgi protocol <https://uwsgi-docs.readthedocs.io/en/latest/Protocol.html>`_, for efficiently proxying requests to uWSGI. In
NGINX parlance, we will create an "upstream" and direct that upstream (via a TCP
socket) to our now-running uWSGI application.

Before proceeding, install NGINX according to `the instructions for your
platform <https://docs.nginx.com/nginx/admin-guide/installing-nginx/installing-nginx-open-source/>`_.

Then, create an NGINX conf file that looks something like this:

.. code-block:: ini
  :caption: /etc/nginx/sites-avaiable/myproject.conf

  server {
    listen 80;
    server_name myproject.com;

    access_log /var/log/nginx/myproject-access.log;
    error_log  /var/log/nginx/myproject-error.log  warn;

    location / {
      uwsgi_pass 127.0.0.1:8080
      include uwsgi_params;
    }
  }

Finally, start (or restart) NGINX:

.. code-block:: sh

  $ sudo service start nginx

You should now have a working application. Check your uWSGI and NGINX logs for
errors if the application does not start.


Further Considerations
''''''''''''''''''''''

We did not explain how to configure TLS (HTTPS) for NGINX, leaving that as an
exercise for the reader. However, we do recommend using Let's Encrypt, which offers free,
short-term certificates with auto-renewal. Visit the `Let’s Encrypt site`_ to learn
how to integrate their service directly with NGINX.

In addition to setting up NGINX and uWSGI to run your application, you will of
course need to deploy a database server or any other services required by your
application. Due to the wide variety of options and considerations in this
space, we have chosen not to include ancillary services in this guide. However,
the Falcon community is always happy to help with deployment questions, so
`please don't hesitate to ask <https://falcon.readthedocs.io/en/stable/community/help.html#chat>`_.


.. _`Let’s Encrypt site`: https://certbot.eff.org/
