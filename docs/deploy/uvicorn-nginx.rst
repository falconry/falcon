.. _deploy-uvicorn-nginx:


Deploying Falcon ASGI on Linux with NGINX and Uvicorn
=====================================================


NGINX is a powerful web server and reverse proxy, and
`Uvicorn <https://www.uvicorn.org/>`_ is a fast ASGI application server.
Together they provide a practical starting point for hosting an asynchronous
:class:`Falcon ASGI application <falcon.asgi.App>` in production. As with the
:ref:`WSGI NGINX + uWSGI guide <deploy>`, the configuration below is only a
starting point for a horizontally scalable deployment.

This guide provides instructions for deploying to a Linux environment only.
However, with a bit of effort you should be able to adapt this configuration to
other operating systems.

For local development and learning, see the :ref:`ASGI tutorial <tutorial-asgi>`
and :ref:`ASGI server installation <install_asgi_server>`.


Running your Application as a Different User
''''''''''''''''''''''''''''''''''''''''''''

It is best to execute the application as a different OS user than the one who
owns the source code for your application. The application user should *NOT*
have write access to your source. This mitigates the chance that someone could
write a malicious Python file to your source directory through an upload
endpoint you might define; when your application restarts, the malicious file is
loaded and proceeds to cause any number of Bad Things™ to happen.

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

  $ python3 -m venv /home/myproject/venv

Then install your dependencies, including Uvicorn. For CPython-based production
deployments, prefer the ``uvicorn[standard]`` extra so that optimized
dependencies such as ``uvloop`` and ``httptools`` are available (see also
:ref:`install_asgi_server`):

.. code:: sh

  $ /home/myproject/venv/bin/pip install -r /home/myproject/src/requirements.txt
  $ /home/myproject/venv/bin/pip install -e /home/myproject/src
  $ /home/myproject/venv/bin/pip install 'uvicorn[standard]'


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
``create_app()`` function or a module-level script. The role of this
function or script is to supply an instance of :class:`falcon.asgi.App`, which
implements the standard ASGI callable interface.

You will need to expose the :class:`~falcon.asgi.App` instance in some way so
that Uvicorn can find it. For this tutorial we recommend creating an
``asgi.py`` file. Modify the logic of the following example file to properly
configure your application. Ensure that you expose a variable called ``app``
which is assigned to your :class:`~falcon.asgi.App` instance.

.. code-block:: python
  :caption: /home/myproject/src/asgi.py

  import os
  import myproject

  # Replace with your app's method of configuration
  config = myproject.get_config(os.environ['MYPROJECT_CONFIG'])

  # Uvicorn will look for this variable (e.g. uvicorn asgi:app)
  app = myproject.create_app(config)

Note that in the above example, the ASGI callable is simply assigned to a
variable, ``app``, rather than being passed to a self-hosting ASGI server
inside the module. Starting an independent server (for example via
``uvicorn.run()``) in your ``asgi.py`` file will render unexpected results when
you later launch Uvicorn from the process manager or command line.

If you are coming from the :ref:`WSGI NGINX + uWSGI guide <deploy>`, note the
difference in naming: uWSGI commonly expects an ``application`` callable in
``wsgi.py``, while Uvicorn is typically pointed at an ``app`` callable via a
module path such as ``asgi:app``.


Deploying Falcon behind Uvicorn
'''''''''''''''''''''''''''''''

With your ``asgi.py`` file in place, it is time to run Uvicorn. In general, you
shouldn't hard-code machine-specific process settings in source control; prefer
generating them from a template according to the target environment (number of
CPUs, etc.).

The following command starts Uvicorn against your ``asgi.py`` module, listening
only on the loopback interface at ``127.0.0.1:8000`` so that NGINX (not the
public internet) is the front door:

.. code:: sh

  $ /home/myproject/venv/bin/uvicorn asgi:app \
      --host 127.0.0.1 \
      --port 8000 \
      --workers 2 \
      --proxy-headers \
      --forwarded-allow-ips='127.0.0.1'

Run the process as the ``myproject-runner`` user so that the application does
not have write access to the source tree (same rationale as the uWSGI
``uid`` / ``gid`` settings in the :ref:`WSGI guide <deploy>`).

.. note::

  **Workers**

  Uvicorn's ``--workers`` flag runs multiple worker processes. The right number
  depends on whether your application is CPU- or I/O-bound, how many CPUs you
  have, and whether you keep in-process caches. Start small, measure, and
  adjust. See Uvicorn's deployment documentation for current guidance.

.. note::

  **Proxy headers**

  When NGINX terminates TLS and forwards requests to Uvicorn, enable
  ``--proxy-headers`` and restrict ``--forwarded-allow-ips`` to your reverse
  proxy (here, localhost). That allows Uvicorn to honor ``X-Forwarded-*``
  (and related) headers from a trusted hop only. In Falcon responders, prefer
  attributes such as :attr:`~falcon.Request.forwarded_scheme` and
  :attr:`~falcon.Request.forwarded_host` when you need the client-facing URL
  behind the proxy.

