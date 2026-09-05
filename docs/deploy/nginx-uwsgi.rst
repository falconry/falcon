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


.. include:: _includes/run-as-different-user.rst

Then install your dependencies.

.. code:: sh

  $ /home/myproject/venv/bin/pip install -r /home/myproject/src/requirements.txt
  $ /home/myproject/venv/bin/pip install -e /home/myproject/src
  $ /home/myproject/venv/bin/pip install uwsgi


.. include:: _includes/venv-note.rst


Preparing your Application for Service
''''''''''''''''''''''''''''''''''''''

For the purposes of this tutorial, we'll assume that you have implemented
a way to configure your application, such as with a
``create_app()`` function or a module-level script. The role of this
function or script is to supply an instance of :any:`falcon.App`, which
implements the standard WSGI callable interface.

You will need to expose the :any:`falcon.App` instance in some way so that
uWSGI can find it. For this tutorial we recommend creating a ``wsgi.py`` file.
Modify the logic of the following example file to properly configure your
application.  Ensure that you expose a variable called ``application`` which
is assigned to your :any:`falcon.App` instance.

.. code-block:: python
  :caption: /home/myproject/src/wsgi.py

  import os
  import myproject

  # Replace with your app's method of configuration
  config = myproject.get_config(os.environ['MYPROJECT_CONFIG'])

  # uWSGI will look for this variable
  application = myproject.create_app(config)

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
your ``wsgi.py`` file and listening at ``127.0.0.1:8080``.

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

.. code-block:: nginx
  :caption: /etc/nginx/sites-available/myproject.conf

  # Redirect HTTP to HTTPS
  server {
    listen 80;
    server_name myproject.com;
    return 301 https://$host$request_uri;
  }

  server {
    listen 443 ssl;
    server_name myproject.com;

    ssl_certificate     /etc/letsencrypt/live/myproject.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/myproject.com/privkey.pem;

    # Mozilla Intermediate configuration
    # https://ssl-config.mozilla.org/#server=nginx
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;

    access_log /var/log/nginx/myproject-access.log;
    error_log  /var/log/nginx/myproject-error.log  warn;

    location / {
      uwsgi_pass 127.0.0.1:8080;
      include uwsgi_params;
    }
  }

.. include:: _includes/tls-note.rst

.. include:: _includes/start-nginx.rst

You should now have a working application. Check your uWSGI and NGINX logs for
errors if the application does not start.


Further Considerations
''''''''''''''''''''''

.. include:: _includes/letsencrypt-further.rst

.. include:: _includes/ancillary-services.rst


.. _`Let's Encrypt`: https://letsencrypt.org/
.. _`Let's Encrypt site`: https://certbot.eff.org/