.. note::

  **TCP vs. UNIX sockets**

  NGINX and Uvicorn can communicate via TCP (as above) or via a UNIX domain
  socket. TCP is simpler for many deployments. UNIX sockets can be preferable
  when you want finer filesystem permissions on the listening endpoint.

In production you will usually supervise Uvicorn with systemd, supervisord, or
your container orchestrator rather than leaving a bare shell process. A minimal
systemd unit might look like this:

.. code-block:: ini
  :caption: /etc/systemd/system/myproject.service

  [Unit]
  Description=myproject ASGI (Uvicorn)
  After=network.target

  [Service]
  User=myproject-runner
  Group=myproject-runner
  WorkingDirectory=/home/myproject/src
  Environment=MYPROJECT_CONFIG=/home/myproject/config.ini
  ExecStart=/home/myproject/venv/bin/uvicorn asgi:app \
      --host 127.0.0.1 \
      --port 8000 \
      --workers 2 \
      --proxy-headers \
      --forwarded-allow-ips=127.0.0.1
  Restart=on-failure

  [Install]
  WantedBy=multi-user.target

Enable and start the service:

.. code:: sh

  $ sudo systemctl daemon-reload
  $ sudo systemctl enable --now myproject

If everything goes well, ``systemctl status myproject`` should show an active
service, and Uvicorn's logs (via the journal) should report workers listening
on ``127.0.0.1:8000``.

.. note::

  It is always a good idea to keep an eye on the Uvicorn and application logs,
  as they will contain exceptions and other information that can help shed light
  on unexpected behaviors.


Connecting NGINX and Uvicorn
''''''''''''''''''''''''''''

Although Uvicorn may serve HTTP (and WebSocket) requests directly, it is
helpful to use a reverse proxy such as NGINX to offload TLS negotiation, static
file serving, buffering, and related concerns. Unlike the uWSGI deployment,
NGINX talks to Uvicorn over plain HTTP using ``proxy_pass`` (not
``uwsgi_pass``).

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
      proxy_pass http://127.0.0.1:8000;
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;

      # WebSocket support (ASGI)
      proxy_http_version 1.1;
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection "upgrade";
    }
  }

.. note::

  The above configuration includes HTTPS with a redirect from HTTP, using
  certificate paths typical of `Let's Encrypt`_. For a plain HTTP-only
  configuration (e.g., during development), you can simplify to a single
  ``server`` block listening on port 80 without the ``ssl_*`` directives.

  For production deployments, use the `Mozilla SSL Configuration Generator`_
  to generate a configuration tuned to your requirements.

  The ``Upgrade`` / ``Connection`` headers are required for WebSocket proxying.
  If your application does not use WebSockets, you may omit those two
  ``proxy_set_header`` lines and the ``proxy_http_version`` directive; keep the
  ``X-Forwarded-*`` headers whenever Uvicorn is configured with
  ``--proxy-headers``.

.. _`Mozilla SSL Configuration Generator`: https://ssl-config.mozilla.org/#server=nginx

Finally, start (or restart) NGINX:

.. code-block:: sh

  $ sudo service start nginx

You should now have a working application. Check your Uvicorn (journal) and
NGINX logs for errors if the application does not start.


Further Considerations
''''''''''''''''''''''

The NGINX configuration above includes TLS (HTTPS) using `Let's Encrypt`_, which
offers free, short-term certificates with auto-renewal. Visit the `Let's Encrypt site`_
to learn how to set up certificates for your domain. Prefer terminating TLS at
NGINX (or another reverse proxy) rather than configuring certificates on Uvicorn
itself for this style of deployment.

Uvicorn supports the ASGI lifespan protocol, which Falcon uses for application
startup and shutdown hooks. Keep lifespan enabled (the Uvicorn default) unless
you have a specific reason to disable it.

Serve static files from NGINX (or a CDN) when possible, rather than through the
ASGI application, so your workers stay focused on dynamic requests.

Only trust forwarded headers from your reverse proxy. Misconfigured
``--forwarded-allow-ips`` (for example, allowing ``*`` on a public interface)
can let clients spoof scheme or client IP information.

In addition to setting up NGINX and Uvicorn to run your application, you will of
course need to deploy a database server or any other services required by your
application. Due to the wide variety of options and considerations in this
space, we have chosen not to include ancillary services in this guide. However,
the Falcon community is always happy to help with deployment questions, so
`please don't hesitate to ask <https://falcon.readthedocs.io/en/stable/community/help.html#chat>`_.

See also:

* :ref:`WSGI deployment with NGINX and uWSGI <deploy>`
* :ref:`ASGI tutorial <tutorial-asgi>` (local Uvicorn usage)
* Gunicorn / Gunicorn+PyPy deployment ideas: `#1369 <https://github.com/falconry/falcon/issues/1369>`_


.. _`Let's Encrypt`: https://letsencrypt.org/
.. _`Let's Encrypt site`: https://certbot.eff.org/
